# Sequence Diagrams

**Product:** Enterprise AI Operations Center  
**Version:** 1.0  
**Date:** 2026-06-13  
**Classification:** Internal — Confidential  
**Status:** Draft — Awaiting Approval

---

## 1. Overview

This document provides sequence diagrams for all critical flows in the platform. Each diagram captures the happy path plus key error/edge cases.

---

## 2. User Registration Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant GW as API Gateway
    participant Auth as Auth Service
    participant DB as PostgreSQL
    participant Redis as Redis
    participant Email as Email Service
    participant Audit as Audit Service

    User->>FE: Fill registration form
    FE->>GW: POST /api/v1/auth/register<br/>{email, password, full_name, org_name}
    GW->>GW: Rate limit check (20 req/min)
    GW->>Auth: Forward request
    
    Auth->>Auth: Validate input (Pydantic)
    Auth->>DB: Check if email exists
    
    alt Email Already Exists
        DB-->>Auth: User found
        Auth-->>GW: 409 Conflict
        GW-->>FE: 409 {error: "Email already registered"}
        FE-->>User: Show error message
    else Email Available
        DB-->>Auth: Not found
        Auth->>Auth: Hash password (Argon2id)
        Auth->>Auth: Generate verification token
        Auth->>DB: BEGIN TRANSACTION
        Auth->>DB: INSERT tenant (org)
        Auth->>DB: INSERT user (inactive)
        Auth->>DB: INSERT default roles for tenant
        Auth->>DB: COMMIT
        Auth->>Redis: Store verification token (TTL 24h)
        Auth->>Email: Send verification email (async)
        Auth->>Audit: Emit UserRegistered event (async)
        Auth-->>GW: 201 Created {user_id, message}
        GW-->>FE: 201 Created
        FE-->>User: "Check your email to verify"
    end
```

---

## 3. SSO Login Flow (SAML 2.0)

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant GW as API Gateway
    participant Auth as Auth Service
    participant IdP as Identity Provider<br/>(Okta / Azure AD)
    participant DB as PostgreSQL
    participant Redis as Redis
    participant Audit as Audit Service

    User->>FE: Click "Sign in with SSO"
    FE->>GW: GET /api/v1/auth/sso/initiate?provider=okta
    GW->>Auth: Forward
    Auth->>Auth: Generate SAML AuthnRequest
    Auth->>Redis: Store request state (CSRF token)
    Auth-->>FE: 302 Redirect to IdP SSO URL

    FE->>IdP: Redirect user to IdP login
    User->>IdP: Enter IdP credentials
    IdP->>IdP: Authenticate user
    IdP-->>FE: POST /api/v1/auth/sso/callback (SAMLResponse)
    
    FE->>GW: POST /api/v1/auth/sso/callback<br/>{SAMLResponse, RelayState}
    GW->>Auth: Forward
    Auth->>Redis: Validate CSRF state
    Auth->>Auth: Validate SAML signature (IdP cert)
    Auth->>Auth: Extract user attributes (email, name, groups)
    Auth->>DB: Find or create user by email
    
    alt New SSO User
        Auth->>DB: CREATE user (auto-verified, SSO-linked)
        Auth->>DB: Assign default role based on IdP groups
    end
    
    Auth->>Auth: Generate JWT + Refresh Token
    Auth->>Redis: Store session
    Auth->>Audit: Emit SSOLoginCompleted event
    Auth-->>FE: 200 {access_token, refresh_token}
    FE->>FE: Store tokens, redirect to dashboard
    FE-->>User: Dashboard loaded
```

---

