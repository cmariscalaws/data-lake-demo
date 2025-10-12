import os
import json
import time
import gzip
import io
import hashlib
import datetime
import urllib.request
import logging
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

BUCKET = os.environ['DATA_LAKE_BUCKET']
USE_REAL_HTTP = os.environ.get('USE_REAL_HTTP', 'false').lower() == 'true'
ENDPOINT_MAP = json.loads(os.environ.get('ENDPOINT_MAP', '{}') or '{}')
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '5'))
QPS_SLEEP_MS = int(os.environ.get('QPS_SLEEP_MS', '50'))

def _deterministic_key(endpoint: str, date: str, page: int) -> str:
    return f"raw/source={endpoint}/ingestion_date={date}/page={page:06d}.json.gz"

def _s3_put_gzip_json(bucket: str, key: str, obj: Dict[str, Any]) -> None:
    logger.info(f"Compressing and uploading to S3", extra={
        "bucket": bucket,
        "key": key,
        "object_size_bytes": len(json.dumps(obj, separators=(',', ':')))
    })
    
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as gz:
        gz.write(json.dumps(obj, separators=(',', ':')).encode('utf-8'))
    data = buf.getvalue()
    etag = hashlib.md5(data).hexdigest()
    
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType='application/json',
            ContentEncoding='gzip',
            Metadata={'content-hash': etag},
        )
        
        logger.info(f"Successfully uploaded to S3", extra={
            "bucket": bucket,
            "key": key,
            "compressed_size_bytes": len(data),
            "content_hash": etag
        })
        
    except ClientError as e:
        logger.error(f"Failed to upload to S3", extra={
            "bucket": bucket,
            "key": key,
            "error_code": e.response['Error']['Code'],
            "error_message": e.response['Error']['Message']
        })
        raise

def _s3_exists(bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        logger.info(f"S3 object exists", extra={"bucket": bucket, "key": key})
        return True
    except ClientError as e:
        if e.response['Error']['Code'] in ('404', 'NotFound'):
            logger.info(f"S3 object does not exist", extra={"bucket": bucket, "key": key})
            return False
        logger.error(f"Error checking S3 object existence", extra={
            "bucket": bucket,
            "key": key,
            "error_code": e.response['Error']['Code'],
            "error_message": e.response['Error']['Message']
        })
        raise

def _mock_fetch(endpoint: str, date: str, page: int) -> Dict[str, Any]:
    logger.info(f"Generating mock data", extra={
        "endpoint": endpoint,
        "date": date,
        "page": page
    })
    
    result = {
        "endpoint": endpoint,
        "date": date,
        "page": page,
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "items": [{"id": f"{endpoint}-{date}-{page}-{i}", "value": i} for i in range(5)]
    }
    
    logger.info(f"Generated mock data", extra={
        "endpoint": endpoint,
        "date": date,
        "page": page,
        "item_count": len(result["items"])
    })
    
    return result

def _http_fetch(endpoint: str, date: str, page: int) -> Dict[str, Any]:
    base = ENDPOINT_MAP.get(endpoint)
    if not base:
        logger.warning(f"No endpoint mapping found, using mock data", extra={
            "endpoint": endpoint,
            "available_endpoints": list(ENDPOINT_MAP.keys())
        })
        return _mock_fetch(endpoint, date, page)
    
    url = f"{base}?date={date}&page={page}"
    req = urllib.request.Request(url, headers={'User-Agent': 'option-a-demo'})
    backoff = 0.5
    
    logger.info(f"Starting HTTP fetch", extra={
        "endpoint": endpoint,
        "url": url,
        "date": date,
        "page": page,
        "max_retries": MAX_RETRIES
    })
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"HTTP fetch attempt {attempt}", extra={
                "endpoint": endpoint,
                "url": url,
                "attempt": attempt,
                "backoff_seconds": backoff if attempt > 1 else 0
            })
            
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status == 200:
                    data = resp.read()
                    result = json.loads(data.decode('utf-8'))
                    
                    logger.info(f"HTTP fetch successful", extra={
                        "endpoint": endpoint,
                        "url": url,
                        "attempt": attempt,
                        "response_size_bytes": len(data),
                        "status_code": resp.status
                    })
                    
                    return result
                elif resp.status in (429, 500, 502, 503, 504):
                    logger.warning(f"Transient HTTP error", extra={
                        "endpoint": endpoint,
                        "url": url,
                        "attempt": attempt,
                        "status_code": resp.status,
                        "will_retry": attempt < MAX_RETRIES
                    })
                    raise RuntimeError(f"transient status {resp.status}")
                else:
                    logger.error(f"Unexpected HTTP status", extra={
                        "endpoint": endpoint,
                        "url": url,
                        "attempt": attempt,
                        "status_code": resp.status
                    })
                    raise RuntimeError(f"unexpected status {resp.status}")
                    
        except Exception as e:
            logger.warning(f"HTTP fetch attempt {attempt} failed", extra={
                "endpoint": endpoint,
                "url": url,
                "attempt": attempt,
                "error": str(e),
                "error_type": type(e).__name__,
                "will_retry": attempt < MAX_RETRIES
            })
            
            if attempt >= MAX_RETRIES:
                logger.error(f"HTTP fetch failed after {MAX_RETRIES} attempts", extra={
                    "endpoint": endpoint,
                    "url": url,
                    "final_error": str(e),
                    "final_error_type": type(e).__name__
                })
                raise
            
            time.sleep(backoff)
            backoff *= 2.0
    
    # This should never be reached, but just in case
    logger.warning(f"Falling back to mock data after HTTP fetch", extra={
        "endpoint": endpoint,
        "url": url
    })
    return _mock_fetch(endpoint, date, page)

