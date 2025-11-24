# EKS Cluster Setup Guide using eksctl

This guide walks you through creating an EKS cluster named `ginthi-dataplane-dev` in the `ap-south-1` region using your existing VPC and subnets.

## Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   aws --version
   aws configure  # If not already configured
   ```

2. **eksctl** installed
   ```bash
   # macOS
   brew tap weaveworks/tap
   brew install weaveworks/tap/eksctl
   
   # Linux
   curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
   sudo mv /tmp/eksctl /usr/local/bin
   
   # Verify installation
   eksctl version
   ```

3. **kubectl** installed
   ```bash
   # macOS
   brew install kubectl
   
   # Linux
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
   
   # Verify installation
   kubectl version --client
   ```

4. **Verify AWS Permissions**
   - Ensure your AWS credentials have permissions to create EKS clusters, IAM roles, and VPC resources
   - Required IAM permissions: `AmazonEKSClusterPolicy`, `AmazonEKSVPCResourceController`, etc.

## Step 1: Verify VPC and Subnet Configuration

Before creating the cluster, verify that your VPC and subnets are properly configured:

```bash
# Check VPC details
aws ec2 describe-vpcs --vpc-ids vpc-03438362cd9251fe7 --region ap-south-1

# Check subnet details
aws ec2 describe-subnets \
  --subnet-ids subnet-09769ec6dcf8dc16e subnet-00ab51323c6d99c00 subnet-0d60e0c6f3c58ca6f \
  --region ap-south-1

# Verify subnets have required tags for EKS
# EKS requires specific tags on subnets. Check if they exist:
aws ec2 describe-subnets \
  --subnet-ids subnet-09769ec6dcf8dc16e subnet-00ab51323c6d99c00 subnet-0d60e0c6f3c58ca6f \
  --region ap-south-1 \
  --query 'Subnets[*].[SubnetId,Tags]'
```

**Important:** If your subnets don't have the required EKS tags, you'll need to add them:

```bash
# Tag subnets for EKS (replace with your actual cluster name)
CLUSTER_NAME="ginthi-dataplane-dev"
SUBNETS=("subnet-09769ec6dcf8dc16e" "subnet-00ab51323c6d99c00" "subnet-0d60e0c6f3c58ca6f")

for subnet in "${SUBNETS[@]}"; do
  aws ec2 create-tags \
    --resources $subnet \
    --tags "Key=kubernetes.io/role/internal-elb,Value=1" \
            "Key=kubernetes.io/role/elb,Value=1" \
            "Key=kubernetes.io/cluster/${CLUSTER_NAME},Value=shared" \
    --region ap-south-1
done

# Tag VPC
aws ec2 create-tags \
  --resources vpc-03438362cd9251fe7 \
  --tags "Key=kubernetes.io/cluster/${CLUSTER_NAME},Value=shared" \
  --region ap-south-1
```

## Step 2: Review Cluster Configuration

Review the cluster configuration file `eks-cluster-config.yaml`:

```bash
cd /Users/aadhith/Documents/Projects/Ginthiai/Backendcode/Ginthi_Backend-development/ginthi_agents/k8s
cat eks-cluster-config.yaml
```

**Key Configuration Points:**
- **Cluster Name**: `ginthi-dataplane-dev`
- **Region**: `ap-south-1`
- **VPC**: `vpc-03438362cd9251fe7`
- **Subnets**: Your 3 subnets across availability zones
- **Node Group**: `t3.medium` instances, 2-5 nodes
- **OIDC Provider**: Enabled (required for AWS Load Balancer Controller)

**Adjust if needed:**
- Instance type (currently `t3.medium`)
- Node group size (currently 2-5 nodes)
- Kubernetes version (currently 1.28)

## Step 3: Create the EKS Cluster

### Option A: Using the Configuration File (Recommended)

```bash
# Create the cluster (this will take 15-20 minutes)
eksctl create cluster -f eks-cluster-config.yaml

# Monitor the creation process
eksctl utils describe-stacks --region ap-south-1 --cluster ginthi-dataplane-dev
```

### Option B: Using Command Line (Alternative)

If you prefer command-line options:

```bash
eksctl create cluster \
  --name ginthi-dataplane-dev \
  --region ap-south-1 \
  --vpc-public-subnets subnet-09769ec6dcf8dc16e,subnet-00ab51323c6d99c00,subnet-0d60e0c6f3c58ca6f \
  --vpc-private-subnets subnet-09769ec6dcf8dc16e,subnet-00ab51323c6d99c00,subnet-0d60e0c6f3c58ca6f \
  --nodegroup-name ginthi-ng-general \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 5 \
  --with-oidc \
  --ssh-access=false \
  --managed
```

## Step 4: Configure kubectl

After the cluster is created, configure kubectl:

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --region ap-south-1 \
  --name ginthi-dataplane-dev

# Verify connection
kubectl cluster-info
kubectl get nodes
```

## Step 5: Verify Cluster Status

```bash
# Check cluster status
eksctl get cluster --name ginthi-dataplane-dev --region ap-south-1

# Check node group status
eksctl get nodegroup --cluster ginthi-dataplane-dev --region ap-south-1

# Verify nodes are ready
kubectl get nodes -o wide

# Check system pods
kubectl get pods -n kube-system
```