## 4. Agent Workflow Execution Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant GW as API Gateway
    participant RBAC as RBAC Engine
    participant Agent as Agent Engine
    participant RAG as RAG Service
    participant LLM as LLM Provider
    participant Redis as Redis Streams
    participant DB as PostgreSQL
    participant Audit as Audit Service
    participant MLOps as MLOps Service

    User->>FE: Click "Run Workflow"
    FE->>GW: POST /api/v1/workflows/{id}/execute<br/>{input_data}
    GW->>GW: Validate JWT
    GW->>RBAC: Authorize(user, workflows:execute, workflow_id)
    RBAC-->>GW: Allowed

    GW->>Agent: Execute workflow
    Agent->>DB: Load workflow DAG definition
    Agent->>Agent: Validate DAG (acyclic, all agents exist)
    Agent->>DB: Create Execution record (status=RUNNING)
    Agent->>Redis: Emit ExecutionStarted event
    Agent-->>FE: 202 Accepted {execution_id}
    
    Note over FE: Frontend opens WebSocket for live updates
    FE->>GW: WSS /ws/v1/agents/executions/{execution_id}

    loop For each DAG level (topological order)
        Agent->>Agent: Get parallel nodes for this level
        
        par Execute nodes in parallel
            Agent->>Agent: Resolve input mappings
            
            alt Node requires RAG retrieval
                Agent->>RAG: Search(query, user_rbac_context)
                RAG->>RBAC: Filter accessible documents
                RAG-->>Agent: Retrieved chunks + citations
            end
            
            Agent->>LLM: Generate(prompt + context)
            
            alt LLM Call Succeeds
                LLM-->>Agent: Response + token count
            else LLM Call Fails
                Agent->>Agent: Try fallback provider
                Agent->>LLM: Generate (fallback provider)
                LLM-->>Agent: Fallback response
            end
            
            Agent->>Agent: Check guardrails (PII, content filter)
            Agent->>Agent: Check cost budget
            
            alt Cost Budget Exceeded
                Agent->>DB: Update Execution (status=BUDGET_EXCEEDED)
                Agent->>Redis: Emit ExecutionFailed event
                Agent->>Audit: Log budget breach
            end
            
            Agent->>DB: Store StepExecution result
            Agent->>Redis: Emit StepCompleted event
            Agent->>MLOps: Record cost + tokens (async)
        end
        
        Redis-->>FE: Stream step completion events
        FE-->>User: Update DAG visualization (live)
    end

    Agent->>DB: Update Execution (status=COMPLETED, output)
    Agent->>Redis: Emit ExecutionCompleted event
    Agent->>Audit: Log execution completion
    Redis-->>FE: Execution complete event
    FE-->>User: Show results + cost summary
```

---

## 5. Human-in-the-Loop Approval Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant Agent as Agent Engine
    participant Redis as Redis
    participant DB as PostgreSQL
    participant Notif as Notification Service

    Note over Agent: Workflow reaches approval node

    Agent->>DB: Update StepExecution (status=AWAITING_APPROVAL)
    Agent->>DB: Update Execution (status=PAUSED)
    Agent->>Redis: Emit ApprovalRequired event
    Agent->>Notif: Send approval notification (email/Slack)
    
    Redis-->>FE: ApprovalRequired event
    FE-->>User: Show approval dialog with context

    alt User Approves
        User->>FE: Click "Approve"
        FE->>Agent: POST /api/v1/workflows/executions/{id}/approve<br/>{step_id, decision: "approve", comment}
        Agent->>DB: Update StepExecution (status=APPROVED)
        Agent->>DB: Update Execution (status=RUNNING)
        Agent->>Agent: Resume DAG execution from approved node
        Agent->>Redis: Emit ExecutionResumed event
    else User Rejects
        User->>FE: Click "Reject"
        FE->>Agent: POST /api/v1/workflows/executions/{id}/approve<br/>{step_id, decision: "reject", reason}
        Agent->>DB: Update StepExecution (status=REJECTED)
        Agent->>DB: Update Execution (status=REJECTED)
        Agent->>Redis: Emit ExecutionRejected event
    end
```

---

