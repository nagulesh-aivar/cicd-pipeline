#!/bin/bash

# EKS Deployment Script for Auth Service and Client Service
# Usage: ./deploy.sh [build|push|deploy|all]

set -e

# Configuration
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPO_BASE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    command -v docker >/dev/null 2>&1 || { log_error "Docker is required but not installed. Aborting."; exit 1; }
    command -v kubectl >/dev/null 2>&1 || { log_error "kubectl is required but not installed. Aborting."; exit 1; }
    command -v aws >/dev/null 2>&1 || { log_error "AWS CLI is required but not installed. Aborting."; exit 1; }
    
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        log_error "AWS_ACCOUNT_ID environment variable is not set."
        log_info "Please set it: export AWS_ACCOUNT_ID=your-account-id"
        exit 1
    fi
    
    log_info "Prerequisites check passed!"
}

build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    log_info "Building auth-service..."
    docker build -t auth-service:latest -f auth_service/Dockerfile auth_service/
    
    log_info "Building client-service..."
    docker build -t client-service:latest -f client_service/Dockerfile client_service/
    
    log_info "Images built successfully!"
}

push_images() {
    log_info "Pushing images to ECR..."
    
    # Login to ECR
    log_info "Logging in to ECR..."
    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO_BASE}
    
    # Create repositories if they don't exist
    log_info "Creating ECR repositories if needed..."
    aws ecr create-repository --repository-name auth-service --region ${AWS_REGION} 2>/dev/null || log_warn "auth-service repository already exists"
    aws ecr create-repository --repository-name client-service --region ${AWS_REGION} 2>/dev/null || log_warn "client-service repository already exists"
    
    # Tag images
    log_info "Tagging images..."
    docker tag auth-service:latest ${ECR_REPO_BASE}/auth-service:latest
    docker tag client-service:latest ${ECR_REPO_BASE}/client-service:latest
    
    # Push images
    log_info "Pushing auth-service..."
    docker push ${ECR_REPO_BASE}/auth-service:latest
    
    log_info "Pushing client-service..."
    docker push ${ECR_REPO_BASE}/client-service:latest
    
    log_info "Images pushed successfully!"
}

update_manifests() {
    log_info "Updating Kubernetes manifests with ECR repository..."
    
    cd "$PROJECT_ROOT/k8s"
    
    # Update image references in deployment files
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|<YOUR_ECR_REPO>|${ECR_REPO_BASE}|g" auth-service-deployment.yaml
        sed -i '' "s|<YOUR_ECR_REPO>|${ECR_REPO_BASE}|g" client-service-deployment.yaml
    else
        # Linux
        sed -i "s|<YOUR_ECR_REPO>|${ECR_REPO_BASE}|g" auth-service-deployment.yaml
        sed -i "s|<YOUR_ECR_REPO>|${ECR_REPO_BASE}|g" client-service-deployment.yaml
    fi
    
    log_info "Manifests updated!"
}

deploy_k8s() {
    log_info "Deploying to Kubernetes..."
    
    cd "$PROJECT_ROOT/k8s"
    
    # Check if kubectl is configured
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "kubectl is not configured or cannot connect to cluster."
        log_info "Please configure kubectl: aws eks update-kubeconfig --name your-cluster-name --region ${AWS_REGION}"
        exit 1
    fi
    
    # Apply ConfigMaps
    log_info "Applying ConfigMaps..."
    kubectl apply -f auth-service-configmap.yaml
    kubectl apply -f client-service-configmap.yaml
    
    # Apply Secrets
    log_info "Applying Secrets..."
    kubectl apply -f auth-service-secrets.yaml
    kubectl apply -f client-service-secrets.yaml
    
    # Apply Deployments and Services
    log_info "Applying Deployments and Services..."
    kubectl apply -f auth-service-deployment.yaml
    kubectl apply -f client-service-deployment.yaml
    
    # Apply Ingress
    log_info "Applying Ingress..."
    kubectl apply -f ingress.yaml
    
    log_info "Deployment completed!"
    log_info "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=auth-service --timeout=300s || log_warn "Auth service pods not ready yet"
    kubectl wait --for=condition=ready pod -l app=client-service --timeout=300s || log_warn "Client service pods not ready yet"
    
    log_info "Getting deployment status..."
    kubectl get pods -l app=auth-service
    kubectl get pods -l app=client-service
    
    log_info "Getting Ingress details..."
    kubectl get ingress services-ingress
    
    ALB_DNS=$(kubectl get ingress services-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
    if [ -n "$ALB_DNS" ]; then
        log_info "ALB DNS: ${ALB_DNS}"
        log_info "Please configure your DNS records to point to this ALB."
    else
        log_warn "ALB DNS not available yet. It may take a few minutes to provision."
    fi
}

main() {
    case "${1:-all}" in
        build)
            check_prerequisites
            build_images
            ;;
        push)
            check_prerequisites
            push_images
            ;;
        deploy)
            check_prerequisites
            update_manifests
            deploy_k8s
            ;;
        all)
            check_prerequisites
            build_images
            push_images
            update_manifests
            deploy_k8s
            ;;
        *)
            echo "Usage: $0 [build|push|deploy|all]"
            echo ""
            echo "Commands:"
            echo "  build   - Build Docker images locally"
            echo "  push    - Push Docker images to ECR"
            echo "  deploy  - Deploy to Kubernetes (assumes images are already pushed)"
            echo "  all     - Build, push, and deploy (default)"
            exit 1
            ;;
    esac
}

main "$@"

