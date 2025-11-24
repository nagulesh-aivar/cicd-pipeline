# Quick Start: EKS Cluster Setup

## Prerequisites Check

```bash
# Verify tools are installed
eksctl version
aws --version
kubectl version --client
helm version  # Optional, will be installed by script if missing
```

## Quick Setup (Automated)

```bash
cd /Users/aadhith/Documents/Projects/Ginthiai/Backendcode/Ginthi_Backend-development/ginthi_agents/k8s

# Make scripts executable
chmod +x setup-eks.sh deploy.sh

# Run automated setup (tags subnets, creates cluster, installs ALB controller)
./setup-eks.sh all
```

This will:
1. ✅ Tag VPC and subnets for EKS
2. ✅ Verify subnet configuration
3. ✅ Create EKS cluster (15-20 minutes)
4. ✅ Configure kubectl
5. ✅ Install AWS Load Balancer Controller
6. ✅ Install Metrics Server

## Manual Setup Steps

### Step 1: Tag VPC and Subnets

```bash
./setup-eks.sh tag
```

### Step 2: Verify Subnet Configuration

The script will show you which AZs your subnets are in. **Update `eks-cluster-config.yaml` if AZs don't match.**

### Step 3: Create Cluster

```bash
./setup-eks.sh create
```

### Step 4: Install AWS Load Balancer Controller

```bash
./setup-eks.sh alb
```

## After Cluster Creation

### 1. Update ConfigMaps and Secrets

Edit these files with your actual values:
- `auth-service-configmap.yaml` - Database host, port, name
- `auth-service-secrets.yaml` - Database credentials
- `client-service-configmap.yaml` - Database host, port, name
- `client-service-secrets.yaml` - Database credentials

### 2. Update Ingress

Edit `ingress.yaml`:
- Replace `<YOUR_ACM_CERTIFICATE_ARN>` with your ACM certificate ARN
- Update domain names (`api-auth.yourdomain.com`, `api-client.yourdomain.com`)

### 3. Build and Push Images

```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=ap-south-1

# Build and push
./deploy.sh build
./deploy.sh push
```

### 4. Deploy Services

```bash
./deploy.sh deploy
```

## Verify Deployment

```bash
# Check pods
kubectl get pods

# Check services
kubectl get svc

# Check ingress and get ALB DNS
kubectl get ingress
kubectl get ingress services-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

## Troubleshooting

### Cluster Creation Fails

```bash
# Check CloudFormation stacks
aws cloudformation describe-stacks --region ap-south-1 | grep ginthi-dataplane-dev

# Check eksctl logs
eksctl utils describe-stacks --region ap-south-1 --cluster ginthi-dataplane-dev
```

### Subnet Tagging Issues

```bash
# Re-run tagging
./setup-eks.sh tag
```

### Pods Not Starting

```bash
# Check logs
kubectl logs -l app=auth-service
kubectl logs -l app=client-service

# Describe pods
kubectl describe pod -l app=auth-service
```

## Important Notes

1. **Subnet Availability Zones**: The script will show you which AZs your subnets are in. Make sure `eks-cluster-config.yaml` matches.

2. **Subnet Types**: If you have separate public/private subnets, update the config file accordingly. ALB needs public subnets.

3. **Database Access**: Ensure your RDS security groups allow traffic from EKS node security groups.

4. **DNS Configuration**: After ALB is created, configure DNS records pointing to the ALB DNS name.

## Next Steps

- Set up monitoring (CloudWatch, Prometheus)
- Configure backup and disaster recovery
- Set up CI/CD pipelines
- Review security best practices

