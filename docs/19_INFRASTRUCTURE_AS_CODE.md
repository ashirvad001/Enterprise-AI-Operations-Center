# Infrastructure as Code (IaC) Architecture

**Product:** Enterprise AI Operations Center  
**Version:** 1.0  
**Date:** 2026-06-13  
**Classification:** Internal — Confidential  
**Status:** Draft — Awaiting Approval

---

## 1. IaC Principles

| Principle | Implementation |
|---|---|
| **Declarative Infrastructure** | All infrastructure is defined in Terraform (or OpenTofu). No manual click-ops in the cloud console. |
| **Modular Design** | Reusable Terraform modules for common patterns (e.g., K8s cluster, database, cache). |
| **Environment Parity** | Staging and Production use the same IaC modules, differing only by input variables (e.g., instance sizes, HA config). |
| **State Management** | Remote state backends (e.g., S3 + DynamoDB for locking) with versioning enabled. |
| **Security Scanning** | IaC code is scanned for misconfigurations (e.g., tfsec, Checkov) before deployment. |

---

## 2. Terraform Module Structure

The IaC repository is structured to separate reusable modules from environment-specific configurations.

```
iac/
├── modules/
│   ├── vpc/                 # Network infrastructure
│   ├── kubernetes/          # EKS/GKE cluster
│   ├── database/            # PostgreSQL RDS
│   ├── cache/               # Redis ElastiCache
│   ├── storage/             # S3 buckets for object store
│   └── iam/                 # Roles, policies, service accounts
│
├── environments/
│   ├── staging/
│   │   ├── main.tf          # Instantiates modules for staging
│   │   ├── variables.tf
│   │   └── terraform.tfvars # Staging-specific values
│   │
│   └── production/
│       ├── main.tf          # Instantiates modules for production
│       ├── variables.tf
│       └── terraform.tfvars # Production-specific values
│
└── shared/                  # Resources shared across envs (e.g., ECR, Route53 zones)
```

---

## 3. Core Infrastructure Components (AWS Example)

While the platform is cloud-agnostic, this provides a concrete example using AWS services.

### 3.1 Networking (VPC)
- **VPC:** Custom VPC spanning 3 Availability Zones (AZs).
- **Subnets:**
  - Public Subnets (Load Balancers, NAT Gateways).
  - Private Subnets (EKS Worker Nodes, App Services).
  - Database Subnets (RDS, ElastiCache) - No internet routing.
- **Security Groups:** Strict ingress/egress rules (e.g., RDS only accepts traffic from EKS worker nodes).

### 3.2 Compute (Kubernetes)
- **Service:** Amazon EKS (Elastic Kubernetes Service).
- **Node Groups:**
  - Standard Nodes: For stateless microservices (t3/m5 instances).
  - GPU Nodes: For local/edge model serving or multimodal analysis (g4dn instances) - scaled to 0 when not in use.
- **Auto-scaling:** Cluster Autoscaler or Karpenter.

### 3.3 Data Storage
- **Relational DB:** Amazon RDS for PostgreSQL (Multi-AZ in Prod).
  - Extensions enabled: `pgvector`, `pgcrypto`.
- **Cache & Pub/Sub:** Amazon ElastiCache for Redis (Cluster mode enabled in Prod).
- **Object Storage:** Amazon S3 (with server-side encryption, versioning, and lifecycle policies).

### 3.4 Observability
- **Metrics/Logs:** AWS CloudWatch or managed Prometheus/Grafana.
- **Audit Logs:** Sent to a separate, restricted S3 bucket with Object Lock enabled (WORM compliance).

---

## 4. Kubernetes Manifest Management

Infrastructure deployment is split into two layers:
1. **Cloud Infrastructure (Terraform):** Provisions the EKS cluster, RDS, Redis, S3, etc.
2. **Kubernetes Resources (Helm/Kustomize via ArgoCD):** Deploys the microservices, ingress controllers, observability stack onto the cluster.

### 4.1 Helm Charts
Create a base Helm chart for microservices, allowing individual services to override values.

```yaml
# values.yaml example for Agent Engine
replicaCount: 3
image:
  repository: ecr.aws/eaioc/agent-engine
  tag: "v1.2.0"
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 1000m
    memory: 2Gi
envFrom:
  - secretRef:
      name: agent-engine-secrets
```

---

## 5. Security & Compliance in IaC

- **Least Privilege IAM:** Use IAM Roles for Service Accounts (IRSA) to grant specific pods access to AWS resources (e.g., only the Multimodal service pod gets S3 access).
- **Encryption:** All EBS volumes, RDS instances, and S3 buckets defined in Terraform must have encryption enabled (`encrypted = true`).
- **Secret Management:** Terraform does NOT manage secrets. It provisions Vault or AWS Secrets Manager. Secrets are injected at runtime.

---

*Document Owner: Cloud/DevOps Architect*  
*Next Review: Upon stakeholder approval of Phase 6*