## 6. RAG Document Ingestion Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant GW as API Gateway
    participant RAG as RAG Service
    participant AV as ClamAV
    participant Parser as Document Parser
    participant Chunker as Chunking Engine
    participant Embedder as Embedding Provider
    participant VecDB as pgvector
    participant ObjStore as Object Store
    participant DB as PostgreSQL
    participant Audit as Audit Service

    User->>FE: Upload document to knowledge base
    FE->>GW: POST /api/v1/rag/knowledge-bases/{kb_id}/documents<br/>(multipart/form-data)
    GW->>GW: Validate JWT + RBAC check
    GW->>RAG: Forward upload

    RAG->>RAG: Validate file type and size (<100MB)
    RAG->>AV: Scan file for malware
    
    alt Malware Detected
        AV-->>RAG: INFECTED
        RAG-->>GW: 422 {error: "File failed security scan"}
        GW-->>FE: Show error
    else Clean
        AV-->>RAG: CLEAN
        RAG->>ObjStore: Store raw document
        RAG->>DB: Create Document record (status=PROCESSING)
        RAG-->>FE: 202 Accepted {document_id, status: "processing"}

        Note over RAG: Async processing (Celery worker)

        RAG->>ObjStore: Retrieve raw document
        RAG->>Parser: Parse document to text
        Parser-->>RAG: Extracted text + metadata

        RAG->>Chunker: Chunk text (strategy from KB config)
        Chunker-->>RAG: List of chunks with positions

        loop For each chunk batch (batch_size=100)
            RAG->>Embedder: Generate embeddings
            Embedder-->>RAG: Embedding vectors (1536-dim)
            RAG->>VecDB: Upsert chunks + embeddings
            RAG->>DB: Store chunk metadata
        end

        RAG->>DB: Update Document (status=READY, chunk_count, metadata)
        RAG->>Audit: Emit DocumentIngested event
    end
```

---

## 7. RAG Retrieval with RBAC Flow

```mermaid
sequenceDiagram
    actor User
    participant GW as API Gateway
    participant RAG as RAG Service
    participant RBAC as RBAC Engine
    participant VecDB as pgvector
    participant BM25 as BM25 Index
    participant Cache as Redis Cache
    participant Audit as Audit Service

    User->>GW: POST /api/v1/rag/search<br/>{query, knowledge_base_id, top_k: 10}
    GW->>GW: Validate JWT
    GW->>RAG: Forward search request

    RAG->>RBAC: Get accessible document IDs for user in KB
    RBAC->>Cache: Check permission cache
    Cache-->>RBAC: Accessible doc IDs [doc_1, doc_5, doc_12, ...]
    RBAC-->>RAG: Filtered document ID set

    par Parallel Search
        RAG->>RAG: Embed query
        RAG->>VecDB: ANN search (query_embedding, filter=doc_ids, top_k=20)
        VecDB-->>RAG: Semantic results (20 chunks + scores)
    and
        RAG->>BM25: Keyword search (query, filter=doc_ids, top_k=20)
        BM25-->>RAG: Keyword results (20 chunks + scores)
    end

    RAG->>RAG: Reciprocal Rank Fusion (semantic + keyword)
    RAG->>RAG: Re-rank top 10 results
    RAG->>RAG: Fit within context window (token limit)
    RAG->>RAG: Attach citations (doc_id, page, score)
    RAG->>Audit: Log search event (async)
    RAG-->>GW: 200 {results: [...], citations: [...], metadata}
    GW-->>User: Search results with citations
```

---

## 8. Voice Conversation Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant GW as API Gateway
    participant Voice as Voice Service
    participant STT as Whisper STT
    participant Agent as Agent Engine
    participant TTS as Coqui TTS
    participant Redis as Redis

    User->>FE: Click "Start Voice Session"
    FE->>GW: WSS /ws/v1/voice/sessions
    GW->>Voice: Establish WebSocket
    Voice->>Redis: Create session {session_id, user_id, context: []}
    Voice-->>FE: {type: "session_started", session_id}

    loop Voice Conversation
        User->>FE: Speak into microphone
        FE->>FE: VAD: Detect speech activity
        FE->>Voice: {type: "audio", data: <base64_pcm>}
        
        Voice->>Voice: Buffer audio chunks
        Voice->>STT: Send audio buffer
        STT-->>Voice: {text: "Summarize today's reports", confidence: 0.95}
        Voice-->>FE: {type: "transcript", text: "...", is_final: true}

        Voice->>Redis: Append to session context
        Voice->>Agent: POST /api/v1/agents/{id}/execute<br/>{input: transcript, context: session_history}
        
        Agent->>Agent: Execute agent with context
        Agent-->>Voice: {response: "Here is a summary..."}

        Voice->>Redis: Append response to context
        Voice->>TTS: Synthesize response text
        
        loop Stream audio chunks
            TTS-->>Voice: Audio chunk (PCM)
            Voice-->>FE: {type: "response", audio: <base64>, is_final: false}
            FE->>FE: Play audio chunk
        end
        
        Voice-->>FE: {type: "response", text: "...", is_final: true}
        FE-->>User: Display text + play audio
    end

    User->>FE: Click "End Session"
    FE->>Voice: {type: "session_end"}
    Voice->>Redis: Mark session completed
    Voice-->>FE: {type: "session_ended"}
```

