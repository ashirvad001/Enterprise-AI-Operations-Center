# Enterprise AI Operations Center — Deployment Guide

## Overview

EAIOC is designed to be deployed in a hybrid environment:
- **Cloud/Data Center:** Core services (Agent Engine, RAG Service, Vector DB, API Gateway)
- **Edge:** Edge LLMs (Raspberry Pi 5, NVIDIA Jetson) for local voice/multimodal processing

## 1. Local Development (Docker Compose)

The easiest way to run the full stack locally is using Docker Compose.

```bash
cd infrastructure/docker
docker compose up -d
```

**Services Exposed:**
- API Gateway: `http://localhost:8000`
- Agent Engine: `http://localhost:8003`
- RAG Service: `http://localhost:8004`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001`
- Ollama: `http://localhost:11434`

## 2. Production Kubernetes (AWS EKS / GCP GKE)

For production, we use Kubernetes with Horizontal Pod Autoscaling (HPA).

### Prerequisites
- `kubectl` configured for your cluster
- Helm (for ingress/metrics-server)

### Deployment Steps

1. **Deploy Metrics Server (Required for HPA)**
   ```bash
   kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
   ```

2. **Deploy Vector Database (StatefulSet)**
   ```bash
   kubectl apply -f infrastructure/kubernetes/vector-db-statefulset.yaml
   ```

3. **Deploy Microservices**
   ```bash
   kubectl apply -f infrastructure/kubernetes/agents-deployment.yaml
   kubectl apply -f infrastructure/kubernetes/api-deployment.yaml
   ```

4. **Verify HPA**
   ```bash
   kubectl get hpa -n eaioc
   ```

### GPU Node Configuration

For the multimodal service or local LLM inference in the cloud, ensure your node group has GPU taints/tolerations. The AWS Terraform module (`infrastructure/terraform/modules/aws`) configures this automatically using `g4dn.xlarge` instances.

## 3. Edge Deployment (Raspberry Pi 5)

EAIOC supports deploying quantized LLMs (GGUF) to edge devices for low-latency voice and multimodal processing.

### Setup

1. **Install Ollama on Pi 5 (Ubuntu/Debian 64-bit)**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Pull Quantized Model**
   ```bash
   # We recommend Q4_K_M for Pi 5 (4.5GB RAM, ~45 TPS)
   ollama pull llama3:8b
   ```

3. **Deploy Edge Node Agent**
   Copy the `services/edge-manager` directory to the Pi, and run the runtime client to connect back to the central API Gateway.

## 4. CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) automatically:
1. Runs `pytest` unit/integration tests
2. Runs RAGAS evaluation harness (fails if precision < 0.80)
3. Builds Docker images and pushes to GHCR
4. Applies Kubernetes manifests to the production cluster

**Secrets Required in GitHub:**
- `KUBECONFIG` (base64 encoded)
- `DOCKER_PASSWORD` (GHCR or Docker Hub token)
