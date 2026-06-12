# API Specification

**Product:** Enterprise AI Operations Center  
**Version:** 1.0  
**Date:** 2026-06-13  
**Classification:** Internal — Confidential  
**Status:** Draft — Awaiting Approval

---

## 1. API Design Principles

| Principle | Implementation |
|---|---|
| **RESTful** | Resource-oriented URLs, proper HTTP verbs, stateless requests |
| **Versioned** | URL path versioning: `/api/v1/...` |
| **Consistent** | Standardized request/response shapes across all endpoints |
| **Documented** | OpenAPI 3.1 spec auto-generated from code annotations |
| **Secure** | JWT Bearer auth on all endpoints; API key support; RBAC enforcement |
| **Paginated** | Cursor-based pagination on all list endpoints |
| **Idempotent** | PUT/DELETE are idempotent; POST uses idempotency keys where applicable |
| **Rate-Limited** | Per-key and per-IP rate limits; 429 responses with Retry-After header |

### 1.1 Base URL

```
Production:  https://api.eaioc.example.com/api/v1
Staging:     https://api-staging.eaioc.example.com/api/v1
Local:       http://localhost:8000/api/v1
```

### 1.2 Authentication

All authenticated endpoints require one of:

```
# JWT Bearer Token (from login/SSO)
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

# API Key (from API key management)
X-API-Key: eaioc_sk_a1b2c3d4e5f6...
```

### 1.3 Standard Response Envelope

**Success Response:**
```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-06-13T00:00:00Z"
  }
}
```

**List Response (Paginated):**
```json
{
  "data": [ ... ],
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-06-13T00:00:00Z"
  },
  "pagination": {
    "cursor": "eyJpZCI6IjEyMyJ9",
    "has_more": true,
    "total_count": 150,
    "page_size": 20
  }
}
```

**Error Response (RFC 7807):**
```json
{
  "type": "https://eaioc.dev/errors/auth/invalid-credentials",
  "title": "Invalid Credentials",
  "status": 401,
  "detail": "The email or password provided is incorrect.",
  "instance": "/api/v1/auth/login",
  "request_id": "req_abc123",
  "timestamp": "2026-06-13T00:00:00Z"
}
```

### 1.4 Common Headers

| Header | Direction | Required | Description |
|---|---|---|---|
| `Authorization` | Request | Yes* | `Bearer <jwt>` — required for authenticated endpoints |
| `X-API-Key` | Request | Alt* | API key — alternative to Bearer token |
| `X-Request-ID` | Request | No | Client-provided correlation ID; generated server-side if absent |
| `X-Tenant-ID` | Request | No | Explicit tenant context (super-admin only) |
| `Content-Type` | Request | Yes (POST/PUT) | `application/json` unless file upload |
| `Accept` | Request | No | `application/json` (default) |
| `X-Request-ID` | Response | Always | Server-generated or echo of client request ID |
| `X-RateLimit-Limit` | Response | Always | Rate limit ceiling for this endpoint |
| `X-RateLimit-Remaining` | Response | Always | Remaining requests in current window |
| `X-RateLimit-Reset` | Response | Always | Unix timestamp when limit resets |
| `Retry-After` | Response | On 429 | Seconds to wait before retrying |

---

## 2. Authentication APIs

### 2.1 Endpoint Summary

| Method | Endpoint | Auth | Rate Limit | Description |
|---|---|---|---|---|
| POST | `/auth/register` | No | 5/min | Register new user and organization |
| POST | `/auth/login` | No | 20/min | Login with email and password |
| POST | `/auth/refresh` | No* | 30/min | Refresh access token |
| POST | `/auth/logout` | Yes | 30/min | Revoke current session |
| POST | `/auth/logout-all` | Yes | 5/min | Revoke all sessions for current user |
| POST | `/auth/verify-email` | No | 10/min | Verify email with token |
| POST | `/auth/forgot-password` | No | 5/min | Request password reset email |
| POST | `/auth/reset-password` | No | 5/min | Reset password with token |
| POST | `/auth/mfa/enable` | Yes | 5/min | Enable TOTP MFA |
| POST | `/auth/mfa/verify` | Partial | 10/min | Verify TOTP code during login |
| POST | `/auth/mfa/disable` | Yes | 5/min | Disable MFA (requires current TOTP) |
| GET | `/auth/sso/initiate` | No | 10/min | Initiate SSO login flow |
| POST | `/auth/sso/callback` | No | 20/min | Handle SSO callback |

