#!/bin/bash

# Lake Formation RBAC Setup Script
# This script sets up the necessary permissions for the Lake Formation RBAC demo

set -e

echo "🚀 Setting up Lake Formation RBAC permissions..."
echo "=================================================="

# Get stack name (default to OptionAIngestionDemoPy)
STACK_NAME=${1:-OptionAIngestionDemoPy}

echo "📋 Using stack: $STACK_NAME"

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 Account ID: $ACCOUNT_ID"

# Get CloudFormation outputs
echo "📋 Getting CloudFormation outputs..."
KMS_KEY_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`DataLakeKeyArn`].OutputValue' --output text)
ATHENA_BUCKET=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`AthenaResultsBucketName`].OutputValue' --output text)

if [ -z "$KMS_KEY_ARN" ] || [ -z "$ATHENA_BUCKET" ]; then
    echo "❌ Error: Could not get required CloudFormation outputs"
    echo "Make sure the stack is deployed and has the required outputs"
    exit 1
fi

KMS_KEY_ID=$(echo $KMS_KEY_ARN | cut -d'/' -f2)
echo "📋 KMS Key ID: $KMS_KEY_ID"
echo "📋 Athena Bucket: $ATHENA_BUCKET"

# Get role names
echo "📋 Getting IAM role names..."
ADMIN_ROLE=$(aws iam list-roles --query 'Roles[?contains(RoleName, `LFAdminRole`)].RoleName' --output text)
CORE_ROLE=$(aws iam list-roles --query 'Roles[?contains(RoleName, `AnalystCoreRole`)].RoleName' --output text)
PII_ROLE=$(aws iam list-roles --query 'Roles[?contains(RoleName, `AnalystPiiRole`)].RoleName' --output text)

if [ -z "$ADMIN_ROLE" ] || [ -z "$CORE_ROLE" ] || [ -z "$PII_ROLE" ]; then
    echo "❌ Error: Could not find required IAM roles"
    echo "Make sure Lake Formation RBAC is deployed"
    exit 1
fi

echo "📋 Admin Role: $ADMIN_ROLE"
echo "📋 Core Role: $CORE_ROLE"
echo "📋 PII Role: $PII_ROLE"

# 1. Fix KMS permissions for Lake Formation service-linked role
echo ""
echo "🔧 Step 1: Fixing KMS permissions for Lake Formation service-linked role..."
aws kms put-key-policy --key-id $KMS_KEY_ID --policy-name default --policy "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Effect\": \"Allow\",
      \"Principal\": {
        \"AWS\": \"arn:aws:iam::$ACCOUNT_ID:root\"
      },
      \"Action\": \"kms:*\",
      \"Resource\": \"*\"
    },
    {
      \"Effect\": \"Allow\",
      \"Principal\": {
        \"AWS\": \"arn:aws:iam::$ACCOUNT_ID:role/aws-service-role/lakeformation.amazonaws.com/AWSServiceRoleForLakeFormationDataAccess\"
      },
      \"Action\": [
        \"kms:Decrypt\",
        \"kms:DescribeKey\"
      ],
      \"Resource\": \"*\"
    }
  ]
}"
echo "✅ KMS permissions updated"

# 2. Add Lake Formation permissions to admin role
echo ""
echo "🔧 Step 2: Adding Lake Formation permissions to admin role..."
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
echo "✅ Admin role permissions updated"

# 3. Add S3 permissions to Core role
echo ""
echo "🔧 Step 3: Adding S3 permissions to Core role..."
aws iam put-role-policy --role-name $CORE_ROLE --policy-name S3ResultsAccess --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Effect\": \"Allow\",
      \"Action\": [
        \"s3:GetObject\",
        \"s3:PutObject\",
        \"s3:DeleteObject\"
      ],
      \"Resource\": \"arn:aws:s3::$ATHENA_BUCKET/core/*\"
    },
    {
      \"Effect\": \"Allow\",
      \"Action\": [
        \"s3:ListBucket\"
      ],
      \"Resource\": \"arn:aws:s3::$ATHENA_BUCKET\"
    }
  ]
}"
echo "✅ Core role S3 permissions updated"

# 4. Add S3 permissions to PII role
echo ""
echo "🔧 Step 4: Adding S3 permissions to PII role..."
aws iam put-role-policy --role-name $PII_ROLE --policy-name S3ResultsAccess --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Effect\": \"Allow\",
      \"Action\": [
        \"s3:GetObject\",
        \"s3:PutObject\",
        \"s3:DeleteObject\"
      ],
      \"Resource\": \"arn:aws:s3::$ATHENA_BUCKET/pii/*\"
    },
    {
      \"Effect\": \"Allow\",
      \"Action\": [
        \"s3:ListBucket\"
      ],
      \"Resource\": \"arn:aws:s3::$ATHENA_BUCKET\"
    }
  ]
}"
echo "✅ PII role S3 permissions updated"

# 5. Add KMS permissions to Core role
echo ""
echo "🔧 Step 5: Adding KMS permissions to Core role..."
aws iam put-role-policy --role-name $CORE_ROLE --policy-name KMSAccess --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Effect\": \"Allow\",
      \"Action\": [
        \"kms:Decrypt\",
        \"kms:DescribeKey\"
      ],
      \"Resource\": \"$KMS_KEY_ARN\"
    }
  ]
}"
echo "✅ Core role KMS permissions updated"

# 6. Add KMS permissions to PII role
echo ""
echo "🔧 Step 6: Adding KMS permissions to PII role..."
aws iam put-role-policy --role-name $PII_ROLE --policy-name KMSAccess --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Effect\": \"Allow\",
      \"Action\": [
        \"kms:Decrypt\",
        \"kms:DescribeKey\"
      ],
      \"Resource\": \"$KMS_KEY_ARN\"
    }
  ]
}"
echo "✅ PII role KMS permissions updated"

echo ""
echo "🎉 All permissions have been set up successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Test basic RBAC: python scripts/test_rbac.py"
echo "2. Run advanced demo: python scripts/demo_rbac.py --stack $STACK_NAME"
echo ""
echo "🔍 What was configured:"
echo "- KMS permissions for Lake Formation service-linked role"
echo "- Lake Formation admin permissions"
echo "- S3 and KMS permissions for both analyst roles"
echo "- Segregated S3 access (Core: /core/, PII: /pii/)"