## Step 6: Install AWS Load Balancer Controller

The AWS Load Balancer Controller is required for the ALB Ingress to work.

### 6.1: Create IAM Policy

```bash
# Download the IAM policy
curl -O https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.0/docs/install/iam_policy.json

# Create the policy
aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam_policy.json \
  --region ap-south-1
```

Note the Policy ARN from the output.

### 6.2: Create Service Account

```bash
# Get your AWS Account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get OIDC issuer URL
export OIDC_ID=$(aws eks describe-cluster \
  --name ginthi-dataplane-dev \
  --region ap-south-1 \
  --query "cluster.identity.oidc.issuer" \
  --output text | sed -e "s/^https:\/\///")

# Check if OIDC provider exists
aws iam list-open-id-connect-providers | grep $OIDC_ID

# If it doesn't exist, create it
eksctl utils associate-iam-oidc-provider \
  --cluster ginthi-dataplane-dev \
  --region ap-south-1 \
  --approve

# Create service account with IAM role
eksctl create iamserviceaccount \
  --cluster ginthi-dataplane-dev \
  --namespace kube-system \
  --name aws-load-balancer-controller \
  --role-name AmazonEKSLoadBalancerControllerRole \
  --attach-policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy \
  --region ap-south-1 \
  --approve
```

### 6.3: Install AWS Load Balancer Controller using Helm

```bash
# Add the EKS chart repo
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Install AWS Load Balancer Controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=ginthi-dataplane-dev \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set region=ap-south-1

# Verify installation
kubectl get deployment -n kube-system aws-load-balancer-controller
kubectl logs -n kube-system deployment/aws-load-balancer-controller
```

## Step 7: Install Metrics Server (Optional but Recommended)

Metrics Server is needed for HPA (Horizontal Pod Autoscaler):

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify
kubectl get deployment metrics-server -n kube-system
```

## Step 8: Verify Everything is Ready

```bash
# Check all system components
kubectl get pods -n kube-system

# Check nodes
kubectl get nodes

# Test cluster connectivity
kubectl run test-pod --image=busybox --rm -it --restart=Never -- echo "Cluster is working!"
```

## Step 9: Deploy Your Services

Now you're ready to deploy your auth-service and client-service. Follow the instructions in `README.md`:

```bash
cd /Users/aadhith/Documents/Projects/Ginthiai/Backendcode/Ginthi_Backend-development/ginthi_agents/k8s

# Set your AWS Account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=ap-south-1

# Run the deployment script
./deploy.sh all
```

## Troubleshooting

### Cluster Creation Fails

```bash
# Check CloudFormation stacks
aws cloudformation describe-stacks --region ap-south-1 | grep ginthi-dataplane-dev

# Check eksctl logs
eksctl utils describe-stacks --region ap-south-1 --cluster ginthi-dataplane-dev
```

### Nodes Not Joining

```bash
# Check node group status
eksctl get nodegroup --cluster ginthi-dataplane-dev --region ap-south-1

# Check node logs (SSH into node or use SSM)
# Verify security groups allow communication between nodes and control plane
```

### AWS Load Balancer Controller Not Working

```bash
# Check controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Verify IAM role
kubectl describe sa aws-load-balancer-controller -n kube-system

# Check IAM policy attachment
aws iam list-attached-role-policies --role-name AmazonEKSLoadBalancerControllerRole
```

### Subnet Tagging Issues

If you get errors about subnet tags:

```bash
# Re-tag subnets
CLUSTER_NAME="ginthi-dataplane-dev"
for subnet in subnet-09769ec6dcf8dc16e subnet-00ab51323c6d99c00 subnet-0d60e0c6f3c58ca6f; do
  aws ec2 create-tags \
    --resources $subnet \
    --tags "Key=kubernetes.io/role/internal-elb,Value=1" \
            "Key=kubernetes.io/role/elb,Value=1" \
            "Key=kubernetes.io/cluster/${CLUSTER_NAME},Value=shared" \
    --region ap-south-1
done
```

## Useful Commands

```bash
# Get cluster info
eksctl get cluster --name ginthi-dataplane-dev --region ap-south-1

# Scale node group
eksctl scale nodegroup --cluster ginthi-dataplane-dev --name ginthi-ng-general --nodes 5 --region ap-south-1

# Update cluster
eksctl update cluster -f eks-cluster-config.yaml

# Delete cluster (use with caution!)
eksctl delete cluster --name ginthi-dataplane-dev --region ap-south-1
```

## Cost Optimization Tips

1. **Use Spot Instances** for non-production workloads:
   ```yaml
   managedNodeGroups:
     - name: ginthi-ng-spot
       instanceTypes: ["t3.medium", "t3a.medium"]
       spot: true
       minSize: 1
       maxSize: 5
   ```

2. **Right-size your nodes** based on actual usage
3. **Enable cluster autoscaler** for automatic scaling
4. **Use Fargate** for serverless workloads

## Next Steps

After the cluster is set up:
1. Deploy your services using the manifests in this directory
2. Configure DNS for your ALB endpoints
3. Set up monitoring and logging (CloudWatch, Prometheus, etc.)
4. Configure backup and disaster recovery
5. Set up CI/CD pipelines

## Additional Resources

- [eksctl Documentation](https://eksctl.io/)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)