### 2.2 Endpoint Details

#### POST `/auth/register`

Register a new user and create their organization.

**Request:**
```json
{
  "email": "priya@acme.com",
  "password": "SecureP@ssw0rd!2026",
  "full_name": "Priya Sharma",
  "organization_name": "Acme Corp"
}
```

**Response (201):**
```json
{
  "data": {
    "user_id": "usr_01HYQR...",
    "email": "priya@acme.com",
    "tenant_id": "tnt_01HYQS...",
    "organization_name": "Acme Corp",
    "is_verified": false,
    "message": "Verification email sent. Please check your inbox."
  }
}
```

**Errors:** `409` email exists | `422` validation error | `429` rate limited

---

#### POST `/auth/login`

Authenticate with email and password.

**Request:**
```json
{
  "email": "priya@acme.com",
  "password": "SecureP@ssw0rd!2026"
}
```

**Response (200) — No MFA:**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "rt_01HYQR...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": "usr_01HYQR...",
      "email": "priya@acme.com",
      "full_name": "Priya Sharma",
      "tenant_id": "tnt_01HYQS...",
      "roles": ["developer"]
    }
  }
}
```

**Response (200) — MFA Required:**
```json
{
  "data": {
    "mfa_required": true,
    "mfa_token": "mfa_01HYQR...",
    "message": "Enter your TOTP code to complete login."
  }
}
```

**Errors:** `401` invalid credentials | `403` account locked/unverified | `429` rate limited

---

## 3. User Management APIs

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/users/me` | Yes | Any | Get current user profile |
| PUT | `/users/me` | Yes | Any | Update current user profile |
| PUT | `/users/me/password` | Yes | Any | Change password |
| GET | `/users/me/sessions` | Yes | Any | List active sessions |
| DELETE | `/users/me/sessions/{id}` | Yes | Any | Revoke specific session |
| GET | `/users` | Yes | users:read | List users in tenant |
| GET | `/users/{id}` | Yes | users:read | Get user details |
| PUT | `/users/{id}` | Yes | users:manage | Update user (admin) |
| DELETE | `/users/{id}` | Yes | users:manage | Deactivate user (soft delete) |
| GET | `/users/me/api-keys` | Yes | Any | List user's API keys |
| POST | `/users/me/api-keys` | Yes | Any | Create new API key |
| DELETE | `/users/me/api-keys/{id}` | Yes | Any | Revoke API key |

#### POST `/users/me/api-keys`

**Request:**
```json
{
  "name": "CI/CD Pipeline",
  "scopes": ["agents:read", "agents:execute", "rag:search"],
  "expires_in_days": 90
}
```

**Response (201):**
```json
{
  "data": {
    "id": "key_01HYQR...",
    "key": "eaioc_sk_a1b2c3d4e5f6g7h8i9j0...",
    "prefix": "eaioc_sk_a1",
    "name": "CI/CD Pipeline",
    "scopes": ["agents:read", "agents:execute", "rag:search"],
    "expires_at": "2026-09-11T00:00:00Z",
    "warning": "Save this key — it will not be shown again."
  }
}
```

---

