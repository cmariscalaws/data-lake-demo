import os
import json
import time
import gzip
import io
import hashlib
import datetime
import urllib.request
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

BUCKET = os.environ['DATA_LAKE_BUCKET']
USE_REAL_HTTP = os.environ.get('USE_REAL_HTTP', 'false').lower() == 'true'
ENDPOINT_MAP = json.loads(os.environ.get('ENDPOINT_MAP', '{}') or '{}')
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '5'))
QPS_SLEEP_MS = int(os.environ.get('QPS_SLEEP_MS', '50'))

def _deterministic_key(endpoint: str, date: str, page: int) -> str:
    return f"raw/source={endpoint}/ingestion_date={date}/page={page:06d}.json.gz"

def _s3_put_gzip_json(bucket: str, key: str, obj: Dict[str, Any]) -> None:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as gz:
        gz.write(json.dumps(obj, separators=(',', ':')).encode('utf-8'))
    data = buf.getvalue()
    etag = hashlib.md5(data).hexdigest()
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType='application/json',
        ContentEncoding='gzip',
        Metadata={'content-hash': etag},
    )

def _s3_exists(bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] in ('404', 'NotFound'):
            return False
        raise

def _mock_fetch(endpoint: str, date: str, page: int) -> Dict[str, Any]:
    return {
        "endpoint": endpoint,
        "date": date,
        "page": page,
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "items": [{"id": f"{endpoint}-{date}-{page}-{i}", "value": i} for i in range(5)]
    }

def _http_fetch(endpoint: str, date: str, page: int) -> Dict[str, Any]:
    base = ENDPOINT_MAP.get(endpoint)
    if not base:
        return _mock_fetch(endpoint, date, page)
    url = f"{base}?date={date}&page={page}"
    req = urllib.request.Request(url, headers={'User-Agent': 'option-a-demo'})
    backoff = 0.5
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status == 200:
                    data = resp.read()
                    return json.loads(data.decode('utf-8'))
                elif resp.status in (429, 500, 502, 503, 504):
                    raise RuntimeError(f"transient status {resp.status}")
                else:
                    raise RuntimeError(f"unexpected status {resp.status}")
        except Exception as e:
            if attempt >= MAX_RETRIES:
                raise
            time.sleep(backoff)
            backoff *= 2.0
    return _mock_fetch(endpoint, date, page)

def process_message(msg: Dict[str, Any]) -> None:
    endpoint = msg['endpoint']
    date = msg['ingestion_date']
    page = int(msg['page'])
    key = _deterministic_key(endpoint, date, page)

    if _s3_exists(BUCKET, key):
        print(f"skip existing {key}")
        return

    if QPS_SLEEP_MS > 0:
        time.sleep(QPS_SLEEP_MS / 1000.0)

    payload = _http_fetch(endpoint, date, page) if USE_REAL_HTTP else _mock_fetch(endpoint, date, page)
    _s3_put_gzip_json(BUCKET, key, payload)
    print(f"wrote s3://{BUCKET}/{key}")

def handler(event, context):
    for rec in event.get('Records', []):
        body = json.loads(rec['body'])
        process_message(body)
    return {"handled": len(event.get('Records', []))}
