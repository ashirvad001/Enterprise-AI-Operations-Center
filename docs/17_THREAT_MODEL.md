# Threat Model

**Product:** Enterprise AI Operations Center  
**Version:** 1.0  
**Date:** 2026-06-13  
**Classification:** Internal — Confidential  
**Status:** Draft — Awaiting Approval

---

## 1. Threat Modeling Methodology

This document uses the **STRIDE** methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) combined with AI-specific threat vectors from the **OWASP Top 10 for LLM Applications**.

### 1.1 Scope

The scope includes the entire Enterprise AI Operations Center platform, encompassing all 10 microservices, the PostgreSQL database, Redis caches, object storage, external LLM integrations, edge devices, and user interfaces.

---

## 2. Platform Threat Analysis (STRIDE)

### 2.1 Spoofing (Authentication & Identity)

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **S-01: Credential Stuffing** | Attacker uses leaked credentials from other sites to access user accounts. | Rate limiting on login; mandatory email verification; optional/enforced MFA; HaveIBeenPwned password check. | Mitigated |
| **S-02: Session Hijacking** | Attacker steals JWT to impersonate a user. | Short-lived access tokens (15m); HttpOnly, Secure, SameSite=Strict cookies for web clients; IP binding option for sessions. | Mitigated |
| **S-03: API Key Theft** | Attacker finds API key in source code or CI logs. | Keys shown only once; SHA-256 hash stored in DB; key rotation capability; scope-limited keys. | Mitigated |
| **S-04: Edge Device Spoofing** | Attacker connects rogue device to Edge Manager. | Mutual TLS (mTLS) with unique device certificates; certificate fingerprint validation. | Mitigated |
| **S-05: Service Impersonation** | Compromised pod pretends to be another internal service. | Service mesh mTLS with SPIFFE workload identity; strict Kubernetes NetworkPolicies. | Mitigated |

### 2.2 Tampering (Integrity)

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **T-01: Data Modification** | Unauthorized modification of RAG documents or agent configs. | Strict RBAC enforcement; Row-Level Security (RLS) in PostgreSQL; all changes logged to audit. | Mitigated |
| **T-02: Parameter Tampering** | User modifies API request payloads to bypass logic (e.g., changing `tenant_id`). | Pydantic strict validation; `tenant_id` derived securely from JWT, ignoring client payload. | Mitigated |
| **T-03: Model Poisoning** | Attacker tampers with ONNX model files sent to edge devices. | Cryptographic checksums (SHA-256) on all model files; verified by edge device before loading. | Mitigated |
| **T-04: Audit Log Alteration** | Insider or attacker modifies audit logs to cover tracks. | Append-only PostgreSQL table (no UPDATE/DELETE grants); cryptographic hash chain linking events. | Mitigated |

### 2.3 Repudiation (Non-repudiation & Audit)

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **R-01: Action Denial** | User denies triggering a costly agent execution or deleting data. | Comprehensive, immutable audit logging with user ID, IP address, request ID, and timestamp. | Mitigated |
| **R-02: System Event Denial** | System cannot prove what happened during an incident. | Centralized logging (Loki/Fluentd) with 1-year retention; OpenTelemetry distributed tracing. | Mitigated |

### 2.4 Information Disclosure (Confidentiality)

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **I-01: Cross-Tenant Data Leak** | Bug allows Tenant A to read Tenant B's data. | PostgreSQL RLS on all tenant-scoped tables; tenant prefix in object storage and Redis. | Mitigated |
| **I-02: PII Leakage in Logs** | Sensitive user input or LLM output logged to observability tools. | PII detection engine (Presidio) masks standard PII formats before log ingestion. | Mitigated |
| **I-03: Secret Exposure** | API keys or DB passwords exposed in environment variables or code. | HashiCorp Vault / Cloud Secrets Manager; injected at runtime via sidecar/tmpfs. | Mitigated |
| **I-04: RAG Context Leak** | User searches KB and retrieves documents they shouldn't see. | Document-level ACLs evaluated *before* vector search (filtering `document_id IN accessible_ids`). | Mitigated |
| **I-05: DB Snapshot Theft** | Attacker steals database backup files from object storage. | AES-256-GCM encryption on all backups; restricted IAM access to backup buckets. | Mitigated |

### 2.5 Denial of Service (Availability)

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **D-01: Volumetric DDoS** | High-volume traffic overwhelms API Gateway. | Cloud WAF / DDoS protection (e.g., Cloudflare/AWS Shield) upstream of gateway. | Mitigated |
| **D-02: Expensive Query Exhaustion** | User triggers complex vector searches or agent loops to consume resources. | API rate limiting; max depth for DAG execution; query timeout limits in PostgreSQL (statement_timeout). | Mitigated |
| **D-03: LLM Cost Exhaustion (Wallet Exhaustion)** | Attacker triggers endless LLM calls to run up provider bills. | Configurable cost budgets per agent and per execution; hard limits in Agent Engine. | Mitigated |
| **D-04: Storage Exhaustion** | Malicious tenant uploads massive files to exhaust storage. | File size limits (100MB default); tenant storage quotas; S3 auto-scaling. | Mitigated |

### 2.6 Elevation of Privilege (Authorization)

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **E-01: Vertical Escalation** | Regular user exploits flaw to gain Admin rights. | Strict RBAC engine; explicit checks on role modification endpoints; default-deny policy. | Mitigated |
| **E-02: Horizontal Escalation** | User accesses another user's private resources. | Resource-level ACLs evaluated for every object access. | Mitigated |
| **E-03: Container Escape** | Compromised application process breaks out to Kubernetes node. | Minimal base images; run as non-root; drop all capabilities; read-only root filesystem. | Mitigated |