## 4. RBAC APIs

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/rbac/roles` | Yes | rbac:manage | List roles in tenant |
| POST | `/rbac/roles` | Yes | rbac:manage | Create custom role |
| GET | `/rbac/roles/{id}` | Yes | rbac:manage | Get role with permissions |
| PUT | `/rbac/roles/{id}` | Yes | rbac:manage | Update role |
| DELETE | `/rbac/roles/{id}` | Yes | rbac:manage | Delete custom role |
| GET | `/rbac/permissions` | Yes | rbac:manage | List all available permissions |
| POST | `/rbac/roles/{id}/permissions` | Yes | rbac:manage | Assign permissions to role |
| DELETE | `/rbac/roles/{id}/permissions/{pid}` | Yes | rbac:manage | Remove permission from role |
| GET | `/rbac/teams` | Yes | users:read | List teams |
| POST | `/rbac/teams` | Yes | users:manage | Create team |
| PUT | `/rbac/teams/{id}` | Yes | users:manage | Update team |
| DELETE | `/rbac/teams/{id}` | Yes | users:manage | Delete team |
| POST | `/rbac/teams/{id}/members` | Yes | users:team_manage | Add member to team |
| DELETE | `/rbac/teams/{id}/members/{uid}` | Yes | users:team_manage | Remove member from team |
| POST | `/rbac/users/{id}/roles` | Yes | rbac:manage | Assign role to user |
| DELETE | `/rbac/users/{id}/roles/{rid}` | Yes | rbac:manage | Remove role from user |
| POST | `/rbac/acl` | Yes | rbac:manage | Create resource ACL |
| DELETE | `/rbac/acl/{id}` | Yes | rbac:manage | Remove resource ACL |
| GET | `/rbac/acl` | Yes | rbac:manage | List ACLs (filterable) |

#### POST `/rbac/roles`

**Request:**
```json
{
  "name": "ML Engineer",
  "description": "Can manage agents and RAG, but not RBAC or billing",
  "permissions": [
    {"resource": "agents", "action": "create"},
    {"resource": "agents", "action": "read"},
    {"resource": "agents", "action": "update"},
    {"resource": "agents", "action": "execute"},
    {"resource": "rag", "action": "create"},
    {"resource": "rag", "action": "read"},
    {"resource": "rag", "action": "search"}
  ]
}
```

**Response (201):**
```json
{
  "data": {
    "id": "role_01HYQR...",
    "name": "ML Engineer",
    "description": "Can manage agents and RAG, but not RBAC or billing",
    "is_system_role": false,
    "permissions": [ ... ],
    "created_at": "2026-06-13T00:00:00Z"
  }
}
```

---

## 5. Agent APIs

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/agents` | Yes | agents:read | List agents (paginated, filterable) |
| POST | `/agents` | Yes | agents:create | Create new agent |
| GET | `/agents/{id}` | Yes | agents:read | Get agent details |
| PUT | `/agents/{id}` | Yes | agents:update | Update agent configuration |
| DELETE | `/agents/{id}` | Yes | agents:delete | Delete agent (soft) |
| POST | `/agents/{id}/execute` | Yes | agents:execute | Execute single agent |
| GET | `/agents/templates` | Yes | agents:read | List agent templates |
| GET | `/workflows` | Yes | agents:read | List workflows |
| POST | `/workflows` | Yes | agents:create | Create workflow |
| GET | `/workflows/{id}` | Yes | agents:read | Get workflow details |
| PUT | `/workflows/{id}` | Yes | agents:update | Update workflow DAG |
| DELETE | `/workflows/{id}` | Yes | agents:delete | Delete workflow |
| POST | `/workflows/{id}/validate` | Yes | agents:read | Validate DAG without executing |
| POST | `/workflows/{id}/execute` | Yes | agents:execute | Execute workflow |
| GET | `/workflows/executions` | Yes | agents:read | List executions (paginated) |
| GET | `/workflows/executions/{id}` | Yes | agents:read | Get execution details with steps |
| POST | `/workflows/executions/{id}/cancel` | Yes | agents:execute | Cancel running execution |
| POST | `/workflows/executions/{id}/approve` | Yes | agents:execute | Approve/reject HITL step |
| GET | `/workflows/executions/{id}/trace` | Yes | agents:read | Get full execution trace |

#### POST `/agents`

**Request:**
```json
{
  "name": "Research Assistant",
  "description": "Searches knowledge bases and summarizes findings",
  "type": "research",
  "model_config": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.3,
    "max_tokens": 4096
  },
  "system_prompt": "You are a research assistant. Search the knowledge base and provide comprehensive summaries with citations.",
  "tools": [
    {"name": "rag_search", "config": {"knowledge_base_id": "kb_01HYQR..."}},
    {"name": "web_search", "config": {"max_results": 5}}
  ],
  "guardrails": {
    "block_pii": true,
    "require_citations": true,
    "max_output_tokens": 2048
  },
  "cost_budget": {
    "max_cost_per_execution": 0.50,
    "max_tokens_per_execution": 50000
  }
}
```

