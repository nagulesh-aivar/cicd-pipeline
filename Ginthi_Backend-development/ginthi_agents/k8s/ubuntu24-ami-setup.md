# Ubuntu 24.04 AMI Setup for EKS

If `Ubuntu2404` is not directly supported by eksctl, you can use a custom Ubuntu 24.04 AMI optimized for EKS.

## Option 1: Check if Ubuntu2404 is Supported

First, try using `Ubuntu2404` in the config file. If eksctl supports it, it will work directly.

```bash
eksctl create cluster -f eks-cluster-config.yaml
```

## Option 2: Use Custom Ubuntu 24.04 AMI

If `Ubuntu2404` is not supported, you need to:

### Step 1: Find or Build Ubuntu 24.04 EKS-Optimized AMI

#### Option A: Use AWS EKS-Optimized Ubuntu AMI (if available)

Check if AWS provides Ubuntu 24.04 AMIs:

```bash
# List available EKS-optimized AMIs
aws ec2 describe-images \
  --owners 602401143452 \
  --filters "Name=name,Values=amazon-eks-node-ubuntu-24.04-*" \
  --region ap-south-1 \
  --query 'Images[*].[ImageId,Name,CreationDate]' \
  --output table
```

#### Option B: Build Custom Ubuntu 24.04 AMI

If AWS doesn't provide Ubuntu 24.04 AMIs, you can build one using Packer:

1. **Install Packer**:
   ```bash
   # macOS
   brew install packer
   
   # Linux
   wget https://releases.hashicorp.com/packer/1.10.0/packer_1.10.0_linux_amd64.zip
   unzip packer_1.10.0_linux_amd64.zip
   sudo mv packer /usr/local/bin/
   ```

2. **Create Packer template** (`ubuntu24-eks-ami.json`):
   ```json
   {
     "builders": [{
       "type": "amazon-ebs",
       "region": "ap-south-1",
       "source_ami_filter": {
         "filters": {
           "virtualization-type": "hvm",
           "name": "ubuntu/images/hvm-ssd/ubuntu-noble-24.04-amd64-server-*",
           "root-device-type": "ebs"
         },
         "owners": ["099720109477"],
         "most_recent": true
       },
       "instance_type": "t3.medium",
       "ssh_username": "ubuntu",
       "ami_name": "eks-ubuntu-24.04-{{timestamp}}",
       "ami_description": "EKS-optimized Ubuntu 24.04 AMI",
       "encrypt_boot": true
     }],
     "provisioners": [{
       "type": "shell",
       "script": "scripts/install-eks-dependencies.sh"
     }]
   }
   ```

3. **Create installation script** (`scripts/install-eks-dependencies.sh`):
   ```bash
   #!/bin/bash
   set -e
   
   # Install required packages
   apt-get update
   apt-get install -y \
     curl \
     wget \
     apt-transport-https \
     ca-certificates \
     gnupg \
     lsb-release
   
   # Install Docker
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
   echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
   apt-get update
   apt-get install -y docker-ce docker-ce-cli containerd.io
   
   # Install kubelet, kubeadm, kubectl
   curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/kubernetes-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | tee /etc/apt/sources.list.d/kubernetes.list
   apt-get update
   apt-get install -y kubelet kubeadm kubectl
   apt-mark hold kubelet kubeadm kubectl
   
   # Install AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   ./aws/install
   
   # Install EKS-specific components
   # Install containerd config for EKS
   mkdir -p /etc/eks
   # Add EKS bootstrap script location
   
   # Cleanup
   apt-get clean
   rm -rf /var/lib/apt/lists/*
   ```

4. **Build the AMI**:
   ```bash
   packer build ubuntu24-eks-ami.json
   ```

   Note the AMI ID from the output.

### Step 2: Update eks-cluster-config.yaml

Replace the `amiFamily` line with the custom AMI:

```yaml
managedNodeGroups:
  - name: ginthi-ng-general
    # ... other config ...
    # Remove: amiFamily: Ubuntu2404
    ami: ami-xxxxxxxxxxxxxxxxx  # Your custom Ubuntu 24.04 AMI ID
    # ... rest of config ...
```

### Step 3: Create Cluster

```bash
eksctl create cluster -f eks-cluster-config.yaml
```

## Option 3: Use Ubuntu 22.04 and Upgrade

If Ubuntu 24.04 support is not available, you can:

1. Use Ubuntu 22.04 initially
2. Create a new node group with Ubuntu 24.04 AMI
3. Migrate workloads
4. Remove old node group

## Verification

After cluster creation, verify Ubuntu version:

```bash
kubectl get nodes -o wide
kubectl get nodes -o jsonpath='{.items[*].status.nodeInfo.osImage}'
```

You should see Ubuntu 24.04 in the output.

## References

- [EKS-Optimized AMIs](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-ami.html)
- [Building Custom AMIs for EKS](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)
- [Ubuntu 24.04 LTS Release Notes](https://wiki.ubuntu.com/NobleNumbat/ReleaseNotes)

