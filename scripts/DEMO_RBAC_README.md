# Option A Ingestion Demo — **CDK Python** with Lake Formation RBAC

This project deploys a batch ingestion pipeline (**EventBridge → SQS → Lambda → S3**) plus **Glue + Athena**,
and adds **Lake Formation** scaffolding to demonstrate **RBAC** with **row** and **column**-level controls.

## What gets created
- **S3**: Data lake bucket (KMS) + Athena results bucket
- **SQS**: 4 queues (api-a/b/c/d) with DLQs
- **Lambda**: `PlannerFn` (cron) and `WorkerFn` (SQS consumers; Python 3.12)
- **Glue**: Database + Crawler (targets `s3://<lake>/raw/`)
- **Athena**: WorkGroups — `option_a_demo_wg` (default), `wg_core_read_demo`, `wg_pii_read_demo`
- **Lake Formation**:
  - Data lake settings (admin role)
  - Registered data location (the lake bucket) using service-linked role
  - Two demo roles: **AnalystCoreRole** and **AnalystPiiRole**
  - Permissions:
    - `DATA_LOCATION_ACCESS` on the lake for both roles
    - `DESCRIBE` on the Glue database for both roles
- **Scripts**: `scripts/demo_rbac.py` — applies **row filter** + **column restrictions** and runs Athena queries under each role

> Note: For simplicity, the script uses direct Lake Formation grants (not tag policies). You can extend to LF-Tag policies later.

## Deploy

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cdk bootstrap
cdk deploy
```

## Ingest + crawl once

Trigger a run (or wait for 01:00 UTC cron):

```bash
aws lambda invoke --function-name $(aws cloudformation list-stack-resources   --stack-name OptionAIngestionDemoPyRBAC   --query "StackResourceSummaries[?LogicalResourceId=='PlannerFn'].PhysicalResourceId"   --output text) /dev/stdout
```

Run the **Glue Crawler** once so Athena sees the table.

## Prerequisites for RBAC Demo

Before running the RBAC demo, you need to set up additional permissions that aren't automatically created by CDK.

### Quick Setup (Automated)

Run the setup script to automatically configure all required permissions:

```bash
# Make script executable (if not already)
chmod +x scripts/setup_rbac_permissions.sh

# Run setup script
./scripts/setup_rbac_permissions.sh [STACK_NAME]
```

The script will automatically:
- Fix KMS permissions for Lake Formation service-linked role
- Add Lake Formation permissions to admin role
- Add S3 and KMS permissions to both analyst roles
- Configure segregated S3 access paths

### Manual Setup (Step-by-Step)

If you prefer to set up permissions manually:

### 1. Fix KMS Permissions for Lake Formation Service-Linked Role

The Lake Formation service-linked role needs KMS decrypt permissions:

```bash
# Get your KMS key ID from CloudFormation outputs
KMS_KEY_ID=$(aws cloudformation describe-stacks --stack-name OptionAIngestionDemoPy --query 'Stacks[0].Outputs[?OutputKey==`DataLakeKeyArn`].OutputValue' --output text | cut -d'/' -f2)

# Update KMS key policy to allow Lake Formation service-linked role
aws kms put-key-policy --key-id $KMS_KEY_ID --policy-name default --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::'$(aws sts get-caller-identity --query Account --output text)':root"
      },
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::'$(aws sts get-caller-identity --query Account --output text)':role/aws-service-role/lakeformation.amazonaws.com/AWSServiceRoleForLakeFormationDataAccess"
      },
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}'
```

### 2. Add Lake Formation Permissions to Admin Role

The Lake Formation admin role needs explicit permissions:

```bash
# Get the admin role name
ADMIN_ROLE=$(aws iam list-roles --query 'Roles[?contains(RoleName, `LFAdminRole`)].RoleName' --output text)

# Add Lake Formation permissions
aws iam put-role-policy --role-name $ADMIN_ROLE --policy-name LakeFormationAdminPolicy --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lakeformation:*"
      ],
      "Resource": "*"
    }
  ]
}'
```

### 3. Add S3 and KMS Permissions to Analyst Roles

Both analyst roles need S3 and KMS permissions for Athena queries:

```bash
# Get role names
CORE_ROLE=$(aws iam list-roles --query 'Roles[?contains(RoleName, `AnalystCoreRole`)].RoleName' --output text)
PII_ROLE=$(aws iam list-roles --query 'Roles[?contains(RoleName, `AnalystPiiRole`)].RoleName' --output text)

# Get Athena results bucket name
ATHENA_BUCKET=$(aws cloudformation describe-stacks --stack-name OptionAIngestionDemoPy --query 'Stacks[0].Outputs[?OutputKey==`AthenaResultsBucketName`].OutputValue' --output text)

# Get KMS key ARN
KMS_KEY_ARN=$(aws cloudformation describe-stacks --stack-name OptionAIngestionDemoPy --query 'Stacks[0].Outputs[?OutputKey==`DataLakeKeyArn`].OutputValue' --output text)

# Add S3 permissions to Core role
aws iam put-role-policy --role-name $CORE_ROLE --policy-name S3ResultsAccess --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::'$ATHENA_BUCKET'/core/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::'$ATHENA_BUCKET'"
    }
  ]
}'

# Add S3 permissions to PII role
aws iam put-role-policy --role-name $PII_ROLE --policy-name S3ResultsAccess --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::'$ATHENA_BUCKET'/pii/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::'$ATHENA_BUCKET'"
    }
  ]
}'

# Add KMS permissions to both roles
aws iam put-role-policy --role-name $CORE_ROLE --policy-name KMSAccess --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "'$KMS_KEY_ARN'"
    }
  ]
}'

aws iam put-role-policy --role-name $PII_ROLE --policy-name KMSAccess --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "'$KMS_KEY_ARN'"
    }
  ]
}'
```

## Test Basic RBAC Setup

After setting up permissions, test the basic RBAC functionality:

```bash
python scripts/test_rbac.py
```

This should show both Core and PII roles can successfully query the data.

## Demonstrate Advanced RBAC

For the full RBAC demo with row and column-level controls:

```bash
python scripts/demo_rbac.py --stack OptionAIngestionDemoPy
```

What the script does:
- Finds the table created by the crawler in `option_a_demo_db`
- Creates a **data cells filter** limiting rows to `source in ('api-a','api-b')` for **AnalystCoreRole**
- Grants **column-level SELECT** to **AnalystCoreRole** on non-PII columns only
- Grants **full SELECT** on the table to **AnalystPiiRole**
- Assumes each role and runs two Athena queries to show:
  - Core sees only api-a/api-b
  - Core **cannot** read the `items` column
  - PII role sees all sources and can read `items`

## Clean up

```bash
cdk destroy
# Then empty S3 buckets manually if needed (data lake and athena results).
```
