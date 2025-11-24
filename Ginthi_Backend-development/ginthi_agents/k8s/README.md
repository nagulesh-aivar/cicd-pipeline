# EKS Deployment Guide for Auth Service and Client Service

This guide provides step-by-step instructions to deploy the `auth_service` and `client_service` to Amazon EKS and expose them publicly via Application Load Balancer (ALB).

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **EKS Cluster** already created
3. **kubectl** configured to connect to your EKS cluster
4. **AWS CLI** configured with appropriate credentials
5. **Docker** installed locally
6. **ECR Repository** created for storing Docker images
7. **RDS PostgreSQL** instances for databases (or existing databases)
8. **ACM Certificate** for HTTPS (optional but recommended)
9. **AWS Load Balancer Controller** installed in your EKS cluster

## Step 1: Install AWS Load Balancer Controller

The AWS Load Balancer Controller is required to create ALB resources from Kubernetes Ingress.

```bash
# Add the EKS chart repo
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Install AWS Load Balancer Controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=your-cluster-name \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# Verify installation
kubectl get deployment -n kube-system aws-load-balancer-controller
```

**Note:** You need to create an IAM service account with appropriate permissions. See [AWS documentation](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html) for details.

## Step 2: Build and Push Docker Images

### Build Images

```bash
# Navigate to the project root
cd /Users/aadhith/Documents/Projects/Ginthiai/Backendcode/Ginthi_Backend-development/ginthi_agents

# Build auth-service image
docker build -t auth-service:latest -f auth_service/Dockerfile auth_service/

# Build client-service image
docker build -t client-service:latest -f client_service/Dockerfile client_service/
```

### Tag and Push to ECR

```bash
# Set your AWS account ID and region
export AWS_ACCOUNT_ID=your-account-id
export AWS_REGION=your-region
export ECR_REPO_BASE=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO_BASE}

# Create ECR repositories (if not exists)
aws ecr create-repository --repository-name auth-service --region ${AWS_REGION} || true
aws ecr create-repository --repository-name client-service --region ${AWS_REGION} || true

# Tag images
docker tag auth-service:latest ${ECR_REPO_BASE}/auth-service:latest
docker tag client-service:latest ${ECR_REPO_BASE}/client-service:latest

# Push images
docker push ${ECR_REPO_BASE}/auth-service:latest
docker push ${ECR_REPO_BASE}/client-service:latest
```

## Step 3: Update Kubernetes Manifests

### Update Image References

Edit the deployment files and replace `<YOUR_ECR_REPO>` with your actual ECR repository URL:

```bash
# In auth-service-deployment.yaml
sed -i '' "s|<YOUR_ECR_REPO>|${ECR_REPO_BASE}|g" k8s/auth-service-deployment.yaml

# In client-service-deployment.yaml
sed -i '' "s|<YOUR_ECR_REPO>|${ECR_REPO_BASE}|g" k8s/client-service-deployment.yaml
```

### Update ConfigMaps

Edit `k8s/auth-service-configmap.yaml` and `k8s/client-service-configmap.yaml` with your actual database configuration:

- `DB_HOST`: Your RDS PostgreSQL endpoint
- `DB_PORT`: PostgreSQL port (usually 5432)
- `DB_NAME`: Your database name

### Update Secrets

**Important:** For production, use AWS Secrets Manager or External Secrets Operator instead of plain YAML files.

Edit `k8s/auth-service-secrets.yaml` and `k8s/client-service-secrets.yaml`:

```bash
# Create secrets using kubectl (more secure)
kubectl create secret generic auth-service-secrets \
  --from-literal=DB_USER=your_db_user \
  --from-literal=DB_PASSWORD=your_db_password \
  --namespace=default

kubectl create secret generic client-service-secrets \
  --from-literal=DB_USER=your_db_user \
  --from-literal=DB_PASSWORD=your_db_password \
  --namespace=default
```

Or update the YAML files and apply:

```bash
# Update the secret files with your actual values
# Then apply
kubectl apply -f k8s/auth-service-secrets.yaml
kubectl apply -f k8s/client-service-secrets.yaml
```

### Update Ingress Configuration

Edit `k8s/ingress.yaml`:

1. Replace `<YOUR_ACM_CERTIFICATE_ARN>` with your ACM certificate ARN (for HTTPS)
2. Update domain names:
   - `api-auth.yourdomain.com` → Your auth service domain
   - `api-client.yourdomain.com` → Your client service domain

Or use path-based routing on a single domain (uncomment the alternative configuration in the file).

## Step 4: Deploy to EKS

```bash
# Apply ConfigMaps
kubectl apply -f k8s/auth-service-configmap.yaml
kubectl apply -f k8s/client-service-configmap.yaml

# Apply Secrets
kubectl apply -f k8s/auth-service-secrets.yaml
kubectl apply -f k8s/client-service-secrets.yaml

# Apply Deployments and Services
kubectl apply -f k8s/auth-service-deployment.yaml
kubectl apply -f k8s/client-service-deployment.yaml

# Apply Ingress
kubectl apply -f k8s/ingress.yaml
```

## Step 5: Verify Deployment

### Check Pods

```bash
kubectl get pods -l app=auth-service
kubectl get pods -l app=client-service
```

### Check Services

```bash
kubectl get svc
```

### Check Ingress and ALB

```bash
# Get Ingress details
kubectl get ingress services-ingress

# Get ALB DNS name
kubectl get ingress services-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### Test Health Endpoints

```bash
# Get ALB DNS
ALB_DNS=$(kubectl get ingress services-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test auth service (if using subdomain routing)
curl http://${ALB_DNS} -H "Host: api-auth.yourdomain.com/health-check"

# Test client service
curl http://${ALB_DNS} -H "Host: api-client.yourdomain.com/health-check"
```

## Step 6: Configure DNS

After the ALB is created, configure your DNS records:

1. Get the ALB DNS name from the Ingress status
2. Create CNAME records in your DNS provider:
   - `api-auth.yourdomain.com` → ALB DNS name
   - `api-client.yourdomain.com` → ALB DNS name

Or use Route 53 alias records if using AWS Route 53.

## Troubleshooting

### Pods Not Starting

```bash
# Check pod logs
kubectl logs -l app=auth-service
kubectl logs -l app=client-service

# Describe pods for events
kubectl describe pod -l app=auth-service
```

### ALB Not Created

```bash
# Check AWS Load Balancer Controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Check Ingress events
kubectl describe ingress services-ingress
```

### Database Connection Issues

- Verify RDS security groups allow traffic from EKS nodes
- Check database credentials in secrets
- Verify database endpoint in ConfigMap

### Health Check Failures

- Ensure `/health-check` endpoint is accessible
- Check pod logs for application errors
- Verify resource limits are sufficient

## Scaling

To scale the services:

```bash
# Scale auth-service
kubectl scale deployment auth-service --replicas=3

# Scale client-service
kubectl scale deployment client-service --replicas=3
```

## Updating Deployments

When you need to update the services:

```bash
# Build and push new images
docker build -t auth-service:v1.1.0 -f auth_service/Dockerfile auth_service/
docker tag auth-service:v1.1.0 ${ECR_REPO_BASE}/auth-service:v1.1.0
docker push ${ECR_REPO_BASE}/auth-service:v1.1.0

# Update deployment
kubectl set image deployment/auth-service auth-service=${ECR_REPO_BASE}/auth-service:v1.1.0

# Or update the YAML and reapply
kubectl apply -f k8s/auth-service-deployment.yaml
```

## Security Best Practices

1. **Use AWS Secrets Manager** or External Secrets Operator instead of Kubernetes Secrets
2. **Enable Pod Security Policies** or Pod Security Standards
3. **Use Network Policies** to restrict pod-to-pod communication
4. **Enable ALB WAF** for additional protection
5. **Use IAM Roles for Service Accounts** (IRSA) for AWS resource access
6. **Enable encryption at rest** for EBS volumes
7. **Use HTTPS only** (redirect HTTP to HTTPS)
8. **Regularly update** base images and dependencies

## Cost Optimization

1. Use **Fargate** for serverless container execution
2. Configure **Horizontal Pod Autoscaler** (HPA) for automatic scaling
3. Use **Spot Instances** for non-production workloads
4. Configure **ALB idle timeout** appropriately
5. Monitor and optimize resource requests/limits

## Additional Resources

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)

