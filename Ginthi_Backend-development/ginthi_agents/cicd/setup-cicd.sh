#!/bin/bash

# AWS CI/CD Pipeline Setup Script
# This script sets up CodePipeline, CodeBuild projects, and required IAM roles
# Usage: ./setup-cicd.sh

set -e

# Configuration
AWS_REGION="ap-south-1"
AWS_ACCOUNT_ID="382806777834"
S3_ARTIFACT_BUCKET="ginthi-cicd-artifacts"
EKS_CLUSTER_NAME="ginthi-dataplane-dev"
CODE_COMMIT_REPO="Ginthi_Backend-development"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    command -v aws >/dev/null 2>&1 || { log_error "AWS CLI is required but not installed."; exit 1; }
    command -v jq >/dev/null 2>&1 || { log_error "jq is required but not installed. Install: brew install jq (macOS) or apt-get install jq (Linux)"; exit 1; }
    log_info "Prerequisites check passed!"
}

# Create S3 bucket for artifacts
create_s3_bucket() {
    log_info "Creating S3 bucket for CI/CD artifacts..."
    if aws s3 ls "s3://${S3_ARTIFACT_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
        if [ "$AWS_REGION" == "us-east-1" ]; then
            aws s3 mb s3://${S3_ARTIFACT_BUCKET} --region ${AWS_REGION}
        else
            aws s3 mb s3://${S3_ARTIFACT_BUCKET} --region ${AWS_REGION}
        fi
        aws s3api put-bucket-versioning --bucket ${S3_ARTIFACT_BUCKET} --versioning-configuration Status=Enabled
        log_info "S3 bucket created: ${S3_ARTIFACT_BUCKET}"
    else
        log_warn "S3 bucket already exists: ${S3_ARTIFACT_BUCKET}"
    fi
}

# Create IAM role for CodeBuild
create_codebuild_role() {
    log_info "Creating IAM role for CodeBuild..."
    
    ROLE_NAME="codebuild-auth-client-service-role"
    
    # Check if role exists
    if aws iam get-role --role-name ${ROLE_NAME} >/dev/null 2>&1; then
        log_warn "IAM role already exists: ${ROLE_NAME}"
    else
        # Create trust policy
        cat > /tmp/codebuild-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
        
        # Create role
        aws iam create-role \
            --role-name ${ROLE_NAME} \
            --assume-role-policy-document file:///tmp/codebuild-trust-policy.json
        
        # Attach policies
        aws iam put-role-policy \
            --role-name ${ROLE_NAME} \
            --policy-name CodeBuildPolicy \
            --policy-document file://$(dirname "$0")/iam-policies/codebuild-policy.json
        
        # Attach AWS managed policy for EKS access
        aws iam attach-role-policy \
            --role-name ${ROLE_NAME} \
            --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
        
        log_info "IAM role created: ${ROLE_NAME}"
    fi
    
    ROLE_ARN=$(aws iam get-role --role-name ${ROLE_NAME} --query 'Role.Arn' --output text)
    echo ${ROLE_ARN}
}

# Create CodeBuild project for auth-service
create_codebuild_project() {
    local SERVICE_NAME=$1
    log_info "Creating CodeBuild project for ${SERVICE_NAME}..."
    
    PROJECT_NAME="${SERVICE_NAME}-build"
    ROLE_ARN=$2
    
    # Check if project exists
    if aws codebuild list-projects --region ${AWS_REGION} | grep -q ${PROJECT_NAME}; then
        log_warn "CodeBuild project already exists: ${PROJECT_NAME}"
        log_info "Updating project..."
        UPDATE_FLAG="--update"
    else
        UPDATE_FLAG=""
    fi
    
    # Get buildspec path
    if [ "$SERVICE_NAME" == "auth-service" ]; then
        BUILDSPEC_PATH="ginthi_agents/auth_service/buildspec.yml"
    else
        BUILDSPEC_PATH="ginthi_agents/client_service/buildspec.yml"
    fi
    
    aws codebuild create-project ${UPDATE_FLAG} \
        --name ${PROJECT_NAME} \
        --region ${AWS_REGION} \
        --source "type=CODECOMMIT,location=https://git-codecommit.${AWS_REGION}.amazonaws.com/v1/repos/${CODE_COMMIT_REPO},buildspec=${BUILDSPEC_PATH}" \
        --artifacts "type=S3,location=${S3_ARTIFACT_BUCKET},name=${PROJECT_NAME},packaging=ZIP" \
        --environment "type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_SMALL,privilegedMode=true" \
        --service-role ${ROLE_ARN} \
        --timeout-in-minutes 60 \
        --queued-timeout-in-minutes 60 \
        > /dev/null
    
    log_info "CodeBuild project created/updated: ${PROJECT_NAME}"
}

