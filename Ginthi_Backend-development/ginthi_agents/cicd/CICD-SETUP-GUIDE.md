# AWS CI/CD Pipeline Setup Guide

This guide will help you set up automated CI/CD pipelines for `auth-service` and `client-service` using AWS CodePipeline and CodeBuild.

## Architecture Overview

```
CodeCommit (Source) → CodePipeline → CodeBuild → ECR → EKS
```

## Prerequisites

1. **AWS CLI** installed and configured
2. **jq** installed (`brew install jq` on macOS, `apt-get install jq` on Linux)
3. **AWS Account** with appropriate permissions
4. **CodeCommit Repository** created (or GitHub/GitLab with webhook)
5. **ECR Repositories** already exist:
   - `auth-service-dev`
   - `client-service-dev`
6. **EKS Cluster** already configured: `ginthi-dataplane-dev`

## Step 1: Create Required IAM Roles

### 1.1 CodePipeline Service Role

If not already created, create the CodePipeline service role:

```bash
aws iam create-role \
    --role-name AWSCodePipelineServiceRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "codepipeline.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

# Attach the policy from cicd/iam-policies/codepipeline-policy.json
aws iam put-role-policy \
    --role-name AWSCodePipelineServiceRole \
    --policy-name CodePipelinePolicy \
    --policy-document file://cicd/iam-policies/codepipeline-policy.json
```

### 1.2 CodeBuild Service Role

The setup script will create this automatically, or you can create it manually:

```bash
# Create trust policy
cat > codebuild-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "codebuild.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create role
aws iam create-role \
    --role-name codebuild-auth-client-service-role \
    --assume-role-policy-document file://codebuild-trust-policy.json

# Attach policies
aws iam put-role-policy \
    --role-name codebuild-auth-client-service-role \
    --policy-name CodeBuildPolicy \
    --policy-document file://cicd/iam-policies/codebuild-policy.json

# Attach EKS policy
aws iam attach-role-policy \
    --role-name codebuild-auth-client-service-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
```

## Step 2: Create S3 Bucket for Artifacts

```bash
aws s3 mb s3://ginthi-cicd-artifacts --region ap-south-1
aws s3api put-bucket-versioning \
    --bucket ginthi-cicd-artifacts \
    --versioning-configuration Status=Enabled
```

## Step 3: Run Setup Script

```bash
cd cicd
chmod +x setup-cicd.sh
./setup-cicd.sh
```

This script will:
- Create S3 bucket for artifacts
- Create IAM roles for CodeBuild
- Create CodeBuild projects for both services
- Create CodePipeline pipelines for both services

## Step 4: Configure Source Repository

### Option A: Using CodeCommit (Recommended for AWS-native setup)

1. **Create CodeCommit Repository** (if not exists):
```bash
aws codecommit create-repository \
    --repository-name Ginthi_Backend-development \
    --region ap-south-1
```

2. **Push your code to CodeCommit**:
```bash
# Add CodeCommit as remote
git remote add codecommit https://git-codecommit.ap-south-1.amazonaws.com/v1/repos/Ginthi_Backend-development

# Push to CodeCommit
git push codecommit main
```

### Option B: Using GitHub

1. **Create GitHub Connection in AWS**:
   - Go to AWS Console → Developer Tools → Settings → Connections
   - Create a new GitHub connection
   - Authorize AWS to access your GitHub account

2. **Update Pipeline Configuration**:
   - Edit `cicd/pipeline-configs/auth-service-pipeline.json`
   - Change source provider from `CodeCommit` to `GitHub`
   - Add connection ARN and repository details

### Option C: Using GitLab

Similar to GitHub, create a GitLab connection and update pipeline configuration.

## Step 5: Verify Pipeline Setup

1. **Check CodeBuild Projects**:
```bash
aws codebuild list-projects --region ap-south-1
```

2. **Check CodePipelines**:
```bash
aws codepipeline list-pipelines --region ap-south-1
```

3. **View in AWS Console**:
   - CodePipeline: https://console.aws.amazon.com/codesuite/codepipeline/pipelines
   - CodeBuild: https://console.aws.amazon.com/codesuite/codebuild/projects

## Step 6: Trigger Pipeline

### Manual Trigger
```bash
# Start pipeline execution
aws codepipeline start-pipeline-execution \
    --name auth-service-pipeline \
    --region ap-south-1
```

### Automatic Trigger
Pipelines are configured to automatically trigger on:
- Code commits to `main` branch (CodeCommit)
- Pull request merges (GitHub/GitLab)

## Step 7: Monitor Pipeline Execution

1. **View Pipeline Status**:
```bash
aws codepipeline get-pipeline-state \
    --name auth-service-pipeline \
    --region ap-south-1
```

2. **View Build Logs**:
```bash
# Get latest build ID
BUILD_ID=$(aws codebuild list-builds-for-project \
    --project-name auth-service-build \
    --region ap-south-1 \
    --query 'ids[0]' --output text)

# Get build logs
aws codebuild batch-get-builds \
    --ids ${BUILD_ID} \
    --region ap-south-1
```

