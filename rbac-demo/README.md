# Lake Formation RBAC Demo

This folder contains all the files needed to demonstrate and test Lake Formation Role-Based Access Control (RBAC) with the data lake.

## 📁 Files Overview

### 📋 Documentation
- **`README.md`** - Complete setup and usage guide

### 🎭 Demo Script
- **`comprehensive_rbac_demo.py`** - **MAIN DEMO** - Complete RBAC validation with row/column-level security

### 🔧 Setup & Testing
- **`setup_rbac_permissions.sh`** - Automated permission configuration script
- **`test_rbac.py`** - Basic RBAC functionality test

## 🎭 Main Demo

### **`comprehensive_rbac_demo.py`**
**Purpose**: **Complete RBAC validation** - Validates both row-level and column-level security

**What it does**:
- ✅ **Row-level security validation** - Core role limited to api-a data only
- ✅ **Column-level security validation** - Core role cannot access 'items' column
- ✅ **Data volume comparison** - Shows different record counts per role
- ✅ **Comprehensive testing** - 4 different test scenarios
- ✅ **Automatic validation** - Analyzes results and confirms RBAC is working

**Key Features**:
- 🔒 **Row filtering** - Core role sees only api-a (20 records), PII role sees all (80 records)
- 🔒 **Column restrictions** - Core role blocked from 'items' column, PII role allowed
- 📊 **Multiple test scenarios** - Row security, column security, combined, volume
- 🎯 **Validation results** - Automatically confirms each security feature is working
- ✅ **Production-ready** - Demonstrates enterprise-grade data lake security

**When to use**:
- 🎭 **Main demonstration** - Primary demo for stakeholders
- 📊 **Complete validation** - Proves all RBAC features are working
- 🎓 **Training/education** - Shows comprehensive Lake Formation capabilities
- 📋 **Compliance demos** - Demonstrates fine-grained access controls

## 🚀 Quick Start

### 1. Prerequisites
Make sure you have:
- ✅ CDK stack deployed with Lake Formation RBAC enabled
- ✅ Data ingested and Glue crawler run
- ✅ AWS CLI configured with appropriate permissions

### 2. Setup Permissions
```bash
# Make setup script executable
chmod +x setup_rbac_permissions.sh

# Run automated setup
./setup_rbac_permissions.sh [STACK_NAME]
```

### 3. Run the Main Demo
```bash
python comprehensive_rbac_demo.py
```

## 📊 What the Demo Shows

### Comprehensive RBAC Demo (`comprehensive_rbac_demo.py`)
- 🔒 **Row-level security**: Core role limited to api-a data only (20 records)
- 🔒 **Column-level security**: Core role cannot access 'items' column (query fails)
- 🔓 **Full access**: PII role can access all data and all columns (80 records)
- 📊 **Automatic validation**: Confirms each security feature is working correctly
- 🎯 **Production-ready**: Demonstrates enterprise-grade data lake security

## 🔧 Permission Requirements

The setup script automatically configures:

1. **KMS permissions** for Lake Formation service-linked role
2. **Lake Formation admin role** permissions
3. **S3 permissions** for Core role (`/core/` path)
4. **S3 permissions** for PII role (`/pii/` path)
5. **KMS permissions** for both analyst roles

## 📋 Role Details

### Core Role (`AnalystCoreRole`)
- **Purpose**: Limited access for non-PII data analysis
- **Workgroup**: `wg_core_read_demo`
- **S3 Results**: `s3://athena-results-bucket/core/`
- **Permissions**: Row and column restrictions via Lake Formation
- **Data Access**: Only `api-a` endpoint data (20 records)
- **Column Access**: Cannot access `items` column (PII data)

### PII Role (`AnalystPiiRole`)
- **Purpose**: Full access including PII data
- **Workgroup**: `wg_pii_read_demo`
- **S3 Results**: `s3://athena-results-bucket/pii/`
- **Permissions**: Full table access
- **Data Access**: All endpoints (`api-a`, `api-b`, `api-c`, `api-d`) - 80 records
- **Column Access**: Can access all columns including `items`