# Create CodePipeline
create_codepipeline() {
    local SERVICE_NAME=$1
    log_info "Creating CodePipeline for ${SERVICE_NAME}..."
    
    PIPELINE_NAME="${SERVICE_NAME}-pipeline"
    PROJECT_NAME="${SERVICE_NAME}-build"
    
    # Check if pipeline exists
    if aws codepipeline get-pipeline --name ${PIPELINE_NAME} --region ${AWS_REGION} >/dev/null 2>&1; then
        log_warn "CodePipeline already exists: ${PIPELINE_NAME}"
        log_info "Updating pipeline..."
        UPDATE_FLAG="--update"
    else
        UPDATE_FLAG=""
    fi
    
    # Create pipeline JSON
    cat > /tmp/${PIPELINE_NAME}.json <<EOF
{
  "pipeline": {
    "name": "${PIPELINE_NAME}",
    "roleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/service-role/AWSCodePipelineServiceRole",
    "artifactStore": {
      "type": "S3",
      "location": "${S3_ARTIFACT_BUCKET}"
    },
    "stages": [
      {
        "name": "Source",
        "actions": [
          {
            "name": "SourceAction",
            "actionTypeId": {
              "category": "Source",
              "owner": "AWS",
              "provider": "CodeCommit",
              "version": "1"
            },
            "configuration": {
              "RepositoryName": "${CODE_COMMIT_REPO}",
              "BranchName": "main",
              "PollForSourceChanges": "true"
            },
            "outputArtifacts": [
              {
                "name": "SourceOutput"
              }
            ]
          }
        ]
      },
      {
        "name": "Build",
        "actions": [
          {
            "name": "BuildAction",
            "actionTypeId": {
              "category": "Build",
              "owner": "AWS",
              "provider": "CodeBuild",
              "version": "1"
            },
            "configuration": {
              "ProjectName": "${PROJECT_NAME}"
            },
            "inputArtifacts": [
              {
                "name": "SourceOutput"
              }
            ],
            "outputArtifacts": [
              {
                "name": "BuildOutput"
              }
            ]
          }
        ]
      }
    ]
  }
}
EOF
    
    if [ -z "$UPDATE_FLAG" ]; then
        aws codepipeline create-pipeline \
            --region ${AWS_REGION} \
            --cli-input-json file:///tmp/${PIPELINE_NAME}.json \
            > /dev/null
    else
        aws codepipeline update-pipeline \
            --region ${AWS_REGION} \
            --cli-input-json file:///tmp/${PIPELINE_NAME}.json \
            > /dev/null
    fi
    
    log_info "CodePipeline created/updated: ${PIPELINE_NAME}"
}

# Main execution
main() {
    log_info "Starting CI/CD setup..."
    
    check_prerequisites
    create_s3_bucket
    
    # Create CodeBuild IAM role
    ROLE_ARN=$(create_codebuild_role)
    log_info "CodeBuild Role ARN: ${ROLE_ARN}"
    
    # Create CodeBuild projects
    create_codebuild_project "auth-service" "${ROLE_ARN}"
    create_codebuild_project "client-service" "${ROLE_ARN}"
    
    # Create CodePipelines
    create_codepipeline "auth-service"
    create_codepipeline "client-service"
    
    log_info "CI/CD setup completed!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Ensure CodeCommit repository '${CODE_COMMIT_REPO}' exists"
    log_info "2. Ensure CodePipeline service role exists: AWSCodePipelineServiceRole"
    log_info "3. Push your code to CodeCommit to trigger the pipeline"
    log_info "4. Monitor pipelines in AWS Console: https://console.aws.amazon.com/codesuite/codepipeline/pipelines"
}

main "$@"

