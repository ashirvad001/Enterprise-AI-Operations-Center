# Data Dictionary

**Product:** Enterprise AI Operations Center  
**Version:** 1.0  
**Date:** 2026-06-13  
**Classification:** Internal — Confidential  
**Status:** Draft — Awaiting Approval

---

## 1. Overview

This data dictionary provides column-level documentation for every table in the platform. Each entry includes the column name, type, constraints, and business meaning.

**Conventions:**
- `PK` = Primary Key
- `FK` = Foreign Key
- `UK` = Unique constraint
- `NN` = NOT NULL
- `DEF` = Has default value
- `RLS` = Table has Row-Level Security

---

## 2. Auth Schema

### 2.1 auth.tenants (RLS: No — admin-managed)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Unique tenant identifier (UUIDv7) |
| `name` | VARCHAR(255) | NN | Human-readable organization name |
| `slug` | VARCHAR(100) | NN, UK | URL-safe organization identifier (e.g., "acme-corp") |
| `plan` | VARCHAR(50) | NN, DEF="free" | Subscription plan: "free", "team", "enterprise", "custom" |
| `settings` | JSONB | NN, DEF="{}" | Tenant-level configuration: allowed LLM providers, branding, limits |
| `is_active` | BOOLEAN | NN, DEF=true | Active/suspended status. Suspended tenants lose API access |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Tenant registration timestamp |
| `updated_at` | TIMESTAMPTZ | NN, DEF=NOW() | Last modification timestamp (trigger-updated) |
| `deleted_at` | TIMESTAMPTZ | Nullable | Soft-delete timestamp. NULL = active |

### 2.2 auth.users (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Unique user identifier (UUIDv7) |
| `tenant_id` | UUID | NN, FK→tenants | Organization the user belongs to |
| `email` | VARCHAR(320) | NN, UK(tenant_id, email) | User email address. RFC 5321 max length. Unique within tenant |
| `hashed_password` | VARCHAR(255) | Nullable | Argon2id hash. NULL for SSO-only users |
| `full_name` | VARCHAR(255) | NN | Display name |
| `is_active` | BOOLEAN | NN, DEF=false | Account active status. Set true after email verification |
| `is_verified` | BOOLEAN | NN, DEF=false | Email verification status |
| `mfa_enabled` | BOOLEAN | NN, DEF=false | Whether TOTP MFA is enrolled |
| `mfa_secret` | VARCHAR(255) | Nullable | AES-256 encrypted TOTP secret. NULL if MFA not enabled |
| `avatar_url` | VARCHAR(2048) | Nullable | Profile picture URL |
| `metadata` | JSONB | NN, DEF="{}" | Extensible user metadata: preferences, SSO attributes |
| `last_login_at` | TIMESTAMPTZ | Nullable | Timestamp of most recent successful login |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Account creation timestamp |
| `updated_at` | TIMESTAMPTZ | NN, DEF=NOW() | Last modification timestamp |
| `deleted_at` | TIMESTAMPTZ | Nullable | Soft-delete timestamp. NULL = active |

### 2.3 auth.sessions (RLS: Yes — via user_id→tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Session identifier |
| `user_id` | UUID | NN, FK→users | User who owns this session |
| `refresh_token_hash` | VARCHAR(255) | NN | SHA-256 hash of the refresh token (token never stored in plaintext) |
| `ip_address` | INET | Nullable | Client IP address at session creation |
| `user_agent` | TEXT | Nullable | Browser/client user agent string |
| `is_revoked` | BOOLEAN | NN, DEF=false | True when session is explicitly revoked (logout) |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Session creation timestamp |
| `expires_at` | TIMESTAMPTZ | NN | Session expiry (refresh token TTL: 7 days default) |

