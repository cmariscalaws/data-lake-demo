# Lake Formation RBAC Demo

This folder contains all the files needed to demonstrate and test Lake Formation Role-Based Access Control (RBAC) with the data lake.

## 📁 Files Overview

### 📋 Documentation
- **`README.md`** - This overview file
- **`DEMO_RBAC_README.md`** - Complete setup and usage guide
- **`INDEX.md`** - File navigation

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

### PII Role (`AnalystPiiRole`)
- **Purpose**: Full access including PII data
- **Workgroup**: `wg_pii_read_demo`
- **S3 Results**: `s3://athena-results-bucket/pii/`
- **Permissions**: Full table access

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