## 🔧 Manual Lake Formation RBAC Setup

### Prerequisites
- ✅ CDK stack deployed with Lake Formation RBAC enabled
- ✅ Data ingested and Glue crawler run
- ✅ AWS Console access with appropriate permissions
- ✅ Glue database: `option_a_demo_db`
- ✅ Glue table: `raw` (with columns: `endpoint`, `date`, `page`, `fetched_at`, `items`)

### Step 1: Register Glue Resources with Lake Formation

#### 1.1 Register Glue Database
1. **AWS Console** → **Lake Formation** → **Administration** → **Data lake locations**
2. Click **"Register location"**
3. **Resource type**: Database
4. **Database**: `option_a_demo_db`
5. **IAM role**: `OptionAIngestionDemoPy-LFAdminRoleE5DF1BFB-fZnZVF27Yd2E`
6. Click **"Register location"**

#### 1.2 Register Glue Table
1. **AWS Console** → **Lake Formation** → **Administration** → **Data lake locations**
2. Click **"Register location"**
3. **Resource type**: Table
4. **Database**: `option_a_demo_db`
5. **Table**: `raw`
6. **IAM role**: `OptionAIngestionDemoPy-LFAdminRoleE5DF1BFB-fZnZVF27Yd2E`
7. Click **"Register location"**

### Step 2: Create Data Cells Filter for Row-Level Security

#### 2.1 Create Row Filter
1. **AWS Console** → **Lake Formation** → **Administration** → **Data filters**
2. Click **"Create filter"**
3. **Table**: `option_a_demo_db.raw`
4. **Filter name**: `core_role_filter`
5. **Row filter expression**: `endpoint = 'api-a'`
6. **Columns**: Select `endpoint`, `date`, `page`, `fetched_at` (exclude `items`)
7. Click **"Create filter"**

### Step 3: Grant Lake Formation Permissions

#### 3.1 Grant Core Role Permissions (Limited Access)
1. **AWS Console** → **Lake Formation** → **Permissions** → **Data permissions**
2. Click **"Grant permissions"**
3. **Principal**: `OptionAIngestionDemoPy-AnalystCoreRoleF1795BD7-UFQUIDydLNMa`
4. **Resource**: `option_a_demo_db.raw`
5. **Columns**: Select `endpoint`, `date`, `page`, `fetched_at` (exclude `items`)
6. **Permissions**: `SELECT`
7. **Data filter**: `core_role_filter`
8. Click **"Grant"**

#### 3.2 Grant PII Role Permissions (Full Access)
1. **AWS Console** → **Lake Formation** → **Permissions** → **Data permissions**
2. Click **"Grant permissions"**
3. **Principal**: `OptionAIngestionDemoPy-AnalystPiiRole0E9F1092-qj0y9WP3JMLG`
4. **Resource**: `option_a_demo_db.raw`
5. **Columns**: Select all columns (including `items`)
6. **Permissions**: `SELECT`
7. Click **"Grant"**

### Step 4: Configure Lake Formation Settings

#### 4.1 Set Default Permissions
1. **AWS Console** → **Lake Formation** → **Administration** → **Settings**
2. **Create table default permissions**: Empty (no default permissions)
3. **Create database default permissions**: Empty (no default permissions)
4. Click **"Save"**

#### 4.2 Add Lake Formation Administrators
1. **AWS Console** → **Lake Formation** → **Administration** → **Settings**
2. **Data lake administrators**: Add your AWS user account
3. **Data lake administrators**: Add `OptionAIngestionDemoPy-LFAdminRoleE5DF1BFB-fZnZVF27Yd2E`
4. Click **"Save"**

### Step 5: Configure IAM Permissions