**Response (201):**
```json
{
  "data": {
    "id": "agt_01HYQR...",
    "name": "Research Assistant",
    "version": "1.0.0",
    "type": "research",
    "status": "active",
    "model_config": { ... },
    "tools": [ ... ],
    "guardrails": { ... },
    "created_at": "2026-06-13T00:00:00Z",
    "created_by": "usr_01HYQR..."
  }
}
```

#### POST `/workflows/{id}/execute`

**Request:**
```json
{
  "input_data": {
    "user_query": "What are the latest compliance requirements for our industry?",
    "output_format": "executive_summary"
  },
  "options": {
    "async": true,
    "webhook_url": "https://acme.com/webhooks/agent-complete"
  }
}
```

**Response (202):**
```json
{
  "data": {
    "execution_id": "exec_01HYQR...",
    "workflow_id": "wf_01HYQR...",
    "status": "running",
    "websocket_url": "/ws/v1/agents/executions/exec_01HYQR...",
    "estimated_duration_seconds": 15,
    "created_at": "2026-06-13T00:00:00Z"
  }
}
```

#### POST `/workflows/executions/{id}/approve`

**Request:**
```json
{
  "step_id": "step_research_review",
  "decision": "approve",
  "comment": "Findings look accurate. Proceed with report generation."
}
```

**Response (200):**
```json
{
  "data": {
    "execution_id": "exec_01HYQR...",
    "step_id": "step_research_review",
    "decision": "approve",
    "status": "running",
    "message": "Execution resumed from approved step."
  }
}
```

---

## 6. RAG APIs

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/rag/knowledge-bases` | Yes | rag:read | List knowledge bases |
| POST | `/rag/knowledge-bases` | Yes | rag:create | Create knowledge base |
| GET | `/rag/knowledge-bases/{id}` | Yes | rag:read | Get KB details with stats |
| PUT | `/rag/knowledge-bases/{id}` | Yes | rag:update | Update KB configuration |
| DELETE | `/rag/knowledge-bases/{id}` | Yes | rag:delete | Delete KB and all documents |
| GET | `/rag/knowledge-bases/{id}/documents` | Yes | rag:read | List documents in KB |
| POST | `/rag/knowledge-bases/{id}/documents` | Yes | rag:create | Upload document to KB |
| GET | `/rag/documents/{id}` | Yes | rag:read | Get document details |
| DELETE | `/rag/documents/{id}` | Yes | rag:delete | Delete document |
| GET | `/rag/documents/{id}/chunks` | Yes | rag:read | List chunks for document |
| POST | `/rag/search` | Yes | rag:search | Search across knowledge bases |
| POST | `/rag/knowledge-bases/{id}/evaluate` | Yes | rag:read | Trigger RAGAS evaluation |
| GET | `/rag/knowledge-bases/{id}/evaluations` | Yes | rag:read | List evaluation results |

#### POST `/rag/knowledge-bases/{id}/documents`

**Request (multipart/form-data):**
```
Content-Type: multipart/form-data; boundary=----

------
Content-Disposition: form-data; name="file"; filename="compliance-policy-2026.pdf"
Content-Type: application/pdf

<binary PDF data>
------
Content-Disposition: form-data; name="metadata"
Content-Type: application/json

