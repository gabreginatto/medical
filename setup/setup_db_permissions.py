#!/usr/bin/env python3
"""
Setup database permissions for IAM service account
This script connects to Cloud SQL and grants necessary permissions
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector

load_dotenv()

async def setup_permissions():
    """Grant database permissions to IAM service account"""

    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    database_name = os.getenv('DATABASE_NAME')
    iam_user = "pncp-medical-app@medical-473219.iam"

    connection_name = f"{project_id}:{region}:{instance_name}"

    print("=" * 70)
    print("Setting up Database Permissions for IAM User")
    print("=" * 70)
    print(f"\nConnection: {connection_name}")
    print(f"Database: {database_name}")
    print(f"IAM User: {iam_user}")

    connector = Connector()

    try:
        print("\n1️⃣  Connecting to Cloud SQL using IAM authentication...")

        # Connect with IAM auth using your service account
        conn = await connector.connect_async(
            instance_connection_string=connection_name,
            driver="asyncpg",
            user=os.getenv('DB_USER'),  # Your IAM service account
            db=database_name,  # asyncpg uses 'db' not 'database'
            enable_iam_auth=True,
            ip_type="public"
        )

        print("   ✅ Connected successfully")

        print(f"\n2️⃣  Granting permissions to {iam_user}...")

        # Grant database connection
        await conn.execute(f'GRANT CONNECT ON DATABASE {database_name} TO "{iam_user}"')
        print("   ✅ Granted CONNECT")

        # Grant schema usage and create
        await conn.execute(f'GRANT USAGE, CREATE ON SCHEMA public TO "{iam_user}"')
        print("   ✅ Granted USAGE and CREATE on schema")

        # Grant permissions on all existing tables
        await conn.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{iam_user}"')
        print("   ✅ Granted table permissions")

        # Grant permissions on all existing sequences
        await conn.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{iam_user}"')
        print("   ✅ Granted sequence permissions")

        # Grant permissions on future tables
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{iam_user}"')
        print("   ✅ Granted default table privileges")

        # Grant permissions on future sequences
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "{iam_user}"')
        print("   ✅ Granted default sequence privileges")

        print("\n3️⃣  Verifying permissions...")
        # Check if user has permissions
        result = await conn.fetch("""
            SELECT grantee, privilege_type, table_schema, table_name
            FROM information_schema.role_table_grants
            WHERE grantee = $1
            LIMIT 5
        """, iam_user)

        if result:
            print(f"   ✅ User has {len(result)} granted permissions (showing first 5):")
            for row in result[:5]:
                print(f"      - {row['privilege_type']} on {row['table_schema']}.{row['table_name']}")
        else:
            print("   ⚠️  No permissions found in grants table (may need manual verification)")

        await conn.close()

        print("\n" + "=" * 70)
        print("✅ Database Permissions Setup Complete!")
        print("=" * 70)
        print(f"\nThe IAM user '{iam_user}' now has:")
        print("  • CONNECT privileges on database")
        print("  • USAGE privileges on public schema")
        print("  • SELECT, INSERT, UPDATE, DELETE on all tables")
        print("  • USAGE, SELECT on all sequences")
        print("  • Default privileges for future objects")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("  1. Ensure you're authenticated: gcloud auth application-default login")
        print("  2. Check your DB_USER in .env matches your service account")
        print("  3. Verify the service account has cloudsql.client role")
        raise

    finally:
        await connector.close_async()

if __name__ == "__main__":
    asyncio.run(setup_permissions())