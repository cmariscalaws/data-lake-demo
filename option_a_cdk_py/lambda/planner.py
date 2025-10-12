import json
import os
import datetime
import logging
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client('sqs')

def _today_iso():
    return datetime.datetime.utcnow().date().isoformat()

def handler(event, context):
    logger.info("Planner Lambda started", extra={
        "function_name": context.function_name,
        "request_id": context.aws_request_id,
        "remaining_time_ms": context.get_remaining_time_in_millis()
    })
    
    try:
        queue_urls = json.loads(os.environ['QUEUE_URLS_JSON'])
        date = _today_iso()
        
        logger.info("Starting planning process", extra={
            "ingestion_date": date,
            "endpoints": list(queue_urls.keys()),
            "total_queues": len(queue_urls)
        })

        total = 0
        endpoint_stats = {}
        
        for endpoint, qurl in queue_urls.items():
            endpoint_total = 0
            logger.info(f"Processing endpoint: {endpoint}", extra={
                "endpoint": endpoint,
                "queue_url": qurl
            })
            
            for page in range(1, 11):  # 10 pages for demo
                body = {
                    "endpoint": endpoint,
                    "ingestion_date": date,
                    "page": page
                }
                
                try:
                    response = sqs.send_message(QueueUrl=qurl, MessageBody=json.dumps(body))
                    total += 1
                    endpoint_total += 1
                    
                    logger.info(f"Sent message for {endpoint} page {page}", extra={
                        "endpoint": endpoint,
                        "page": page,
                        "message_id": response.get('MessageId'),
                        "md5": response.get('MD5OfBody')
                    })
                    
                except ClientError as e:
                    logger.error(f"Failed to send message for {endpoint} page {page}", extra={
                        "endpoint": endpoint,
                        "page": page,
                        "error_code": e.response['Error']['Code'],
                        "error_message": e.response['Error']['Message']
                    })
                    raise
            
            endpoint_stats[endpoint] = endpoint_total
            logger.info(f"Completed endpoint: {endpoint}", extra={
                "endpoint": endpoint,
                "messages_sent": endpoint_total
            })

        result = {
            "status": "ok", 
            "planned": total, 
            "date": date,
            "endpoint_stats": endpoint_stats
        }
        
        logger.info("Planner Lambda completed successfully", extra={
            "total_messages_planned": total,
            "ingestion_date": date,
            "endpoint_stats": endpoint_stats
        })
        
        return result
        
    except Exception as e:
        logger.error("Planner Lambda failed", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "request_id": context.aws_request_id
        })
        raise
