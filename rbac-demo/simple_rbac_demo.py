#!/usr/bin/env python3

"""
Simplified RBAC demonstration using Lake Formation with Athena.
This version uses the Lake Formation admin role to set up permissions.
"""

import boto3
import time

def get_admin_session():
    """Get session using Lake Formation admin role"""
    sts = boto3.client("sts")
    admin_role_arn = "arn:aws:iam::047719628777:role/OptionAIngestionDemoPy-LFAdminRoleE5DF1BFB-fZnZVF27Yd2E"
    
    response = sts.assume_role(
        RoleArn=admin_role_arn,
        RoleSessionName="lf-admin-demo"
    )
    
    credentials = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name="us-west-2"
    )

def get_role_arns():
    """Get the analyst role ARNs"""
    iam = boto3.client("iam")
    roles = iam.list_roles()["Roles"]
    
    core_role = None
    pii_role = None
    
    for role in roles:
        if "AnalystCoreRole" in role["RoleName"]:
            core_role = role["Arn"]
        elif "AnalystPiiRole" in role["RoleName"]:
            pii_role = role["Arn"]
    
    return core_role, pii_role

def setup_lake_formation_permissions(session):
    """Set up Lake Formation permissions using admin role"""
    lf = session.client("lakeformation")
    account_id = "047719628777"
    db_name = "option_a_demo_db"
    table_name = "raw"
    
    core_role, pii_role = get_role_arns()
    
    print(f"Core Role: {core_role}")
    print(f"PII Role: {pii_role}")
    
    # Grant SELECT permission to both roles on the table
    try:
        lf.grant_permissions(
            Principal={"DataLakePrincipalIdentifier": core_role},
            Resource={"Table": {"CatalogId": account_id, "DatabaseName": db_name, "Name": table_name}},
            Permissions=["SELECT"]
        )
        print("✅ Granted SELECT permission to Core role")
    except Exception as e:
        print(f"❌ Failed to grant permission to Core role: {e}")
    
    try:
        lf.grant_permissions(
            Principal={"DataLakePrincipalIdentifier": pii_role},
            Resource={"Table": {"CatalogId": account_id, "DatabaseName": db_name, "Name": table_name}},
            Permissions=["SELECT"]
        )
        print("✅ Granted SELECT permission to PII role")
    except Exception as e:
        print(f"❌ Failed to grant permission to PII role: {e}")

def test_role_access():
    """Test access using different roles"""
    core_role, pii_role = get_role_arns()
    
    # Test Core role
    print("\n🔍 Testing Core Role Access...")
    try:
        sts = boto3.client("sts")
        core_response = sts.assume_role(
            RoleArn=core_role,
            RoleSessionName="core-test"
        )
        
        core_session = boto3.Session(
            aws_access_key_id=core_response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=core_response["Credentials"]["SecretAccessKey"],
            aws_session_token=core_response["Credentials"]["SessionToken"],
            region_name="us-west-2"
        )
        
        athena = core_session.client("athena")
        query_id = athena.start_query_execution(
            QueryString='SELECT source, COUNT(*) as files FROM "option_a_demo_db"."raw" GROUP BY source ORDER BY source',
            QueryExecutionContext={"Database": "option_a_demo_db"},
            WorkGroup="wg_core_read_demo"
        )["QueryExecutionId"]
        
        # Wait for completion
        while True:
            status = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]["Status"]["State"]
            if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            time.sleep(1)
        
        if status == "SUCCEEDED":
            results = athena.get_query_results(QueryExecutionId=query_id)
            print("✅ Core role query succeeded!")
            print("Results:")
            for row in results["ResultSet"]["Rows"][1:]:  # Skip header
                data = [d.get("VarCharValue", "") for d in row["Data"]]
                print(f"  {data[0]}: {data[1]} files")
        else:
            print(f"❌ Core role query failed: {status}")
            
    except Exception as e:
        print(f"❌ Core role test failed: {e}")
    
    # Test PII role
    print("\n🔍 Testing PII Role Access...")
    try:
        pii_response = sts.assume_role(
            RoleArn=pii_role,
            RoleSessionName="pii-test"
        )
        
        pii_session = boto3.Session(
            aws_access_key_id=pii_response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=pii_response["Credentials"]["SecretAccessKey"],
            aws_session_token=pii_response["Credentials"]["SessionToken"],
            region_name="us-west-2"
        )
        
        athena = pii_session.client("athena")
        query_id = athena.start_query_execution(
            QueryString='SELECT source, COUNT(*) as files FROM "option_a_demo_db"."raw" GROUP BY source ORDER BY source',
            QueryExecutionContext={"Database": "option_a_demo_db"},
            WorkGroup="wg_pii_read_demo"
        )["QueryExecutionId"]
        
        # Wait for completion
        while True:
            status = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]["Status"]["State"]
            if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            time.sleep(1)
        
        if status == "SUCCEEDED":
            results = athena.get_query_results(QueryExecutionId=query_id)
            print("✅ PII role query succeeded!")
            print("Results:")
            for row in results["ResultSet"]["Rows"][1:]:  # Skip header
                data = [d.get("VarCharValue", "") for d in row["Data"]]
                print(f"  {data[0]}: {data[1]} files")
        else:
            print(f"❌ PII role query failed: {status}")
            
    except Exception as e:
        print(f"❌ PII role test failed: {e}")

def main():
    print("🚀 Lake Formation RBAC Demo")
    print("=" * 50)
    
    # Get admin session
    admin_session = get_admin_session()
    print("✅ Got Lake Formation admin session")
    
    # Set up permissions
    print("\n🔧 Setting up Lake Formation permissions...")
    setup_lake_formation_permissions(admin_session)
    
    # Test role access
    print("\n🧪 Testing role-based access...")
    test_role_access()
    
    print("\n🎉 Demo completed!")

if __name__ == "__main__":
    main()
