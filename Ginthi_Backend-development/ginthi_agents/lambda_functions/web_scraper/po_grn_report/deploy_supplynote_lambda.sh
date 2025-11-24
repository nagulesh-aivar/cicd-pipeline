#!/usr/bin/env bash
set -euo pipefail

#####################################
# CONFIGURATION (read from ENV)
#####################################

# Load local .env file if it exists
if [ -f .env ]; then
  echo "🔧 Loading environment variables from .env..."
  set -o allexport
  source .env
  set +o allexport
fi

# Required: fill or export these before running
ECR_URI=${ECR_URI:-"1234567890.dkr.ecr.ap-south-1.amazonaws.com/supplynote-scraper"}
LAMBDA_NAME=${LAMBDA_NAME:-"supplynote-scraper"}
AWS_REGION=${AWS_REGION:-"ap-south-1"}

# Optional:
IMAGE_TAG=${IMAGE_TAG:-"latest"}
DOCKER_IMAGE_NAME=${DOCKER_IMAGE_NAME:-"supplynote-scraper"}
LAMBDA_ROLE_ARN=${LAMBDA_ROLE_ARN:-""}

#####################################
# AWS CREDENTIALS SETUP
#####################################

# Expect credentials from environment or .env
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-""}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-""}
AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-""}  # optional

#environment variables check
SUPPLYNOTE_EMAIL=${SUPPLYNOTE_EMAIL:-""}
SUPPLYNOTE_PASSWORD=${SUPPLYNOTE_PASSWORD:-""}
SUPPLYNOTE_BASE_URL=${SUPPLYNOTE_BASE_URL:-""}
S3_BUCKET=${S3_BUCKET:-""}


if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" ]]; then
  echo "❌ Missing AWS credentials! Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env or environment."
  exit 1
fi

echo "🔐 Configuring AWS CLI credentials for region $AWS_REGION ..."
aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID"
aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY"
aws configure set default.region "$AWS_REGION"

if [[ -n "$AWS_SESSION_TOKEN" ]]; then
  aws configure set aws_session_token "$AWS_SESSION_TOKEN"
fi

#####################################
# BUILD + DEPLOY
#####################################

echo "🚀 Starting Lambda Docker deploy..."
echo "Region: $AWS_REGION"
echo "ECR URI: $ECR_URI"
echo "Lambda Name: $LAMBDA_NAME"
echo "Image Tag: $IMAGE_TAG"
echo "-----------------------------------"

# Step 1: Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$(echo "$ECR_URI" | cut -d'/' -f1)"

# Step 2: Build Docker image for Lambda (Lambda requires linux/amd64)
echo "🏗️  Building Docker image..."
docker buildx build --platform linux/amd64 -t "$DOCKER_IMAGE_NAME" .

# Step 3: Tag the image
FULL_IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"
echo "🏷️  Tagging image as $FULL_IMAGE_URI"
docker tag "${DOCKER_IMAGE_NAME}:latest" "$FULL_IMAGE_URI"

# Step 4: Push to ECR
echo "⬆️  Pushing image to ECR..."
docker push "$FULL_IMAGE_URI"

# Step 5: Deploy to Lambda
echo "🌀 Checking if Lambda function exists..."
set +e
aws lambda get-function --function-name "$LAMBDA_NAME" --region "$AWS_REGION" >/dev/null 2>&1
EXISTS=$?
set -e

if [[ $EXISTS -ne 0 ]]; then
  if [[ -z "$LAMBDA_ROLE_ARN" ]]; then
    echo "❌ Lambda function doesn't exist. Please set LAMBDA_ROLE_ARN to create it."
    exit 1
  fi

  echo "🆕 Creating new Lambda function $LAMBDA_NAME ..."
  aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --package-type Image \
    --code ImageUri="$FULL_IMAGE_URI" \
    --role "$LAMBDA_ROLE_ARN" \
    --timeout 300 \
    --memory-size 1024 \
    --region "$AWS_REGION"
else
  echo "♻️  Updating existing Lambda function code with new image..."
  aws lambda update-function-code \
    --function-name "$LAMBDA_NAME" \
    --image-uri "$FULL_IMAGE_URI" \
    --region "$AWS_REGION"
fi

echo "⏳ Waiting for Lambda to finish updating..."
aws lambda wait function-updated --function-name "$LAMBDA_NAME" --region "$AWS_REGION"

echo "✅ Deployment complete!"
echo "Lambda [$LAMBDA_NAME] now running image: $FULL_IMAGE_URI"

# Optional: update environment variables after deploy
if [[ -n "${SUPPLYNOTE_EMAIL:-}" && -n "${SUPPLYNOTE_PASSWORD:-}" ]]; then
  echo "🌍 Updating Lambda environment variables..."
  aws lambda update-function-configuration \
    --function-name "$LAMBDA_NAME" \
    --region "$AWS_REGION" \
    --environment "Variables={SUPPLYNOTE_EMAIL=$SUPPLYNOTE_EMAIL,SUPPLYNOTE_PASSWORD=$SUPPLYNOTE_PASSWORD,S3_BUCKET=$S3_BUCKET}"
fi
echo "✅ Environment variables updated."