#### 5.1 Core Role S3 Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::optionaingestiondemopy-athenaresultsbucket879938fa-vegnrliagxy4/core/*",
                "arn:aws:s3:::optionaingestiondemopy-athenaresultsbucket879938fa-vegnrliagxy4/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::optionaingestiondemopy-athenaresultsbucket879938fa-vegnrliagxy4"
        }
    ]
}
```

#### 5.2 PII Role S3 Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::optionaingestiondemopy-athenaresultsbucket879938fa-vegnrliagxy4/pii/*",
                "arn:aws:s3:::optionaingestiondemopy-athenaresultsbucket879938fa-vegnrliagxy4/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::optionaingestiondemopy-athenaresultsbucket879938fa-vegnrliagxy4"
        }
    ]
}
```

#### 5.3 Athena Permissions (Both Roles)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "athena:StartQueryExecution",
                "athena:StopQueryExecution",
                "athena:GetQueryExecution",
                "athena:GetQueryResults",
                "athena:GetWorkGroup",
                "athena:ListQueryExecutions",
                "athena:ListWorkGroups"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "glue:GetDatabase",
                "glue:GetDatabases",
                "glue:GetTable",
                "glue:GetTables",
                "glue:GetPartition",
                "glue:GetPartitions"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "lakeformation:GetDataAccess",
                "lakeformation:SearchTablesByLFTags",
                "lakeformation:GetResourceLFTags"
            ],
            "Resource": "*"
        }
    ]
}
```

### Step 6: Verify Setup

#### 6.1 Test Row-Level Security
```bash
# Run the comprehensive demo
python comprehensive_rbac_demo.py
```

**Expected Results:**
- **Core Role**: Only sees `api-a` data (20 records)
- **PII Role**: Sees all endpoints (80 records)

#### 6.2 Test Column-Level Security
**Expected Results:**
- **Core Role**: Cannot access `items` column (query fails)
- **PII Role**: Can access `items` column (query succeeds)

### Step 7: Troubleshooting

#### 7.1 Common Issues
1. **"Resource does not exist"**: Glue resources not registered with Lake Formation
2. **"Insufficient permissions"**: Missing Lake Formation administrator permissions
3. **"Access denied"**: Missing S3 or KMS permissions for Athena results
4. **Identical results**: Lake Formation permissions not properly configured

#### 7.2 Verification Commands
```bash
# Check registered resources
aws lakeformation list-resources --output table

# Check Data Cells Filters
aws lakeformation list-data-cells-filter --output table

# Check Lake Formation settings
aws lakeformation get-data-lake-settings --output json

# Check role permissions
aws iam list-attached-role-policies --role-name OptionAIngestionDemoPy-AnalystCoreRoleF1795BD7-UFQUIDydLNMa
aws iam list-attached-role-policies --role-name OptionAIngestionDemoPy-AnalystPiiRole0E9F1092-qj0y9WP3JMLG
```

## 🛠️ Troubleshooting

### Common Issues
1. **Permission errors**: Run `setup_rbac_permissions.sh` again
2. **Query failures**: Check KMS and S3 permissions
3. **Role assumption errors**: Verify role names and ARNs

### Debug Commands
```bash
# Check CloudFormation outputs
aws cloudformation describe-stacks --stack-name OptionAIngestionDemoPy --query 'Stacks[0].Outputs'

# List IAM roles
aws iam list-roles --query 'Roles[?contains(RoleName, `Analyst`)].{Name:RoleName,Arn:Arn}'

# Check Lake Formation settings
aws lakeformation get-data-lake-settings
```

## 📚 Additional Resources

- **Main Project README**: `../option_a_cdk_py/README.md`
- **Lake Formation Setup Guide**: `../option_a_cdk_py/LAKE_FORMATION_SETUP.md`
- **CDK Stack Code**: `../option_a_cdk_py/option_a/stack.py`

## 🎯 Next Steps

After mastering basic RBAC, explore:
- **Lake Formation Tags**: More sophisticated access control
- **Cross-account access**: Multi-account data sharing
- **Data masking**: Dynamic data obfuscation
- **Audit logging**: Comprehensive access tracking