### 2.4 auth.api_keys (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | API key identifier |
| `user_id` | UUID | NN, FK→users | User who created this key |
| `tenant_id` | UUID | NN, FK→tenants | Tenant scope for this key |
| `key_hash` | VARCHAR(255) | NN, UK | SHA-256 hash of the full API key. Key shown once at creation |
| `key_prefix` | VARCHAR(12) | NN | First 8 chars of key for identification (e.g., "eaioc_sk_a1b2") |
| `name` | VARCHAR(255) | NN | Human-readable key name (e.g., "CI/CD Pipeline Key") |
| `scopes` | TEXT[] | NN, DEF="{}" | Permitted API scopes: ["agents:read", "rag:search"] |
| `is_active` | BOOLEAN | NN, DEF=true | Active/revoked status |
| `last_used_at` | TIMESTAMPTZ | Nullable | Last API call timestamp using this key |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Key creation timestamp |
| `expires_at` | TIMESTAMPTZ | Nullable | Optional expiry. NULL = no expiry |

### 2.5 auth.sso_connections (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | SSO connection identifier |
| `tenant_id` | UUID | NN, FK→tenants | Tenant that owns this SSO configuration |
| `provider` | VARCHAR(50) | NN | SSO protocol: "saml" or "oidc" |
| `provider_config_encrypted` | TEXT | NN | AES-256 encrypted JSON containing IdP config (client_id, client_secret, metadata_url, etc.) |
| `entity_id` | VARCHAR(512) | UK | SAML Entity ID or OIDC Issuer URL. Globally unique |
| `acs_url` | VARCHAR(2048) | Nullable | SAML Assertion Consumer Service URL |
| `metadata_url` | VARCHAR(2048) | Nullable | IdP metadata URL for SAML auto-configuration |
| `is_active` | BOOLEAN | NN, DEF=true | Active/disabled status |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Connection creation timestamp |
| `updated_at` | TIMESTAMPTZ | NN, DEF=NOW() | Last modification timestamp |

### 2.6 auth.password_reset_tokens

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Token record identifier |
| `user_id` | UUID | NN, FK→users | User requesting password reset |
| `token_hash` | VARCHAR(255) | NN, UK | SHA-256 hash of reset token sent via email |
| `is_used` | BOOLEAN | NN, DEF=false | True after token is consumed |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Token creation timestamp |
| `expires_at` | TIMESTAMPTZ | NN | Token expiry (default: 1 hour) |

---

## 3. RBAC Schema

### 3.1 rbac.permissions (System-wide, no tenant isolation)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Permission identifier |
| `resource` | VARCHAR(100) | NN, UK(resource, action) | Resource being protected: "agents", "rag", "voice", "rbac", etc. |
| `action` | VARCHAR(100) | NN, UK(resource, action) | Action on the resource: "create", "read", "update", "delete", "execute", "manage" |
| `description` | TEXT | Nullable | Human-readable explanation of what this permission grants |
| `is_system` | BOOLEAN | NN, DEF=true | System-defined permissions cannot be deleted by tenants |

### 3.2 rbac.roles (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Role identifier |
| `tenant_id` | UUID | NN, FK→tenants | Tenant that owns this role |
| `name` | VARCHAR(100) | NN, UK(tenant_id, name) | Role name: "Super Admin", "Developer", custom names |
| `description` | TEXT | Nullable | Human-readable role description |
| `is_system_role` | BOOLEAN | NN, DEF=false | System roles (Super Admin, etc.) cannot be deleted |
| `is_active` | BOOLEAN | NN, DEF=true | Active/disabled status |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Role creation timestamp |
| `updated_at` | TIMESTAMPTZ | NN, DEF=NOW() | Last modification timestamp |

### 3.3 rbac.role_permissions

| Column | Type | Constraints | Description |
|---|---|---|---|
| `role_id` | UUID | PK, FK→roles | Role receiving the permission |
| `permission_id` | UUID | PK, FK→permissions | Permission being granted |
| `assigned_at` | TIMESTAMPTZ | NN, DEF=NOW() | When the permission was assigned to this role |

### 3.4 rbac.teams (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Team identifier |
| `tenant_id` | UUID | NN, FK→tenants | Tenant that owns this team |
| `name` | VARCHAR(255) | NN, UK(tenant_id, name) | Team name |
| `description` | TEXT | Nullable | Team description |
| `parent_team_id` | UUID | FK→teams | Parent team for hierarchical structure. NULL = top-level |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Team creation timestamp |
| `updated_at` | TIMESTAMPTZ | NN, DEF=NOW() | Last modification timestamp |
| `deleted_at` | TIMESTAMPTZ | Nullable | Soft-delete timestamp |