{"department": "legal", "author": "Jane Smith", "tags": ["compliance", "2026", "policy"]}
------
```

**Response (202):**
```json
{
  "data": {
    "document_id": "doc_01HYQR...",
    "filename": "compliance-policy-2026.pdf",
    "content_type": "application/pdf",
    "file_size_bytes": 2456789,
    "status": "processing",
    "message": "Document accepted. Processing will complete in ~30 seconds.",
    "status_url": "/api/v1/rag/documents/doc_01HYQR..."
  }
}
```

#### POST `/rag/search`

**Request:**
```json
{
  "query": "What are the data retention requirements for EU customers?",
  "knowledge_base_ids": ["kb_01HYQR..."],
  "top_k": 5,
  "search_type": "hybrid",
  "filters": {
    "metadata": {"department": "legal"},
    "date_range": {"from": "2025-01-01", "to": "2026-12-31"}
  },
  "options": {
    "include_chunks": true,
    "min_relevance_score": 0.7
  }
}
```

**Response (200):**
```json
{
  "data": {
    "results": [
      {
        "chunk_id": "chk_01HYQR...",
        "document_id": "doc_01HYQR...",
        "content": "EU data retention requirements mandate that personal data...",
        "relevance_score": 0.92,
        "search_scores": {
          "vector_score": 0.89,
          "bm25_score": 0.85,
          "rrf_score": 0.92
        },
        "citation": {
          "document_name": "GDPR-Compliance-Guide-2026.pdf",
          "page_number": 14,
          "section": "Section 3.2 - Data Retention"
        },
        "metadata": {
          "department": "legal",
          "author": "Jane Smith"
        }
      }
    ],
    "query_metadata": {
      "total_results": 5,
      "search_type": "hybrid",
      "embedding_model": "text-embedding-3-small",
      "latency_ms": 125
    }
  }
}
```

---

## 7. Multimodal APIs

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| POST | `/multimodal/analyze/image` | Yes | multimodal:use | Analyze an image using vision LLM |
| POST | `/multimodal/analyze/document` | Yes | multimodal:use | OCR + analyze a document image |
| POST | `/multimodal/analyze/video` | Yes | multimodal:use | Extract frames and analyze video |
| POST | `/multimodal/transcribe` | Yes | multimodal:use | Transcribe audio file |
| GET | `/multimodal/assets` | Yes | multimodal:use | List media assets |
| GET | `/multimodal/assets/{id}` | Yes | multimodal:use | Get asset with analysis results |
| DELETE | `/multimodal/assets/{id}` | Yes | multimodal:manage | Delete media asset |
| GET | `/multimodal/assets/{id}/results` | Yes | multimodal:use | List analysis results for asset |

#### POST `/multimodal/analyze/image`

**Request (multipart/form-data):**
```
file: <image binary>
prompt: "Describe the contents of this image in detail. Identify any text, logos, or notable objects."
model: "gpt-4o"
```

**Response (200):**
```json
{
  "data": {
    "asset_id": "media_01HYQR...",
    "analysis_type": "vision",
    "model": "gpt-4o",
    "result": {
      "description": "The image shows a corporate office building with...",
      "detected_objects": ["building", "signage", "entrance"],
      "detected_text": ["ACME Corporation", "Main Entrance"],
      "confidence": 0.94
    },
    "cost": {
      "tokens_in": 1200,
      "tokens_out": 350,
      "cost_usd": 0.012
    },
    "duration_ms": 2340
  }
}
```

---

## 8. Voice APIs

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| POST | `/voice/sessions` | Yes | voice:use | Create voice session (returns WebSocket URL) |
| GET | `/voice/sessions` | Yes | voice:use | List voice sessions |
| GET | `/voice/sessions/{id}` | Yes | voice:use | Get session details with transcript |
| DELETE | `/voice/sessions/{id}` | Yes | voice:use | End voice session |
| GET | `/voice/providers` | Yes | voice:use | List available STT/TTS providers |
| PUT | `/voice/settings` | Yes | voice:manage | Update voice settings |

#### POST `/voice/sessions`

**Request:**
```json
{
  "agent_id": "agt_01HYQR...",
  "stt_provider": "whisper",
  "tts_provider": "coqui",
  "language": "en",
  "options": {
    "noise_cancellation": true,
    "vad_enabled": true,
    "record_audio": false
  }
}
```

**Response (201):**
```json
{
  "data": {
    "session_id": "vs_01HYQR...",
    "websocket_url": "/ws/v1/voice/sessions/vs_01HYQR...",
    "status": "active",
    "stt_provider": "whisper",
    "tts_provider": "coqui",
    "language": "en",
    "created_at": "2026-06-13T00:00:00Z"
  }
}
```

### 8.1 WebSocket Protocol — Voice

**Connection:** `wss://api.eaioc.example.com/ws/v1/voice/sessions/{session_id}?token=<jwt>`

**Client → Server Messages:**
```json
{"type": "audio", "data": "<base64_pcm_16khz_mono>", "sequence": 1}
{"type": "config", "vad_threshold": 0.5, "silence_duration_ms": 1000}
{"type": "end_session"}
```

**Server → Client Messages:**
```json
{"type": "transcript", "text": "...", "is_final": true, "confidence": 0.95}
{"type": "agent_response", "text": "...", "audio": "<base64_pcm>", "is_final": false}
{"type": "agent_response", "text": "...", "audio": "<base64_pcm>", "is_final": true}
{"type": "error", "code": "stt_error", "message": "..."}
{"type": "session_ended", "summary": {"utterances": 12, "duration_seconds": 180}}
```

