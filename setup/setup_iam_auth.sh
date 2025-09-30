#!/bin/bash
# Setup IAM Authentication for Cloud SQL
# This script configures the service account with proper permissions

set -e

echo "=================================="
echo "Cloud SQL IAM Authentication Setup"
echo "=================================="

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found"
    exit 1
fi

# Verify required variables
if [ -z "$GOOGLE_CLOUD_PROJECT" ] || [ -z "$CLOUD_SQL_INSTANCE" ] || [ -z "$CLOUD_SQL_REGION" ]; then
    echo "❌ Missing required environment variables"
    echo "Required: GOOGLE_CLOUD_PROJECT, CLOUD_SQL_INSTANCE, CLOUD_SQL_REGION"
    exit 1
fi

echo ""
echo "📋 Configuration:"
echo "   Project: $GOOGLE_CLOUD_PROJECT"
echo "   Region: $CLOUD_SQL_REGION"
echo "   Instance: $CLOUD_SQL_INSTANCE"
echo ""

# Set project
echo "1️⃣  Setting GCloud project..."
gcloud config set project $GOOGLE_CLOUD_PROJECT

# Get default service account
DEFAULT_SA="${GOOGLE_CLOUD_PROJECT}@appspot.gserviceaccount.com"
COMPUTE_SA="$(gcloud iam service-accounts list --filter="email ~ compute@developer" --format="value(email)" | head -1)"

if [ -z "$COMPUTE_SA" ]; then
    echo "⚠️  Compute Engine default service account not found"
    echo "   Using App Engine default: $DEFAULT_SA"
    SERVICE_ACCOUNT=$DEFAULT_SA
else
    echo "✅ Found Compute Engine service account: $COMPUTE_SA"
    SERVICE_ACCOUNT=$COMPUTE_SA
fi

echo ""
echo "2️⃣  Granting Cloud SQL Client role to service account..."
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.client" \
    --condition=None

echo ""
echo "3️⃣  Granting Cloud SQL Instance User role..."
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.instanceUser" \
    --condition=None

echo ""
echo "4️⃣  Checking Cloud SQL instance status..."
INSTANCE_STATUS=$(gcloud sql instances describe $CLOUD_SQL_INSTANCE \
    --project=$GOOGLE_CLOUD_PROJECT \
    --format="value(state)" 2>/dev/null || echo "NOT_FOUND")

if [ "$INSTANCE_STATUS" = "NOT_FOUND" ]; then
    echo "❌ Cloud SQL instance '$CLOUD_SQL_INSTANCE' not found"
    echo ""
    echo "💡 To create the instance, run:"
    echo "   gcloud sql instances create $CLOUD_SQL_INSTANCE \\"
    echo "     --database-version=POSTGRES_15 \\"
    echo "     --tier=db-f1-micro \\"
    echo "     --region=$CLOUD_SQL_REGION \\"
    echo "     --network=default \\"
    echo "     --database-flags=cloudsql.iam_authentication=on"
    exit 1
elif [ "$INSTANCE_STATUS" != "RUNNABLE" ]; then
    echo "⚠️  Instance is in state: $INSTANCE_STATUS (waiting for RUNNABLE)"
    echo "   This may take a few minutes..."
else
    echo "✅ Instance is RUNNABLE"
fi

echo ""
echo "5️⃣  Enabling IAM authentication on the instance..."
gcloud sql instances patch $CLOUD_SQL_INSTANCE \
    --project=$GOOGLE_CLOUD_PROJECT \
    --database-flags=cloudsql.iam_authentication=on \
    --quiet || echo "⚠️  IAM authentication may already be enabled"

echo ""
echo "6️⃣  Creating IAM database user..."
# Extract username from service account email (part before @)
DB_IAM_USER=$(echo $SERVICE_ACCOUNT | cut -d'@' -f1 | tr '.' '_' | tr '-' '_')

echo "   Creating user: $DB_IAM_USER"
echo "   (mapped from: $SERVICE_ACCOUNT)"

# Try to create the IAM user
gcloud sql users create $DB_IAM_USER \
    --instance=$CLOUD_SQL_INSTANCE \
    --project=$GOOGLE_CLOUD_PROJECT \
    --type=CLOUD_IAM_SERVICE_ACCOUNT 2>/dev/null || echo "   (User may already exist)"

echo ""
echo "7️⃣  Setting up database permissions..."
echo "   You'll need to run these SQL commands to grant permissions:"
echo ""
echo "   -- Connect to your database:"
echo "   gcloud sql connect $CLOUD_SQL_INSTANCE --user=postgres --database=pncp_medical_data"
echo ""
echo "   -- Then run these SQL commands:"
echo "   GRANT CONNECT ON DATABASE pncp_medical_data TO \"$DB_IAM_USER\";"
echo "   GRANT USAGE ON SCHEMA public TO \"$DB_IAM_USER\";"
echo "   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"$DB_IAM_USER\";"
echo "   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"$DB_IAM_USER\";"
echo "   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \"$DB_IAM_USER\";"
echo "   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO \"$DB_IAM_USER\";"
echo ""

echo "=================================="
echo "✅ IAM Authentication Setup Complete"
echo "=================================="
echo ""
echo "📝 Update your .env file with:"
echo "   DB_USER=$SERVICE_ACCOUNT"
echo "   # Remove DB_PASSWORD (not needed with IAM auth)"
echo ""
echo "🔑 The service account will authenticate using your gcloud credentials"
echo ""
echo "⚠️  Don't forget to run the SQL grant commands above!"