### 3.5 rbac.team_members

| Column | Type | Constraints | Description |
|---|---|---|---|
| `team_id` | UUID | PK, FK→teams | Team |
| `user_id` | UUID | PK, FK→users | User added to the team |
| `joined_at` | TIMESTAMPTZ | NN, DEF=NOW() | When user was added to team |

### 3.6 rbac.user_roles

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Assignment identifier |
| `user_id` | UUID | NN, FK→users | User receiving the role |
| `role_id` | UUID | NN, FK→roles | Role being assigned |
| `team_id` | UUID | FK→teams | Team scope. NULL = org-level (applies to all teams) |
| `assigned_by` | UUID | FK→users | Admin who made this assignment |
| `assigned_at` | TIMESTAMPTZ | NN, DEF=NOW() | When the role was assigned |

### 3.7 rbac.resource_acls (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | ACL entry identifier |
| `tenant_id` | UUID | NN, FK→tenants | Tenant scope |
| `resource_id` | UUID | NN | ID of the protected resource (document, agent, KB) |
| `resource_type` | VARCHAR(100) | NN | Type of resource: "document", "agent", "knowledge_base" |
| `principal_id` | UUID | NN | ID of the entity receiving access (user, team, or role) |
| `principal_type` | VARCHAR(20) | NN | Type of principal: "user", "team", "role" |
| `actions` | TEXT[] | NN | Permitted actions: ["read"], ["read", "write"], etc. |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | ACL creation timestamp |
| `expires_at` | TIMESTAMPTZ | Nullable | Optional time-limited access |

---

## 4. Agents Schema

### 4.1 agents.agents (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Agent identifier |
| `tenant_id` | UUID | NN, FK→tenants | Owning tenant |
| `name` | VARCHAR(255) | NN, UK(tenant_id, name, version) | Agent name |
| `description` | TEXT | Nullable | What this agent does |
| `version` | VARCHAR(20) | NN, DEF="1.0.0" | Semantic version |
| `type` | VARCHAR(50) | NN, DEF="conversational" | Agent type: "conversational", "research", "code_review", "data_analysis", "custom" |
| `model_config` | JSONB | NN, DEF="{}" | LLM config: `{"provider": "openai", "model": "gpt-4o", "temperature": 0.7, "max_tokens": 4096}` |
| `tools_config` | JSONB | NN, DEF="[]" | List of tools: `[{"name": "web_search", "config": {...}}]` |
| `system_prompt` | TEXT | Nullable | System prompt template for this agent |
| `guardrails` | JSONB | NN, DEF="{}" | Output validation rules: `{"block_pii": true, "content_filter": "strict"}` |
| `cost_budget` | JSONB | NN, DEF | Per-execution cost limits: `{"max_cost_per_execution": 1.0, "max_tokens": 100000}` |
| `is_active` | BOOLEAN | NN, DEF=true | Active/disabled status |
| `created_by` | UUID | NN, FK→users | User who created this agent |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NN, DEF=NOW() | Last modification timestamp |
| `deleted_at` | TIMESTAMPTZ | Nullable | Soft-delete timestamp |

### 4.2 agents.workflows (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Workflow identifier |
| `tenant_id` | UUID | NN, FK→tenants | Owning tenant |
| `name` | VARCHAR(255) | NN, UK(tenant_id, name) | Workflow name |
| `description` | TEXT | Nullable | What this workflow does |
| `dag_definition` | JSONB | NN | DAG structure: `{"nodes": [...], "edges": [...]}` — validated for acyclicity |
| `variables` | JSONB | NN, DEF="{}" | Workflow-level variables and defaults |
| `trigger_config` | JSONB | NN, DEF="{}" | Trigger configuration: `{"type": "manual"}` or `{"type": "schedule", "cron": "..."}` |
| `is_active` | BOOLEAN | NN, DEF=true | Active/disabled status |
| `created_by` | UUID | NN, FK→users | User who created this workflow |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NN, DEF=NOW() | Last modification timestamp |
| `deleted_at` | TIMESTAMPTZ | Nullable | Soft-delete timestamp |

