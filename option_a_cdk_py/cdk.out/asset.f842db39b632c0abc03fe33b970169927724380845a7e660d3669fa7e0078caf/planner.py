import json
import os
import datetime
import boto3

sqs = boto3.client('sqs')

def _today_iso():
    return datetime.datetime.utcnow().date().isoformat()

def handler(event, context):
    queue_urls = json.loads(os.environ['QUEUE_URLS_JSON'])
    date = _today_iso()

    total = 0
    for endpoint, qurl in queue_urls.items():
        for page in range(1, 11):  # 10 pages for demo
            body = {
                "endpoint": endpoint,
                "ingestion_date": date,
                "page": page
            }
            sqs.send_message(QueueUrl=qurl, MessageBody=json.dumps(body))
            total += 1

    return {"status": "ok", "planned": total, "date": date}
