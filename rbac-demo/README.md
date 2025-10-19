# Lake Formation RBAC Demo

This folder contains all the files needed to demonstrate and test Lake Formation Role-Based Access Control (RBAC) with the data lake.

## 📁 Files Overview

### 📋 Documentation
- **`DEMO_RBAC_README.md`** - Complete setup and usage guide
- **`README.md`** - This overview file

### 🔧 Setup Scripts
- **`setup_rbac_permissions.sh`** - Automated permission configuration script
- **`test_rbac.py`** - Basic RBAC functionality test

### 🎭 Demo Scripts
- **`demo_rbac.py`** - Advanced RBAC demo with row/column-level controls
- **`simple_rbac_demo.py`** - Simplified RBAC demonstration

## 🔍 Demo Script Comparison

### **`simple_rbac_demo.py` (186 lines)**
**Purpose**: **Basic RBAC testing** - Simple permission verification

**What it does**:
- ✅ **Uses Lake Formation admin role** to set up permissions
- ✅ **Basic permission grants** (DATA_LOCATION_ACCESS, DESCRIBE, SELECT)
- ✅ **Simple query test** - just counts files by source
- ✅ **Role assumption testing** for both Core and PII roles
- ✅ **Hardcoded values** (account ID, role ARNs)

**Key Features**:
- 🔧 **Admin role setup** - Uses `LFAdminRole` to configure permissions
- 📊 **Basic query** - `SELECT source, COUNT(*) FROM table GROUP BY source`
- 🎯 **Simple validation** - Just checks if roles can query successfully

**When to use**:
- 🧪 **Testing basic setup** - Quick validation that roles work
- 🔧 **Debugging permissions** - Simple permission verification
- ⚡ **Fast validation** - Quick check after setup

---

### **`demo_rbac.py` (177 lines)**
**Purpose**: **Advanced RBAC demonstration** - Full security showcase

**What it does**:
- ✅ **Creates Data Cells Filter** for row-level security
- ✅ **Column-level security** - restricts access to specific columns
- ✅ **Advanced query testing** - multiple queries showing different access levels
- ✅ **Dynamic role discovery** - finds roles by name pattern
- ✅ **Comprehensive error handling** and validation

**Key Features**:
- 🔒 **Row-level security** - Data Cells Filter limiting to `api-a` and `api-b`
- 🔒 **Column-level security** - Core role cannot access `items` column
- 📊 **Multiple queries** - Shows different results based on permissions
- 🎯 **Advanced validation** - Proves both row and column restrictions work

**When to use**:
- 🎭 **Demonstrating RBAC** - Showing stakeholders the security features
- 📊 **Full security showcase** - Proving row and column-level security
- 🎓 **Training/education** - Teaching Lake Formation capabilities
- 📋 **Compliance demos** - Showing fine-grained access controls

### **📋 Quick Comparison Table**

| Feature | `simple_rbac_demo.py` | `demo_rbac.py` |
|---------|----------------------|----------------|
| **Complexity** | Basic | Advanced |
| **Purpose** | Permission testing | Security demonstration |
| **Row Security** | ❌ No Data Cells Filter | ✅ Data Cells Filter |
| **Column Security** | ❌ No column restrictions | ✅ Column-level restrictions |
| **Query Types** | 1 simple query | 2+ complex queries |
| **Role Discovery** | Hardcoded ARNs | Dynamic discovery |
| **Error Handling** | Basic | Comprehensive |
| **Use Case** | Quick validation | Stakeholder demo |

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

### 3. Test Basic RBAC
```bash
python test_rbac.py
```

### 4. Run Simple Demo (Optional)
```bash
python simple_rbac_demo.py
```

### 5. Run Advanced Demo
```bash
python demo_rbac.py --stack OptionAIngestionDemoPy
```

## 📊 What the Demo Shows

### Basic RBAC Test (`test_rbac.py`)
- ✅ Core Role can query data using `wg_core_read_demo` workgroup
- ✅ PII Role can query data using `wg_pii_read_demo` workgroup
- ✅ Results are segregated in separate S3 paths (`/core/` vs `/pii/`)

### Simple RBAC Demo (`simple_rbac_demo.py`)
- 🔧 **Admin role setup**: Uses `LFAdminRole` to configure basic permissions
- 📊 **Basic query validation**: Simple count query to verify role access
- ✅ **Permission verification**: Confirms both roles can query successfully
- ⚡ **Quick testing**: Fast validation of RBAC setup

### Advanced RBAC Demo (`demo_rbac.py`)
- 🔒 **Row-level security**: Core role limited to `api-a` and `api-b` sources
- 🔒 **Column-level security**: Core role cannot access `items` column
- 🔓 **Full access**: PII role can access all sources and columns
- 📈 **Query comparison**: Shows different results based on role permissions

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