### 4.3 agents.workflow_executions (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Execution identifier |
| `workflow_id` | UUID | NN, FK→workflows | Workflow being executed |
| `tenant_id` | UUID | NN, FK→tenants | Tenant context |
| `triggered_by` | UUID | NN, FK→users | User who triggered execution |
| `status` | VARCHAR(30) | NN, DEF="pending", CHECK | Execution status: pending, running, paused, completed, failed, cancelled, budget_exceeded, rejected, timeout |
| `input_data` | JSONB | NN, DEF="{}" | Input parameters provided by user |
| `output_data` | JSONB | Nullable | Final output from terminal DAG nodes |
| `total_cost` | DECIMAL(12,6) | NN, DEF=0 | Accumulated USD cost across all steps |
| `total_tokens` | INTEGER | NN, DEF=0 | Total tokens consumed (input + output) |
| `error_message` | TEXT | Nullable | Error description if status is "failed" |
| `started_at` | TIMESTAMPTZ | NN, DEF=NOW() | Execution start timestamp |
| `completed_at` | TIMESTAMPTZ | Nullable | Execution completion timestamp |

### 4.4 agents.step_executions

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Step execution identifier |
| `execution_id` | UUID | NN, FK→executions (CASCADE) | Parent workflow execution |
| `node_id` | VARCHAR(100) | NN | Node identifier within the DAG definition |
| `agent_id` | UUID | FK→agents | Agent used for this step (NULL for non-agent nodes) |
| `status` | VARCHAR(30) | NN, DEF="pending", CHECK | Step status: pending, running, completed, failed, awaiting_approval, approved, rejected, skipped, timeout |
| `input_data` | JSONB | NN, DEF="{}" | Resolved input (from mapping + previous step outputs) |
| `output_data` | JSONB | Nullable | Step output data |
| `cost` | DECIMAL(12,6) | NN, DEF=0 | USD cost for this step |
| `tokens_in` | INTEGER | NN, DEF=0 | Input tokens consumed |
| `tokens_out` | INTEGER | NN, DEF=0 | Output tokens generated |
| `duration_ms` | INTEGER | Nullable | Step execution duration in milliseconds |
| `llm_provider` | VARCHAR(50) | Nullable | Which LLM provider was actually used (may differ from config if fallback) |
| `model_name` | VARCHAR(100) | Nullable | Which model was actually used |
| `attempt_number` | INTEGER | NN, DEF=1 | Retry attempt number |
| `error_message` | TEXT | Nullable | Error description if step failed |
| `started_at` | TIMESTAMPTZ | NN, DEF=NOW() | Step start timestamp |
| `completed_at` | TIMESTAMPTZ | Nullable | Step completion timestamp |

### 4.5 agents.agent_templates

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Template identifier |
| `name` | VARCHAR(255) | NN, UK | Template name |
| `category` | VARCHAR(100) | NN | Category: "chat", "research", "code_review", "data_analysis", "custom" |
| `description` | TEXT | Nullable | What this template does |
| `template_config` | JSONB | NN | Full agent + workflow config as template |
| `is_public` | BOOLEAN | NN, DEF=true | Available to all tenants |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Template creation timestamp |

---

## 5. RAG Schema

### 5.1 rag.knowledge_bases (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Knowledge base identifier |
| `tenant_id` | UUID | NN, FK→tenants | Owning tenant |
| `name` | VARCHAR(255) | NN, UK(tenant_id, name) | Knowledge base name |
| `description` | TEXT | Nullable | Purpose and contents description |
| `chunking_config` | JSONB | NN, DEF | Chunking strategy config: `{"strategy": "recursive", "chunk_size": 512, "chunk_overlap": 50}` |
| `embedding_config` | JSONB | NN, DEF | Embedding model config: `{"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536}` |
| `status` | VARCHAR(30) | NN, DEF="active" | Status: "active", "building", "error" |
| `document_count` | INTEGER | NN, DEF=0 | Total number of documents (denormalized for dashboard) |
| `chunk_count` | INTEGER | NN, DEF=0 | Total number of chunks (denormalized for dashboard) |
| `version` | VARCHAR(20) | NN, DEF="1" | Knowledge base version for rollback |
| `created_by` | UUID | NN, FK→users | User who created this KB |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NN, DEF=NOW() | Last modification timestamp |
| `deleted_at` | TIMESTAMPTZ | Nullable | Soft-delete timestamp |