---

## 9. Edge APIs

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/edge/devices` | Yes | edge:read | List registered edge devices |
| POST | `/edge/devices` | Yes | edge:manage | Register new edge device |
| GET | `/edge/devices/{id}` | Yes | edge:read | Get device details with status |
| PUT | `/edge/devices/{id}` | Yes | edge:manage | Update device configuration |
| DELETE | `/edge/devices/{id}` | Yes | edge:manage | Decommission device |
| GET | `/edge/devices/{id}/models` | Yes | edge:read | List models deployed on device |
| POST | `/edge/devices/{id}/models` | Yes | edge:manage | Deploy model to device |
| DELETE | `/edge/devices/{id}/models/{mid}` | Yes | edge:manage | Remove model from device |
| POST | `/edge/devices/{id}/models/{mid}/rollback` | Yes | edge:manage | Rollback model to previous version |
| GET | `/edge/devices/{id}/telemetry` | Yes | edge:read | Get device telemetry (time range) |
| POST | `/edge/devices/{id}/command` | Yes | edge:manage | Send remote command |

#### POST `/edge/devices`

**Request:**
```json
{
  "device_name": "factory-floor-cam-01",
  "device_type": "jetson_orin",
  "hardware_info": {
    "cpu": "ARM Cortex-A78AE",
    "ram_gb": 32,
    "gpu": "NVIDIA Ampere (2048 CUDA cores)",
    "storage_gb": 64
  },
  "certificate": "<PEM encoded device certificate>"
}
```

**Response (201):**
```json
{
  "data": {
    "device_id": "dev_01HYQR...",
    "device_name": "factory-floor-cam-01",
    "device_type": "jetson_orin",
    "status": "registered",
    "grpc_endpoint": "grpc://edge.eaioc.example.com:50051",
    "mqtt_topic": "telemetry/dev_01HYQR...",
    "api_token": "edge_tk_...",
    "created_at": "2026-06-13T00:00:00Z"
  }
}
```

---

## 10. MLOps & Observability APIs

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/mlops/cost/summary` | Yes | billing:read | Cost summary (daily/weekly/monthly) |
| GET | `/mlops/cost/breakdown` | Yes | billing:read | Cost breakdown by agent/user/team/model |
| GET | `/mlops/cost/timeseries` | Yes | billing:read | Cost over time (for charts) |
| GET | `/mlops/metrics` | Yes | agents:read | Platform metrics summary |
| GET | `/mlops/drift` | Yes | agents:read | Model drift alerts |
| GET | `/mlops/evaluations` | Yes | rag:read | RAG evaluation results |
| POST | `/mlops/evaluations` | Yes | rag:read | Trigger on-demand evaluation |
| GET | `/mlops/experiments` | Yes | agents:read | List MLflow experiments |
| GET | `/mlops/experiments/{id}` | Yes | agents:read | Get experiment details |

#### GET `/mlops/cost/summary`

**Query Parameters:** `period=monthly&from=2026-01-01&to=2026-06-30`

**Response (200):**
```json
{
  "data": {
    "period": "monthly",
    "total_cost_usd": 4523.87,
    "total_tokens": 125000000,
    "breakdown_by_provider": {
      "openai": {"cost_usd": 3200.00, "tokens": 80000000, "requests": 45000},
      "anthropic": {"cost_usd": 1100.00, "tokens": 35000000, "requests": 12000},
      "ollama": {"cost_usd": 0, "tokens": 10000000, "requests": 8000}
    },
    "breakdown_by_type": {
      "agent": {"cost_usd": 2800.00, "percentage": 61.9},
      "rag": {"cost_usd": 1200.00, "percentage": 26.5},
      "multimodal": {"cost_usd": 400.00, "percentage": 8.8},
      "voice": {"cost_usd": 123.87, "percentage": 2.7}
    },
    "trend": "up_12_percent"
  }
}
```

---

