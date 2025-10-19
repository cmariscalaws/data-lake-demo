# AWS Option A Demo (CDK **Python**) — EventBridge → SQS → Lambda → S3 (+ Glue, Athena)

This is a Step-Functions-free batch ingestion pipeline implemented with **AWS CDK in Python**.

- **EventBridge (cron)** triggers a **Planner Lambda** that enqueues work onto **4 SQS queues** (one per endpoint).
- A single **Worker Lambda (Python)** is subscribed to all queues; it fetches (mock by default or real HTTP) and writes **gzipped JSON** to **S3** under:
  `raw/source=<endpoint>/ingestion_date=<YYYY-MM-DD>/page=000001.json.gz`
- **Glue Database + Crawler** builds/updates tables so you can query with **Athena**.
- **Athena WorkGroup** + results bucket configured.
- **CloudWatch Alarms**: DLQ has messages, age-of-oldest-message, worker errors.

> By default the Worker uses a mock payload. Flip `USE_REAL_HTTP=true` and set `ENDPOINT_MAP` to call real APIs.

## Prerequisites
- Python 3.11+
- AWS CDK v2 (`npm i -g aws-cdk` once) — only the CLI is Node-based.
- AWS credentials configured

## Setup & Deploy
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cdk bootstrap
cdk deploy
```

## Trigger a test run
- Either wait for the cron (01:00 UTC) or invoke the **Planner** manually from the console, or:
```bash
aws lambda invoke --function-name $(aws cloudformation list-stack-resources   --stack-name OptionAIngestionDemoPy   --query "StackResourceSummaries[?LogicalResourceId=='PlannerFn'].PhysicalResourceId"   --output text) /dev/stdout
```

Check S3 for new objects:
```
s3://<DataLakeBucket>/raw/source=api-a/ingestion_date=<today>/
...
```

Start the **Glue Crawler** or wait for its schedule, then query in **Athena** using the created WorkGroup.

## Lake Formation RBAC Setup

The stack includes Lake Formation RBAC components that are temporarily disabled due to CloudFormation execution role limitations. To enable them:

1. **Follow the detailed guide**: See [LAKE_FORMATION_SETUP.md](./LAKE_FORMATION_SETUP.md)
2. **Quick steps**:
   - Add Lake Formation permissions to CDK execution role in AWS Console
   - Uncomment Lake Formation code in `option_a/stack.py`
   - Run `cdk deploy --all --require-approval never`

This enables:
- **Role-based access control** with separate analyst roles
- **Data segregation** via dedicated Athena workgroups  
- **Fine-grained permissions** managed by Lake Formation

## Clean up
```bash
cdk destroy
# Then empty the S3 buckets (data lake and athena results) if CloudFormation can't auto-delete them.
```

## Flip to real HTTP
- Update Worker Lambda environment:
  - `USE_REAL_HTTP=true`
  - `ENDPOINT_MAP={"api-a":"https://apiA.example.com/data","api-b":"https://apiB.example.com/data","api-c":"...","api-d":"..."}`
- The Worker does simple `GET ?date=YYYY-MM-DD&page=N` with exponential backoff on 429/5xx.

## Project layout
```
.
├─ app.py
├─ option_a/
│  └─ stack.py
├─ lambda/
│  ├─ planner.py
│  └─ worker.py
├─ cdk.json
└─ requirements.txt
```