---

## 9. Edge Model Sync Flow

```mermaid
sequenceDiagram
    participant Edge as Edge Device
    participant GRPC as gRPC Server<br/>(Edge Manager)
    participant RBAC2 as RBAC Engine
    participant DB2 as PostgreSQL
    participant ObjStore2 as Object Store
    participant MQTT as MQTT Broker
    participant MLOps2 as MLOps Service

    Note over Edge: Periodic sync check (every 5 min)

    Edge->>GRPC: GetModelManifest(device_id, current_versions)
    GRPC->>GRPC: Verify device certificate (mTLS)
    GRPC->>RBAC2: Check device authorization for models
    GRPC->>DB2: Get latest model versions for device
    
    alt New Version Available
        DB2-->>GRPC: Updated manifest
        GRPC-->>Edge: ModelManifest {models: [{id, version, checksum, size}]}
        
        Edge->>Edge: Compare with local versions
        Edge->>GRPC: DownloadModel(model_id, version)
        
        loop Stream model chunks
            GRPC->>ObjStore2: Read model file
            ObjStore2-->>GRPC: File chunk
            GRPC-->>Edge: ModelChunk {data, sequence, total}
        end
        
        Edge->>Edge: Verify checksum (SHA-256)
        Edge->>Edge: Load model into ONNX Runtime
        Edge->>Edge: Run validation inference
        
        alt Validation Passes
            Edge->>MQTT: Publish telemetry/device_id<br/>{model_updated: true, version, status: "active"}
        else Validation Fails
            Edge->>Edge: Rollback to previous version
            Edge->>MQTT: Publish telemetry/device_id<br/>{model_updated: false, error: "validation_failed"}
        end
    else No Updates
        DB2-->>GRPC: Same versions
        GRPC-->>Edge: ModelManifest {models: []} (no changes)
    end

    Note over Edge: Continuous telemetry reporting

    loop Every 60 seconds
        Edge->>MQTT: Publish telemetry/device_id<br/>{inference_count, avg_latency_ms, error_rate,<br/>memory_usage, cpu_usage, model_versions}
        MQTT->>MLOps2: Forward telemetry
        MLOps2->>DB2: Store metrics
    end
```

---

## 10. Token Refresh Flow

```mermaid
sequenceDiagram
    actor Client
    participant GW as API Gateway
    participant Auth as Auth Service
    participant Redis as Redis
    participant DB as PostgreSQL

    Note over Client: Access token expired (401 on API call)

    Client->>GW: POST /api/v1/auth/refresh<br/>{refresh_token}
    GW->>Auth: Forward (no JWT validation for this endpoint)
    
    Auth->>DB: Lookup refresh token hash
    
    alt Token Valid & Not Expired
        DB-->>Auth: Session record
        Auth->>Auth: Generate new JWT (15 min)
        Auth->>Auth: Generate new refresh token (rotation)
        Auth->>DB: Update session with new refresh token hash
        Auth->>DB: Invalidate old refresh token
        Auth->>Redis: Update session cache
        Auth-->>Client: 200 {access_token, refresh_token, expires_in}
    else Token Expired or Revoked
        DB-->>Auth: Not found or expired
        Auth-->>Client: 401 {error: "Refresh token invalid"}
        Note over Client: Redirect to login
    end
```

---

## 11. Cost Budget Enforcement Flow