---

## 3. AI-Specific Threat Analysis (OWASP Top 10 for LLMs)

### 3.1 LLM01: Prompt Injection

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **Direct Injection** | User crafts input to override system instructions (e.g., "Ignore previous instructions"). | System prompt isolation; input classifiers; output validation against guardrails. | Partially Mitigated (Inherent LLM risk) |
| **Indirect Injection** | Malicious instructions embedded in uploaded RAG documents or websites. | Document scanning; treating RAG context as untrusted data; clear delimiter separation in prompts. | Partially Mitigated |

### 3.2 LLM02: Insecure Output Handling

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **XSS via LLM Output** | LLM generates malicious JavaScript rendered by frontend. | React/Next.js automatic escaping; strict Content Security Policy (CSP); sanitizing markdown. | Mitigated |
| **Command Execution** | LLM output passed directly to system shell or eval(). | Code execution tools run in isolated, ephemeral sandboxes (gVisor/Firecracker); no direct eval(). | Mitigated |

### 3.3 LLM03: Training Data Poisoning

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **RAG Poisoning** | User uploads false information to KB to manipulate agent answers. | RBAC on KB uploads; source citations required on all RAG answers; audit trail of document uploaders. | Mitigated |

### 3.4 LLM04: Model Denial of Service

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **Context Window Exhaustion** | Input crafted to exceed token limits, causing crashes. | Hard limits on input length; token counting (tiktoken) before LLM calls; truncation strategies. | Mitigated |

### 3.5 LLM05: Supply Chain Vulnerabilities

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **Compromised Base Model** | Open-source model (e.g., Ollama) contains backdoor. | Use established providers (OpenAI, Anthropic) or verify SHA hashes of downloaded weights. | Mitigated |
| **Malicious PyPI Package** | Dependency hijacking in Python microservices. | Snyk/pip-audit scanning; pinned hashes in requirements.txt; private PyPI mirror for enterprise. | Mitigated |

### 3.6 LLM06: Sensitive Information Disclosure

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **Model Leakage** | LLM outputs confidential data from its context window. | Strict RBAC on RAG retrieval (don't put unauthorized data in context); PII output filtering guardrails. | Mitigated |

### 3.7 LLM07: Insecure Plugin Design

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **Tool Abuse** | Agent tricked into using a tool maliciously (e.g., deleting DB). | Principle of least privilege for tools; Human-in-the-Loop (HITL) approval required for destructive actions. | Mitigated |

### 3.8 LLM08: Excessive Agency

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **Runaway Agent** | Autonomous loop spirals out of control. | DAG node execution limits; max iterations constraint; cost budget circuit breakers; manual kill switch. | Mitigated |

### 3.9 LLM09: Overreliance

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **Hallucination Acceptance** | User blindly trusts incorrect LLM output for critical decision. | Mandatory citations for RAG; UI warnings about AI fallibility; RAGAS evaluation pipeline for KB quality. | Mitigated |

### 3.10 LLM10: Model Theft

| Threat | Description | Mitigation | Status |
|---|---|---|---|
| **Edge Model Extraction** | Attacker physically extracts ONNX model from edge device. | Disk encryption on edge devices; models encrypted at rest; mTLS required to download models. | Mitigated |

---

## 4. Trust Boundaries & Data Flow Analysis

### 4.1 Key Trust Boundaries

1. **Internet ↔ API Gateway:** Untrusted external traffic. Protected by TLS, WAF, Rate Limiting, and JWT/API Key validation.
2. **Tenant A ↔ Tenant B:** Logical boundary. Protected by PostgreSQL Row-Level Security (RLS) and application-level tenant context enforcement.
3. **Application ↔ LLM Provider:** Semi-trusted external boundary. Protected by TLS, API keys, and Prompt Injection defenses (treating LLM output as untrusted).
4. **Application ↔ Edge Device:** Untrusted physical boundary. Protected by mTLS, certificate validation, and zero-trust payload verification.
5. **Services ↔ Database/Cache:** Internal trusted boundary. Protected by service mesh mTLS and network policies.

### 4.2 High-Risk Data Flows

| Flow | Data | Risk | Mitigation |
|---|---|---|---|
| User Upload → RAG | Documents | Malware, Indirect Prompt Injection | ClamAV scanning, strict parsing, RBAC indexing |
| RAG Retrieval → LLM | Enterprise Data | Data exfiltration via LLM | Provider data processing agreements (zero retention), TLS |
| LLM Response → Frontend | Generated Text | XSS, Hallucinations | Markdown sanitization, CSP, Citations |
| Edge Device → MLOps | Telemetry | Device spoofing | mTLS client certificates |

---

## 5. Security Controls Summary Matrix

| Control Category | Implemented Defenses |
|---|---|
| **Identity & Access** | JWT (RS256), API Keys, MFA (TOTP), RBAC, Resource ACLs, SSO (SAML/OIDC) |
| **Data Protection** | AES-256 (At Rest), TLS 1.3 (In Transit), PII Masking, PostgreSQL RLS |
| **Network & Infra** | WAF, K8s NetworkPolicies, Service Mesh (mTLS), Non-root Containers |
| **Application Sec** | Pydantic validation, RFC 7807 Errors, Rate Limiting, CSP, SameSite Cookies |
| **AI Specific** | Cost Budgets, Guardrails, HITL Approvals, Prompt Isolation, RAGAS Eval |
| **Observability** | Immutable Audit Hash Chain, Prometheus/Grafana, Distributed Tracing |

---

*Document Owner: Security Architect*  
*Next Review: Upon stakeholder approval of Phase 5*