### 5.2 rag.documents (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Document identifier |
| `knowledge_base_id` | UUID | NN, FK→knowledge_bases | Parent knowledge base |
| `tenant_id` | UUID | NN, FK→tenants | Tenant scope (denormalized for RLS performance) |
| `filename` | VARCHAR(512) | NN | Original filename |
| `content_type` | VARCHAR(100) | NN | MIME type: "application/pdf", "text/markdown", etc. |
| `file_size_bytes` | BIGINT | NN | Raw file size in bytes |
| `file_hash_sha256` | VARCHAR(64) | NN | SHA-256 hash of original file (deduplication) |
| `storage_path` | VARCHAR(1024) | NN | Object store path: "s3://bucket/tenant_id/docs/uuid.pdf" |
| `status` | VARCHAR(30) | NN, DEF="pending", CHECK | Processing status: pending, processing, ready, failed, deleting |
| `chunk_count` | INTEGER | NN, DEF=0 | Number of chunks generated from this document |
| `page_count` | INTEGER | Nullable | Number of pages (if applicable) |
| `metadata` | JSONB | NN, DEF="{}" | Custom metadata: `{"author": "...", "department": "...", "tags": [...]}` |
| `uploaded_by` | UUID | NN, FK→users | User who uploaded this document |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Upload timestamp |
| `updated_at` | TIMESTAMPTZ | NN, DEF=NOW() | Last status change timestamp |
| `deleted_at` | TIMESTAMPTZ | Nullable | Soft-delete timestamp |

### 5.3 rag.chunks (RLS: Yes — tenant_id)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, DEF | Chunk identifier |
| `document_id` | UUID | NN, FK→documents (CASCADE) | Source document |
| `knowledge_base_id` | UUID | NN, FK→knowledge_bases | Parent KB (denormalized for search performance) |
| `tenant_id` | UUID | NN, FK→tenants | Tenant scope (denormalized for RLS performance) |
| `content` | TEXT | NN | Raw chunk text content |
| `chunk_index` | INTEGER | NN | Position within the document (0-based) |
| `start_page` | INTEGER | Nullable | Starting page number (for citation) |
| `end_page` | INTEGER | Nullable | Ending page number |
| `start_char` | INTEGER | NN | Starting character offset in original document |
| `end_char` | INTEGER | NN | Ending character offset in original document |
| `token_count` | INTEGER | NN | Token count (using tiktoken cl100k_base) |
| `metadata` | JSONB | NN, DEF="{}" | Chunk-level metadata: `{"heading": "...", "section": "..."}` |
| `embedding` | vector(1536) | Nullable | Dense vector embedding from embedding model |
| `content_tsvector` | tsvector | Generated | PostgreSQL full-text search vector (auto-generated from content) |
| `created_at` | TIMESTAMPTZ | NN, DEF=NOW() | Chunk creation timestamp |

---

## 6. Remaining Schemas (Summary)

### 6.1 multimodal.media_assets — See Database Design doc for full DDL

| Column | Type | Key | Description |
|---|---|---|---|
| `id` | UUID | PK | Asset identifier |
| `tenant_id` | UUID | FK | Tenant scope |
| `filename` | VARCHAR(512) | NN | Original filename |
| `media_type` | VARCHAR(20) | NN | "image", "video", "audio", "document" |
| `content_type` | VARCHAR(100) | NN | MIME type |
| `file_size_bytes` | BIGINT | NN | File size |
| `storage_path` | VARCHAR(1024) | NN | Object store path |
| `status` | VARCHAR(30) | NN | Processing status |
| `metadata` | JSONB | NN | Custom metadata |
| `uploaded_by` | UUID | FK | Uploading user |
| `created_at` | TIMESTAMPTZ | NN | Upload timestamp |
| `deleted_at` | TIMESTAMPTZ | | Soft delete |

### 6.2 voice.sessions — See Database Design doc for full DDL

