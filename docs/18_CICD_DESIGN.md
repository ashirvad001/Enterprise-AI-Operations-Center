# CI/CD & Deployment Architecture

**Product:** Enterprise AI Operations Center  
**Version:** 1.0  
**Date:** 2026-06-13  
**Classification:** Internal — Confidential  
**Status:** Draft — Awaiting Approval

---

## 1. CI/CD Principles

| Principle | Implementation |
|---|---|
| **GitOps** | Git is the single source of truth for both code and infrastructure. All deployments are triggered by Git commits. |
| **Shift Left Security** | SAST, SCA, and container scanning occur in the CI pipeline before merging. |
| **Immutable Artifacts** | Docker images are built once, signed, and promoted across environments (Dev → Staging → Prod). |
| **Zero-Downtime Deployments** | Rolling updates or Blue/Green deployments for all microservices. |
| **Infrastructure as Code** | Terraform manages cloud resources; ArgoCD manages Kubernetes resources. |

---

## 2. Pipeline Architecture

### 2.1 Branching Strategy (Trunk-Based Development)

- **`main`**: The single source of truth. Always deployable.
- **`feature/*`**: Short-lived branches for new features.
- **`bugfix/*`**: Short-lived branches for bug fixes.
- **`release/*`**: Created from `main` for production deployments.

### 2.2 Continuous Integration (CI) Flow

**Trigger:** Pull Request to `main` (or push to feature branch).
**Tool:** GitHub Actions / GitLab CI.

```mermaid
flowchart LR
    PR[Pull Request] --> LINT[Lint & Format<br/>Ruff/Black]
    PR --> TYPE[Type Check<br/>MyPy]
    
    LINT --> TEST[Unit Tests<br/>Pytest]
    TYPE --> TEST
    
    TEST --> SAST[Security Scan<br/>Bandit/Semgrep]
    TEST --> SCA[Dependency Scan<br/>Snyk/Pip-Audit]
    
    SAST --> BUILD[Build Docker Image]
    SCA --> BUILD
    
    BUILD --> IMG_SCAN[Image Scan<br/>Trivy]
    IMG_SCAN --> SIGN[Sign Image<br/>Cosign]
    
    SIGN --> PUSH[Push to Registry<br/>(Tagged w/ SHA)]
    PUSH --> PR_APPROVE[PR Approved & Merged]
```

### 2.3 Continuous Deployment (CD) Flow (GitOps)

**Trigger:** Merge to `main` (for Staging) or release tag (for Production).
**Tool:** ArgoCD.

```mermaid
flowchart LR
    MERGE[Merge to main] --> UPDATE_MANIFEST[Update K8s Manifests<br/>(Helm/Kustomize)]
    UPDATE_MANIFEST --> PUSH_CONFIG[Push to Config Repo]
    
    PUSH_CONFIG --> ARGOCD[ArgoCD Sync]
    
    subgraph K8s Cluster
        ARGOCD --> ROLLOUT[Deploy New Pods]
        ROLLOUT --> HEALTH[Health Checks]
        HEALTH --> TRAFFIC[Switch Traffic]
    end
    
    HEALTH -- "Fails" --> ROLLBACK[Auto-Rollback]
```

---

## 3. Deployment Environments

| Environment | Purpose | Infrastructure | Deployment Trigger |
|---|---|---|---|
| **Development** | Individual developer testing | Local (Docker Compose / Minikube) | Manual |
| **Staging** | Integration testing, QA, Pre-prod validation | Cloud K8s (scaled down) | Auto on merge to `main` |
| **Production** | Live customer traffic | Cloud K8s (HA, multi-AZ) | Manual approval / Tag release |

---

## 4. CI/CD Pipeline Stages Detail

### 4.1 Build Stage
- **Base Images:** Use minimal, secure base images (e.g., `python:3.11-slim` or `distroless`).
- **Multi-stage Builds:** Separate build dependencies from runtime dependencies.
- **Caching:** Cache pip dependencies and Docker layers to speed up builds.

### 4.2 Test Stage
- **Unit Tests:** Run in isolation. Must have >80% code coverage.
- **Integration Tests:** Spin up required dependencies (e.g., PostgreSQL, Redis) using Testcontainers or Docker Compose in the CI runner.
- **E2E Tests:** Run against the Staging environment.

### 4.3 Security Scans
- **SAST (Static Application Security Testing):** Analyzes source code for vulnerabilities (Bandit for Python, ESLint for JS).
- **SCA (Software Composition Analysis):** Checks dependencies for known CVEs.
- **Container Scanning:** Scans built Docker images for OS and library vulnerabilities (Trivy).

### 4.4 Deployment Strategies

**Microservices (Stateless):**
- **Rolling Update (Default):** Kubernetes default. Starts new pods, waits for readiness probes, then terminates old pods.
- **Canary (Optional):** Route a small percentage of traffic (e.g., 5%) to new pods, monitor metrics, then gradually increase to 100%.

**Database Migrations (Stateful):**
- Migrations must be backward compatible (e.g., add new column, don't drop/rename existing columns immediately).
- Executed via an init-container or a pre-sync job in ArgoCD before application pods start.

---

## 5. Artifact Management

- **Container Registry:** Use a private registry (AWS ECR, GCP Artifact Registry, Azure ACR).
- **Versioning:** Images tagged with Git SHA (e.g., `eaioc-auth:abc123f`) and semantic versions for releases (e.g., `eaioc-auth:v1.2.0`).
- **Retention:** Keep last N images; delete untagged/old images to save costs.

---

*Document Owner: DevOps Engineer*  
*Next Review: Upon stakeholder approval of Phase 6*