```mermaid
sequenceDiagram
    participant Agent as Agent Engine
    participant LLM2 as LLM Provider
    participant MLOps3 as MLOps Service
    participant DB3 as PostgreSQL
    participant Redis2 as Redis
    participant Audit2 as Audit Service

    Note over Agent: During workflow execution

    Agent->>LLM2: Generate(prompt)
    LLM2-->>Agent: Response {tokens_in: 2000, tokens_out: 500}
    
    Agent->>Agent: Calculate cost (model pricing table)
    Agent->>Redis2: INCRBY execution:{id}:cost {step_cost}
    Agent->>Redis2: GET execution:{id}:cost
    Redis2-->>Agent: Current total: $0.45
    
    Agent->>DB3: Get execution budget limit ($0.50)
    
    alt Under Budget
        Agent->>Agent: Continue execution
        Agent->>MLOps3: Record cost metric (async)
    else Budget Exceeded
        Agent->>DB3: Update Execution (status=BUDGET_EXCEEDED)
        Agent->>Redis2: Emit BudgetExceeded event
        Agent->>Audit2: Log budget breach {execution_id, budget, actual}
        Agent->>Agent: Terminate remaining steps
        Agent-->>Agent: Return partial results with budget warning
    end
```

---

## 12. Audit Hash Chain Integrity Flow

```mermaid
sequenceDiagram
    participant Service as Any Service
    participant Redis3 as Redis Streams
    participant Audit3 as Audit Service
    participant DB4 as PostgreSQL<br/>(Append-Only)

    Service->>Redis3: XADD audit_events {event_data}
    
    Note over Audit3: Audit consumer (continuous)
    
    Redis3-->>Audit3: New audit event
    Audit3->>DB4: Get last hash chain entry
    DB4-->>Audit3: {sequence: 1042, hash: "abc123..."}
    
    Audit3->>Audit3: Compute new hash:<br/>SHA-256(prev_hash + event_data + timestamp)
    
    Audit3->>DB4: INSERT audit_event<br/>{sequence: 1043, hash: "def456...",<br/>prev_hash: "abc123...", event_data,<br/>timestamp, tenant_id}
    
    Note over DB4: Table has no UPDATE/DELETE permissions<br/>Only INSERT allowed (append-only)

    Note over Audit3: Periodic integrity verification (hourly)
    
    Audit3->>DB4: SELECT * FROM audit_events<br/>ORDER BY sequence LIMIT 1000
    DB4-->>Audit3: Event chain
    
    loop Verify each event
        Audit3->>Audit3: Recompute hash from prev_hash + data
        Audit3->>Audit3: Compare with stored hash
        alt Hash Mismatch
            Audit3->>Audit3: ALERT: Tampering detected!
        end
    end
```

---

## 13. Multi-Agent Communication Flow

```mermaid
sequenceDiagram
    participant Orchestrator as Workflow Orchestrator
    participant AgentA as Research Agent
    participant AgentB as Analysis Agent
    participant AgentC as Report Agent
    participant Redis4 as Redis Streams
    participant LLM3 as LLM Provider
    participant RAG2 as RAG Service

    Orchestrator->>Orchestrator: Parse DAG: A → B → C

    Note over Orchestrator: Level 1: Research Agent
    Orchestrator->>AgentA: Execute(input: user_query)
    AgentA->>RAG2: Search knowledge base
    RAG2-->>AgentA: Retrieved context
    AgentA->>LLM3: Generate research summary
    LLM3-->>AgentA: Research findings
    AgentA->>Redis4: XADD agent_msgs {from: A, to: B, data: findings}
    AgentA-->>Orchestrator: StepResult {output: findings}

    Note over Orchestrator: Level 2: Analysis Agent
    Orchestrator->>Orchestrator: Map A.output → B.input
    Orchestrator->>AgentB: Execute(input: research_findings)
    AgentB->>LLM3: Analyze findings, extract insights
    LLM3-->>AgentB: Analysis with insights
    AgentB->>Redis4: XADD agent_msgs {from: B, to: C, data: analysis}
    AgentB-->>Orchestrator: StepResult {output: analysis}

    Note over Orchestrator: Level 3: Report Agent
    Orchestrator->>Orchestrator: Map B.output → C.input
    Orchestrator->>AgentC: Execute(input: analysis)
    AgentC->>LLM3: Generate executive report
    LLM3-->>AgentC: Formatted report
    AgentC-->>Orchestrator: StepResult {output: report}

    Orchestrator->>Orchestrator: Aggregate final output
    Orchestrator-->>Orchestrator: ExecutionComplete {output: report}
```

---

*Document Owner: Solutions Architect*  
*Next Review: Upon stakeholder approval of Phase 2*