3. **Check EKS Deployment**:
```bash
kubectl get pods -l app=auth-service
kubectl get pods -l app=client-service
```

## Pipeline Flow

### Auth Service Pipeline

1. **Source Stage**: 
   - Monitors CodeCommit repository
   - Triggers on commits to `main` branch
   - Downloads source code

2. **Build Stage**:
   - Runs `buildspec.yml` from `auth_service/` directory
   - Builds Docker image
   - Pushes to ECR: `382806777834.dkr.ecr.ap-south-1.amazonaws.com/auth-service-dev:latest`
   - Updates Kubernetes deployment

3. **Deploy Stage** (in buildspec):
   - Configures kubectl for EKS cluster
   - Updates deployment with new image
   - Waits for rollout to complete

### Client Service Pipeline

Same flow as auth-service, but for `client-service-dev` repository.

## Customization

### Change Image Tag Strategy

Edit `buildspec.yml` to use different tagging:

```yaml
# Use commit hash
IMAGE_TAG=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)

# Use branch name
IMAGE_TAG=$(echo $CODEBUILD_SOURCE_VERSION | cut -d'/' -f2)

# Use timestamp
IMAGE_TAG=$(date +%Y%m%d-%H%M%S)
```

### Add Testing Stage

Add a test phase in `buildspec.yml`:

```yaml
phases:
  pre_build:
    commands:
      - echo Installing dependencies...
      - pip install -r requirements.txt
      - pip install pytest pytest-cov
  
  build:
    commands:
      - echo Running tests...
      - pytest --cov=auth_service --cov-report=xml
      - echo Building Docker image...
      # ... rest of build commands
```

### Add Manual Approval

Add approval stage in pipeline configuration:

```json
{
  "name": "Approval",
  "actions": [{
    "name": "ManualApproval",
    "actionTypeId": {
      "category": "Approval",
      "owner": "AWS",
      "provider": "Manual",
      "version": "1"
    }
  }]
}
```

### Environment-Specific Deployments

Create separate pipelines for dev/staging/prod:

```bash
# Dev pipeline (current)
auth-service-pipeline-dev

# Staging pipeline
auth-service-pipeline-staging

# Production pipeline
auth-service-pipeline-prod
```

Update `buildspec.yml` to use environment-specific variables:

```yaml
env:
  variables:
    ENVIRONMENT: "dev"  # or "staging", "prod"
    ECR_REPOSITORY: "auth-service-${ENVIRONMENT}"
    EKS_CLUSTER_NAME: "ginthi-dataplane-${ENVIRONMENT}"
```

## Troubleshooting

### Pipeline Fails at Source Stage

- **Issue**: Cannot access repository
- **Solution**: Check IAM permissions for CodePipeline service role
- **Check**: `aws iam get-role-policy --role-name AWSCodePipelineServiceRole --policy-name CodePipelinePolicy`

### Build Fails with ECR Permission Denied

- **Issue**: CodeBuild cannot push to ECR
- **Solution**: Verify CodeBuild role has ECR permissions
- **Check**: `aws iam get-role-policy --role-name codebuild-auth-client-service-role --policy-name CodeBuildPolicy`

### Deployment Fails with kubectl Error

- **Issue**: Cannot connect to EKS cluster
- **Solution**: 
  1. Ensure CodeBuild role has EKS permissions
  2. Check EKS cluster name is correct
  3. Verify kubectl is installed in CodeBuild environment (it is in standard:7.0 image)

### Image Not Updating in Kubernetes

- **Issue**: Deployment shows old image
- **Solution**: 
  1. Check if `kubectl set image` command succeeded
  2. Verify image tag is correct
  3. Check deployment rollout status: `kubectl rollout status deployment/auth-service`

## Cost Optimization

1. **Use Spot Instances for CodeBuild**:
   - Add to CodeBuild project: `computeType=BUILD_GENERAL1_SMALL_SPOT`

2. **Set Build Timeout**:
   - Already configured: `timeout-in-minutes: 60`

3. **Clean Up Old Artifacts**:
   - Set S3 lifecycle policy to delete artifacts older than 30 days

## Security Best Practices

1. **Use Secrets Manager for Sensitive Data**:
   - Store database credentials in AWS Secrets Manager
   - Reference in buildspec: `env.parameter-store`

2. **Scan Docker Images**:
   - Enable ECR image scanning
   - Add security scanning step in buildspec

3. **Use Least Privilege IAM Roles**:
   - Only grant necessary permissions
   - Regularly audit IAM policies

## Next Steps

1. Set up notifications (SNS) for pipeline failures
2. Add integration tests in build stage
3. Set up blue/green deployments
4. Configure monitoring and alerting
5. Add rollback mechanism

## Support

For issues or questions:
- Check AWS CodePipeline documentation
- Review build logs in CodeBuild console
- Check Kubernetes events: `kubectl describe deployment/auth-service`

