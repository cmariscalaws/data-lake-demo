# Lake Formation RBAC Setup Guide

This guide provides step-by-step instructions to manually configure Lake Formation RBAC after the initial CDK deployment.

## Prerequisites

- ✅ CDK stack deployed successfully (core infrastructure)
- ✅ AWS Console access with administrative permissions
- ✅ Understanding of Lake Formation concepts

## Overview

The Lake Formation RBAC components are temporarily disabled in the CDK code due to CloudFormation execution role limitations. This guide shows how to:

1. **Manually grant Lake Formation permissions** to the CDK CloudFormation execution role
2. **Enable Lake Formation RBAC** in the CDK code
3. **Deploy the complete stack** with RBAC enabled

## Step-by-Step Instructions

### Step 1: Deploy Lake Formation with Admin Role Only

1. Open `option_a/stack.py` in your editor
2. Find the Lake Formation section (around line 195)
3. **Remove the comment markers** `"""` at lines 220 and 321
4. **Uncomment the outputs** at lines 364-368 (remove the `#` prefix)
5. **Deploy the stack** (this will create LF admin role and basic setup):
   ```bash
   cd /path/to/option_a_cdk_py
   source .venv/bin/activate
   cdk deploy --all --require-approval never
   ```

### Step 2: Find Your CDK CloudFormation Execution Role

1. Open the **AWS Console** → **IAM** → **Roles**
2. Search for: `cdk-hnb659fds-cfn-exec-role-`
3. Click on the role that matches your account ID and region
4. Note the full role name (e.g., `cdk-hnb659fds-cfn-exec-role-123456789012-us-west-2`)

### Step 3: Add Lake Formation Permissions to CDK Role

1. In the role details page, click **"Add permissions"** → **"Create inline policy"**
2. Switch to **JSON** tab
3. Paste the following policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lakeformation:GrantPermissions",
        "lakeformation:RevokePermissions",
        "lakeformation:PutDataLakeSettings",
        "lakeformation:GetDataLakeSettings",
        "lakeformation:RegisterResource",
        "lakeformation:DeregisterResource",
        "lakeformation:DescribeResource",
        "lakeformation:ListResources"
      ],
      "Resource": "*"
    }
  ]
}
```

4. Click **"Next"**
5. Name the policy: `LakeFormationPermissions`
6. Click **"Create policy"**

### Step 4: Add CDK Role to Lake Formation Administrators

1. Open **AWS Console** → **Lake Formation** → **Settings**
2. In the **"Data lake administrators"** section, click **"Add"**
3. Enter the CDK execution role ARN:
   ```
   arn:aws:iam::{YOUR_ACCOUNT_ID}:role/cdk-hnb659fds-cfn-exec-role-{YOUR_ACCOUNT_ID}-{YOUR_REGION}
   ```
4. Click **"Save"**

### Step 5: Update CDK Code to Include CFN Role

1. Open `option_a/stack.py` in your editor
2. Find the Lake Formation administrators section (around line 251)
3. **Uncomment the CFN execution role** in the admins list:

```python
# Configure Lake Formation administrators
# Both the admin role and CFN execution role can manage LF permissions
lf_admins = [
    lf.CfnDataLakeSettings.DataLakePrincipalProperty(
        data_lake_principal_identifier=lf_admin_role.role_arn
    ),
    lf.CfnDataLakeSettings.DataLakePrincipalProperty(
        data_lake_principal_identifier=cdk.Fn.sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:role/cdk-hnb659fds-cfn-exec-role-${AWS::AccountId}-${AWS::Region}")
    )
]
```

### Step 6: Deploy the Complete Stack

1. Deploy the updated stack:
   ```bash
   cdk deploy --all --require-approval never
   ```

### Step 7: Verify Deployment

1. Check the **CloudFormation Console** for successful deployment
2. Verify the **Lake Formation Console** shows:
   - Registered S3 location
   - Data lake administrators configured
   - Principal permissions granted

## What Gets Created

After successful deployment, you'll have:

### IAM Roles
- **LFAdminRole**: Full Lake Formation administrative access
- **AnalystCoreRole**: Limited access (no PII, restricted rows)
- **AnalystPiiRole**: Full access including PII data

### Lake Formation Resources
- **Data Lake Settings**: Configured with admin roles
- **S3 Data Location**: Registered for permission management
- **Principal Permissions**: 
  - `DATA_LOCATION_ACCESS` for both analyst roles
  - `DESCRIBE` on the Glue database

### Athena Workgroups
- **wg_core_read_demo**: For core analyst role
- **wg_pii_read_demo**: For PII analyst role
- Separate result locations for query segregation

## Testing the RBAC Setup

### 1. Test Role Assumption
```bash
# Assume the core analyst role
aws sts assume-role \
  --role-arn "arn:aws:iam::ACCOUNT:role/OptionAIngestionDemoPy-AnalystCoreRoleF1795BD7-XXXXX" \
  --role-session-name "test-core-analyst"

# Assume the PII analyst role  
aws sts assume-role \
  --role-arn "arn:aws:iam::ACCOUNT:role/OptionAIngestionDemoPy-AnalystPiiRole0E9F1092-XXXXX" \
  --role-session-name "test-pii-analyst"
```

### 2. Test Athena Queries
- Use the appropriate workgroup for each role
- Verify query results are segregated by workgroup
- Check that Lake Formation permissions are enforced

### 3. Test Glue Catalog Access
- Verify both roles can see the `option_a_demo_db` database
- Check that table metadata is accessible
- Confirm Lake Formation gates actual data access

## Troubleshooting

### Common Issues

1. **"AccessDenied" errors during deployment**
   - Verify the CDK execution role has the Lake Formation permissions
   - Check that the policy was created correctly

2. **"Resource does not exist" errors**
   - Ensure the S3 bucket is properly registered with Lake Formation
   - Verify the Glue database exists

3. **Role assumption failures**
   - Check that the role ARNs are correct
   - Verify the roles have proper trust policies

### Verification Commands

```bash
# Check stack outputs
aws cloudformation describe-stacks \
  --stack-name OptionAIngestionDemoPy \
  --query 'Stacks[0].Outputs'

# Verify Lake Formation settings
aws lakeformation get-data-lake-settings

# List registered resources
aws lakeformation list-resources
```

## Security Considerations

- **Principle of Least Privilege**: Each role has only the minimum required permissions
- **Data Segregation**: Query results are stored in separate S3 locations
- **Audit Trail**: All Lake Formation actions are logged in CloudTrail
- **Encryption**: All data is encrypted at rest using KMS

## Next Steps

After successful RBAC setup:

1. **Configure Data Catalog**: Add tables and partitions to the Glue catalog
2. **Set Up Data Tags**: Use Lake Formation tags for fine-grained access control
3. **Implement Row-Level Security**: Configure data filters for sensitive data
4. **Monitor Usage**: Set up CloudWatch dashboards for query monitoring

## Support

For issues with this setup:
1. Check the CloudFormation events for deployment errors
2. Review Lake Formation logs in CloudTrail
3. Verify IAM permissions are correctly configured
4. Consult AWS Lake Formation documentation for advanced scenarios