| Column | Type | Key | Description |
|---|---|---|---|
| `id` | UUID | PK | Session identifier |
| `tenant_id` | UUID | FK | Tenant scope |
| `user_id` | UUID | FK | Session owner |
| `agent_id` | UUID | FK | Agent handling the session |
| `status` | VARCHAR(20) | NN | "active", "completed", "error" |
| `stt_provider` | VARCHAR(50) | NN | Speech-to-text provider |
| `tts_provider` | VARCHAR(50) | NN | Text-to-speech provider |
| `language` | VARCHAR(10) | NN | Session language code |
| `started_at` | TIMESTAMPTZ | NN | Session start |
| `ended_at` | TIMESTAMPTZ | | Session end |

### 6.3 edge.devices — See Database Design doc for full DDL

| Column | Type | Key | Description |
|---|---|---|---|
| `id` | UUID | PK | Device identifier |
| `tenant_id` | UUID | FK | Tenant scope |
| `device_name` | VARCHAR(255) | UK(tenant, name) | Device display name |
| `device_type` | VARCHAR(100) | NN | Hardware type |
| `hardware_info` | JSONB | NN | CPU, RAM, GPU details |
| `certificate_fingerprint` | VARCHAR(64) | UK | mTLS certificate fingerprint |
| `status` | VARCHAR(20) | NN | "registered", "online", "offline", "error", "decommissioned" |
| `last_heartbeat_at` | TIMESTAMPTZ | | Last telemetry receipt |

### 6.4 audit.events — See Database Design doc for full DDL

| Column | Type | Key | Description |
|---|---|---|---|
| `id` | UUID | PK | Event identifier |
| `sequence_num` | BIGSERIAL | UK | Monotonic sequence for hash chain ordering |
| `tenant_id` | UUID | NN | Tenant scope (not FK — audit is independent) |
| `user_id` | UUID | | Acting user (NULL for system events) |
| `request_id` | VARCHAR(64) | NN | Correlation ID for distributed tracing |
| `action` | VARCHAR(100) | NN | Action performed: "user.login", "agent.execute", "document.upload" |
| `resource_type` | VARCHAR(100) | NN | Affected resource type |
| `resource_id` | UUID | | Affected resource ID |
| `outcome` | VARCHAR(20) | NN | "success", "failure", "denied", "error" |
| `details` | JSONB | NN | Action-specific details (changes, parameters, etc.) |
| `ip_address` | INET | | Client IP address |
| `prev_hash` | VARCHAR(64) | | SHA-256 hash of previous event (hash chain) |
| `event_hash` | VARCHAR(64) | NN | SHA-256 hash: `H(prev_hash + action + details + timestamp)` |
| `recorded_at` | TIMESTAMPTZ | NN | Event timestamp |

---

## 7. JSONB Column Schemas

### 7.1 agents.agents.model_config

```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "temperature": 0.7,
  "max_tokens": 4096,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "stop_sequences": [],
  "fallback_chain": [
    {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    {"provider": "ollama", "model": "llama3:8b"}
  ]
}
```

### 7.2 agents.workflows.dag_definition

```json
{
  "nodes": [
    {
      "id": "research",
      "type": "agent",
      "agent_id": "uuid-here",
      "config": {},
      "input_mapping": {"query": "$.input.user_query"},
      "output_mapping": {"findings": "$.output.response"},
      "timeout_seconds": 60,
      "retry_policy": {"max_attempts": 3, "backoff": "exponential"},
      "requires_approval": false
    }
  ],
  "edges": [
    {"from": "research", "to": "analysis", "condition": null}
  ]
}
```

### 7.3 rag.knowledge_bases.chunking_config

```json
{
  "strategy": "recursive",
  "chunk_size": 512,
  "chunk_overlap": 50,
  "separators": ["\n\n", "\n", ". ", " "],
  "length_function": "tiktoken_cl100k"
}
```

### 7.4 agents.agents.guardrails

```json
{
  "block_pii": true,
  "pii_types": ["email", "phone", "ssn", "credit_card"],
  "content_filter": "strict",
  "max_output_tokens": 2048,
  "blocked_topics": [],
  "require_citations": false,
  "custom_validators": []
}
```

---

*Document Owner: Data Architect*  
*Next Review: Upon stakeholder approval of Phase 3*