## 11. Audit APIs

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/audit/events` | Yes | audit:read | Search audit events (paginated) |
| GET | `/audit/events/{id}` | Yes | audit:read | Get specific audit event |
| POST | `/audit/events/export` | Yes | audit:read | Export audit events (CSV/JSON) |
| GET | `/audit/integrity` | Yes | audit:read | Verify hash chain integrity |
| GET | `/audit/summary` | Yes | audit:read | Audit summary statistics |

#### GET `/audit/events`

**Query Parameters:**
```
?action=user.login
&outcome=failure
&from=2026-06-01T00:00:00Z
&to=2026-06-13T23:59:59Z
&user_id=usr_01HYQR...
&cursor=eyJ...
&page_size=50
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "evt_01HYQR...",
      "sequence_num": 10423,
      "action": "user.login",
      "outcome": "failure",
      "user_id": "usr_01HYQR...",
      "resource_type": "session",
      "details": {
        "reason": "invalid_password",
        "attempt_number": 3
      },
      "ip_address": "203.0.113.42",
      "user_agent": "Mozilla/5.0...",
      "event_hash": "a3f2b1c4...",
      "recorded_at": "2026-06-13T10:30:00Z"
    }
  ],
  "pagination": {
    "cursor": "eyJ...",
    "has_more": true,
    "total_count": 127,
    "page_size": 50
  }
}
```

---

## 12. Health & System APIs

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Overall system health |
| GET | `/health/ready` | No | Kubernetes readiness probe |
| GET | `/health/live` | No | Kubernetes liveness probe |
| GET | `/health/services` | Yes (admin) | Detailed per-service health |

#### GET `/health`

**Response (200):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 864000,
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "vector_store": "healthy",
    "object_store": "healthy"
  }
}
```

---

## 13. WebSocket APIs

### 13.1 Agent Execution Stream

**URL:** `wss://api.eaioc.example.com/ws/v1/agents/executions/{execution_id}?token=<jwt>`

**Server → Client Events:**
```json
{"event": "execution.started", "execution_id": "exec_...", "timestamp": "..."}
{"event": "step.started", "step_id": "research", "agent_name": "Research Agent"}
{"event": "step.llm_chunk", "step_id": "research", "content": "Based on..."}
{"event": "step.completed", "step_id": "research", "duration_ms": 3400, "cost": 0.05}
{"event": "step.approval_required", "step_id": "review", "context": {...}}
{"event": "execution.completed", "output": {...}, "total_cost": 0.23, "duration_ms": 12000}
{"event": "execution.failed", "error": "Budget exceeded", "step_id": "analysis"}
```

### 13.2 Voice Session Stream

See Section 8.1 above.

---

## 14. Rate Limiting Strategy

| Endpoint Group | Default Limit | Enterprise Limit | Strategy |
|---|---|---|---|
| Auth (login/register) | 20 req/min | 50 req/min | Per-IP sliding window |
| User Management | 100 req/min | 500 req/min | Per-user token bucket |
| Agent CRUD | 200 req/min | 1000 req/min | Per-API-key token bucket |
| Agent Execute | 50 req/min | 500 req/min | Per-API-key token bucket |
| RAG Search | 100 req/min | 1000 req/min | Per-API-key token bucket |
| RAG Upload | 20 req/min | 100 req/min | Per-API-key token bucket |
| Multimodal | 30 req/min | 200 req/min | Per-API-key token bucket |
| Voice Sessions | 10 req/min | 100 req/min | Per-user token bucket |
| Audit | 100 req/min | 500 req/min | Per-API-key token bucket |
| MLOps | 200 req/min | 1000 req/min | Per-API-key token bucket |

**Rate Limit Response (429):**
```json
{
  "type": "https://eaioc.dev/errors/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "You have exceeded the rate limit of 100 requests per minute.",
  "retry_after": 32
}
```

---

## 15. API Versioning Strategy

| Version | Status | Sunset Date | Notes |
|---|---|---|---|
| `v1` | **Active** | — | Current stable version |
| `v2` | Planned | — | Introduced only for breaking changes |

**Versioning Rules:**
- Non-breaking changes (new fields, new endpoints) are added to current version
- Breaking changes (removed fields, changed semantics) require new major version
- Deprecated versions have 6-month sunset period with `Sunset` header
- `Deprecation` header added to deprecated endpoints

---

*Document Owner: API Architect / Technical Lead*  
*Next Review: Upon stakeholder approval of Phase 4*