def process_message(msg: Dict[str, Any]) -> None:
    endpoint = msg['endpoint']
    date = msg['ingestion_date']
    page = int(msg['page'])
    key = _deterministic_key(endpoint, date, page)

    logger.info(f"Processing message", extra={
        "endpoint": endpoint,
        "date": date,
        "page": page,
        "s3_key": key
    })

    if _s3_exists(BUCKET, key):
        logger.info(f"Skipping existing file", extra={
            "endpoint": endpoint,
            "date": date,
            "page": page,
            "s3_key": key
        })
        return

    if QPS_SLEEP_MS > 0:
        logger.info(f"Applying QPS sleep", extra={
            "sleep_ms": QPS_SLEEP_MS,
            "endpoint": endpoint,
            "page": page
        })
        time.sleep(QPS_SLEEP_MS / 1000.0)

    logger.info(f"Fetching data", extra={
        "endpoint": endpoint,
        "date": date,
        "page": page,
        "use_real_http": USE_REAL_HTTP
    })
    
    payload = _http_fetch(endpoint, date, page) if USE_REAL_HTTP else _mock_fetch(endpoint, date, page)
    
    logger.info(f"Uploading to S3", extra={
        "endpoint": endpoint,
        "date": date,
        "page": page,
        "s3_key": key,
        "payload_item_count": len(payload.get("items", []))
    })
    
    _s3_put_gzip_json(BUCKET, key, payload)
    
    logger.info(f"Successfully processed message", extra={
        "endpoint": endpoint,
        "date": date,
        "page": page,
        "s3_key": key,
        "s3_url": f"s3://{BUCKET}/{key}"
    })

def handler(event, context):
    logger.info("Worker Lambda started", extra={
        "function_name": context.function_name,
        "request_id": context.aws_request_id,
        "remaining_time_ms": context.get_remaining_time_in_millis(),
        "record_count": len(event.get('Records', []))
    })
    
    try:
        processed_count = 0
        failed_count = 0
        processing_stats = {}
        
        for i, rec in enumerate(event.get('Records', [])):
            try:
                logger.info(f"Processing record {i+1}", extra={
                    "record_index": i,
                    "message_id": rec.get('messageId'),
                    "receipt_handle": rec.get('receiptHandle')[:20] + "..." if rec.get('receiptHandle') else None
                })
                
                body = json.loads(rec['body'])
                endpoint = body.get('endpoint', 'unknown')
                
                # Track stats per endpoint
                if endpoint not in processing_stats:
                    processing_stats[endpoint] = {"processed": 0, "failed": 0}
                
                process_message(body)
                processed_count += 1
                processing_stats[endpoint]["processed"] += 1
                
                logger.info(f"Successfully processed record {i+1}", extra={
                    "record_index": i,
                    "endpoint": endpoint,
                    "message_id": rec.get('messageId')
                })
                
            except Exception as e:
                failed_count += 1
                endpoint = body.get('endpoint', 'unknown') if 'body' in locals() else 'unknown'
                if endpoint in processing_stats:
                    processing_stats[endpoint]["failed"] += 1
                
                logger.error(f"Failed to process record {i+1}", extra={
                    "record_index": i,
                    "endpoint": endpoint,
                    "message_id": rec.get('messageId'),
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                # Re-raise to trigger Lambda retry/DLQ
                raise
        
        result = {
            "handled": processed_count,
            "failed": failed_count,
            "processing_stats": processing_stats
        }
        
        logger.info("Worker Lambda completed", extra={
            "total_processed": processed_count,
            "total_failed": failed_count,
            "processing_stats": processing_stats,
            "request_id": context.aws_request_id
        })
        
        return result
        
    except Exception as e:
        logger.error("Worker Lambda failed", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "request_id": context.aws_request_id,
            "record_count": len(event.get('Records', []))
        })
        raise
