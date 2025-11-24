#!/bin/bash

# EKS Cluster Setup Script
# This script automates the setup of EKS cluster with proper subnet tagging

set -e

# Configuration
CLUSTER_NAME="ginthi-dataplane-dev"
REGION="ap-south-1"
VPC_ID="vpc-03438362cd9251fe7"
SUBNETS=("subnet-09769ec6dcf8dc16e" "subnet-00ab51323c6d99c00" "subnet-0d60e0c6f3c58ca6f")

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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
    
    command -v eksctl >/dev/null 2>&1 || { 
        log_error "eksctl is not installed. Please install it first."
        log_info "Installation: https://eksctl.io/introduction/installation/"
        exit 1
    }
    
    command -v aws >/dev/null 2>&1 || { 
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    }
    
    command -v kubectl >/dev/null 2>&1 || { 
        log_error "kubectl is not installed. Please install it first."
        exit 1
    }
    
    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS credentials not configured. Please run 'aws configure'"
        exit 1
    fi
    
    log_info "Prerequisites check passed!"
}

# Tag VPC and subnets for EKS
tag_vpc_subnets() {
    log_info "Tagging VPC and subnets for EKS..."
    
    # Tag VPC
    log_info "Tagging VPC: ${VPC_ID}"
    aws ec2 create-tags \
        --resources ${VPC_ID} \
        --tags "Key=kubernetes.io/cluster/${CLUSTER_NAME},Value=shared" \
        --region ${REGION} 2>/dev/null || log_warn "VPC tags may already exist"
    
    # Tag subnets
    for subnet in "${SUBNETS[@]}"; do
        log_info "Tagging subnet: ${subnet}"
        aws ec2 create-tags \
            --resources ${subnet} \
            --tags \
                "Key=kubernetes.io/role/internal-elb,Value=1" \
                "Key=kubernetes.io/role/elb,Value=1" \
                "Key=kubernetes.io/cluster/${CLUSTER_NAME},Value=shared" \
            --region ${REGION} 2>/dev/null || log_warn "Subnet ${subnet} tags may already exist"
    done
    
    log_info "VPC and subnet tagging completed!"
}

# Verify subnet configuration
verify_subnets() {
    log_info "Verifying subnet configuration..."
    
    log_warn "Please verify the availability zones in eks-cluster-config.yaml match your subnets:"
    for subnet in "${SUBNETS[@]}"; do
        AZ=$(aws ec2 describe-subnets \
            --subnet-ids ${subnet} \
            --region ${REGION} \
            --query 'Subnets[0].AvailabilityZone' \
            --output text)
        SUBNET_TYPE=$(aws ec2 describe-subnets \
            --subnet-ids ${subnet} \
            --region ${REGION} \
            --query 'Subnets[0].MapPublicIpOnLaunch' \
            --output text)
        TYPE="private"
        [ "$SUBNET_TYPE" = "True" ] && TYPE="public"
        log_info "Subnet ${subnet} is in ${AZ} (${TYPE})"
    done
    log_warn "If AZs don't match, update eks-cluster-config.yaml before proceeding"
}

# Create EKS cluster
create_cluster() {
    log_info "Creating EKS cluster: ${CLUSTER_NAME}"
    log_warn "This will take 15-20 minutes..."
    
    eksctl create cluster -f eks-cluster-config.yaml
    
    log_info "Cluster created successfully!"
}

# Configure kubectl
configure_kubectl() {
    log_info "Configuring kubectl..."
    
    aws eks update-kubeconfig \
        --region ${REGION} \
        --name ${CLUSTER_NAME}
    
    log_info "kubectl configured!"
    
    # Verify connection
    if kubectl cluster-info >/dev/null 2>&1; then
        log_info "Cluster connection verified!"
        kubectl get nodes
    else
        log_error "Failed to connect to cluster"
        exit 1
    fi
}

# Install AWS Load Balancer Controller
install_alb_controller() {
    log_info "Installing AWS Load Balancer Controller..."
    
    # Get AWS Account ID
    export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Associate OIDC provider
    log_info "Associating OIDC provider..."
    eksctl utils associate-iam-oidc-provider \
        --cluster ${CLUSTER_NAME} \
        --region ${REGION} \
        --approve
    
    # Download IAM policy
    log_info "Downloading IAM policy..."
    curl -s -o /tmp/iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.0/docs/install/iam_policy.json
    
    # Create IAM policy
    log_info "Creating IAM policy..."
    POLICY_ARN=$(aws iam create-policy \
        --policy-name AWSLoadBalancerControllerIAMPolicy-${CLUSTER_NAME} \
        --policy-document file:///tmp/iam_policy.json \
        --query 'Policy.Arn' \
        --output text 2>/dev/null || \
        aws iam get-policy \
            --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy-${CLUSTER_NAME} \
            --query 'Policy.Arn' \
            --output text)
    
    log_info "Policy ARN: ${POLICY_ARN}"
    
    # Create service account
    log_info "Creating service account..."
    eksctl create iamserviceaccount \
        --cluster ${CLUSTER_NAME} \
        --namespace kube-system \
        --name aws-load-balancer-controller \
        --role-name AmazonEKSLoadBalancerControllerRole-${CLUSTER_NAME} \
        --attach-policy-arn ${POLICY_ARN} \
        --region ${REGION} \
        --approve
    
    # Install using Helm
    log_info "Installing AWS Load Balancer Controller using Helm..."
    
    # Check if Helm is installed
    if ! command -v helm &> /dev/null; then
        log_warn "Helm is not installed. Installing Helm..."
        # Install Helm
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    fi
    
    # Add Helm repo
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update
    
    # Install controller
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName=${CLUSTER_NAME} \
        --set serviceAccount.create=false \
        --set serviceAccount.name=aws-load-balancer-controller \
        --set region=${REGION} \
        --wait
    
    log_info "AWS Load Balancer Controller installed!"
    
    # Verify
    kubectl get deployment -n kube-system aws-load-balancer-controller
}

# Install metrics server
install_metrics_server() {
    log_info "Installing Metrics Server..."
    
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    
    log_info "Metrics Server installed!"
}

# Main function
main() {
    case "${1:-all}" in
        tag)
            check_prerequisites
            tag_vpc_subnets
            ;;
        create)
            check_prerequisites
            verify_subnets
            create_cluster
            configure_kubectl
            ;;
        alb)
            check_prerequisites
            configure_kubectl
            install_alb_controller
            ;;
        metrics)
            check_prerequisites
            configure_kubectl
            install_metrics_server
            ;;
        all)
            check_prerequisites
            tag_vpc_subnets
            verify_subnets
            create_cluster
            configure_kubectl
            install_alb_controller
            install_metrics_server
            log_info "EKS cluster setup completed!"
            log_info "Next steps:"
            log_info "1. Review and update ConfigMaps and Secrets in k8s/ directory"
            log_info "2. Build and push Docker images to ECR"
            log_info "3. Deploy services using: ./deploy.sh all"
            ;;
        *)
            echo "Usage: $0 [tag|create|alb|metrics|all]"
            echo ""
            echo "Commands:"
            echo "  tag     - Tag VPC and subnets for EKS"
            echo "  create  - Create EKS cluster"
            echo "  alb     - Install AWS Load Balancer Controller"
            echo "  metrics - Install Metrics Server"
            echo "  all     - Run all steps (default)"
            exit 1
            ;;
    esac
}

main "$@"

