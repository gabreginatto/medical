-- Grant permissions to IAM service account user
-- Run this with: gcloud sql connect pncp-medical-db --user=postgres --database=pncp_medical_data < grant_iam_permissions.sql

-- Connect to the database
\c pncp_medical_data;

-- Grant database connection
GRANT CONNECT ON DATABASE pncp_medical_data TO "pncp-medical-app@medical-473219.iam";

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO "pncp-medical-app@medical-473219.iam";

-- Grant permissions on all existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "pncp-medical-app@medical-473219.iam";

-- Grant permissions on all existing sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "pncp-medical-app@medical-473219.iam";

-- Grant permissions on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "pncp-medical-app@medical-473219.iam";

-- Grant permissions on future sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "pncp-medical-app@medical-473219.iam";

-- Verify grants
\dp