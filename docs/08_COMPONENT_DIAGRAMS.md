# Component Diagrams

**Product:** Enterprise AI Operations Center  
**Version:** 1.0  
**Date:** 2026-06-13  
**Classification:** Internal — Confidential  
**Status:** Draft — Awaiting Approval

---

## 1. Overview

This document provides C4 Level 3 (Component) diagrams for each service in the platform, showing internal structure, dependencies, and interactions.

---

## 2. Auth Service — Components

```mermaid
flowchart TB
    subgraph AuthService["Auth Service"]
        direction TB
        subgraph Interface["Interface Layer"]
            AR["Auth Router<br/>/api/v1/auth/*"]
            UR["User Router<br/>/api/v1/users/*"]
        end
        
        subgraph Application["Application Layer"]
            AS["AuthService<br/>register, login, refresh"]
            MS["MFAService<br/>enable, verify TOTP"]
            AKS["APIKeyService<br/>create, rotate, revoke"]
        end
        
        subgraph Domain["Domain Layer"]
            UE["User Entity"]
            SE["Session Entity"]
            AKE["APIKey Entity"]
            PH["PasswordHasher<br/>(Argon2id)"]
            TG["TokenGenerator<br/>(JWT)"]
        end
        
        subgraph Infrastructure["Infrastructure Layer"]
            UR2["UserRepository<br/>(SQLAlchemy)"]
            SR["SessionRepository"]
            AKR["APIKeyRepository"]
            SSO["SSOProvider<br/>(SAML/OIDC)"]
            SC["SessionCache<br/>(Redis)"]
            EM["EmailService<br/>(verification)"]
        end
    end

    AR --> AS
    AR --> MS
    UR --> AKS
    AS --> UE
    AS --> SE
    AS --> PH
    AS --> TG
    MS --> UE
    AKS --> AKE
    AS --> UR2
    AS --> SR
    AS --> SC
    AS --> SSO
    AS --> EM
    AKS --> AKR

    PG["PostgreSQL"] -.-> UR2
    PG -.-> SR
    PG -.-> AKR
    REDIS["Redis"] -.-> SC
    IDP["Identity Provider"] -.-> SSO
```

---

## 3. RBAC Engine — Components

```mermaid
flowchart TB
    subgraph RBACEngine["RBAC Engine"]
        direction TB
        subgraph Interface2["Interface Layer"]
            RR["RBAC Router<br/>/api/v1/rbac/*"]
            MW["AuthZ Middleware<br/>(per-request check)"]
        end
        
        subgraph Application2["Application Layer"]
            RS["RBACService<br/>manage roles & permissions"]
            PE["PermissionEvaluator<br/>authorize(user, resource, action)"]
        end
        
        subgraph Domain2["Domain Layer"]
            RE["Role Entity"]
            PME["Permission Entity"]
            ACL["ResourceACL Entity"]
            TE["Team Entity"]
            PI["PermissionInheritance<br/>(org→team→user)"]
        end
        
        subgraph Infrastructure2["Infrastructure Layer"]
            RR2["RoleRepository"]
            PR["PermissionRepository"]
            ACLR["ACLRepository"]
            PC["PermissionCache<br/>(Redis, TTL 5m)"]
        end
    end

    RR --> RS
    MW --> PE
    RS --> RE
    RS --> PME
    PE --> PI
    PE --> ACL
    RS --> RR2
    RS --> PR
    PE --> PC
    PE --> ACLR

    PG2["PostgreSQL"] -.-> RR2
    PG2 -.-> PR
    PG2 -.-> ACLR
    REDIS2["Redis"] -.-> PC
```

---

## 4. Agent Engine — Components

```mermaid
flowchart TB
    subgraph AgentEngine["Agent Engine"]
        direction TB
        subgraph Interface3["Interface Layer"]
            AGR["Agent Router<br/>/api/v1/agents/*"]
            WFR["Workflow Router<br/>/api/v1/workflows/*"]
            WS["WebSocket Handler<br/>/ws/v1/agents/*"]
        end
        
        subgraph Application3["Application Layer"]
            AGS["AgentService<br/>CRUD, execute"]
            WO["WorkflowOrchestrator<br/>DAG execution engine"]
            TM["ToolManager<br/>tool registry & invocation"]
        end
        
        subgraph Domain3["Domain Layer"]
            AGE["Agent Entity"]
            WFE["Workflow Entity"]
            DAG["DAGDefinition<br/>nodes, edges, validation"]
            EXE["Execution Entity"]
            STEP["StepExecution Entity"]
            GR["Guardrails<br/>output validation"]
            CB["CostBudget<br/>per-execution limits"]
        end
        
        subgraph Infrastructure3["Infrastructure Layer"]
            AGR2["AgentRepository"]
            WFR2["WorkflowRepository"]
            EXR["ExecutionRepository"]
            LLM["LLM Provider Registry<br/>(OpenAI, Anthropic, etc.)"]
            FC["FallbackChain<br/>(with circuit breakers)"]
            TR["ToolRegistry<br/>(built-in + custom)"]
            ES["Event Stream<br/>(Redis Streams)"]
        end
    end

    AGR --> AGS
    WFR --> WO
    WS --> WO
    AGS --> AGE
    WO --> WFE
    WO --> DAG
    WO --> EXE
    WO --> STEP
    WO --> GR
    WO --> CB
    WO --> TM
    AGS --> AGR2
    WO --> WFR2
    WO --> EXR
    WO --> FC
    TM --> TR
    WO --> ES

    FC --> LLM
    PG3["PostgreSQL"] -.-> AGR2
    PG3 -.-> WFR2
    PG3 -.-> EXR
    REDIS3["Redis"] -.-> ES
    EXTLLM["LLM APIs"] -.-> LLM
```

---

## 5. RAG Service — Components

```mermaid
flowchart TB
    subgraph RAGService["RAG Service"]
        direction TB
        subgraph Interface4["Interface Layer"]
            DR["Document Router<br/>/api/v1/documents/*"]
            SR2["Search Router<br/>/api/v1/rag/search"]
            KBR["KB Router<br/>/api/v1/rag/knowledge-bases/*"]
        end
        
        subgraph Application4["Application Layer"]
            IS["IngestionService<br/>parse, chunk, embed, store"]
            RS2["RetrievalService<br/>search, rank, cite"]
            KBS["KBManagementService<br/>create, version, rollback"]
            ES2["EvaluationService<br/>RAGAS metrics"]
        end
        
        subgraph Domain4["Domain Layer"]
            KBE["KnowledgeBase Entity"]
            DE["Document Entity"]
            CE["Chunk Entity"]
            CIT["Citation Value Object"]
            CS2["ChunkingStrategy<br/>(fixed, semantic, recursive)"]
        end
        
        subgraph Infrastructure4["Infrastructure Layer"]
            DR2["DocumentRepository"]
            CR["ChunkRepository"]
            VS["VectorStore<br/>(pgvector / Qdrant)"]
            EP["EmbeddingProvider<br/>(OpenAI / local)"]
            DP["DocumentParsers<br/>(PDF, DOCX, HTML, MD)"]
            OS["ObjectStore<br/>(S3 / MinIO)"]
            BM["BM25Index<br/>(keyword search)"]
            RRF["RRF Ranker<br/>(fusion)"]
            AV["AntiVirus<br/>(ClamAV)"]
        end
    end

    DR --> IS
    SR2 --> RS2
    KBR --> KBS
    IS --> DE
    IS --> CE
    IS --> CS2
    RS2 --> CIT
    RS2 --> VS
    RS2 --> BM
    RS2 --> RRF
    IS --> DP
    IS --> EP
    IS --> VS
    IS --> OS
    IS --> AV
    ES2 --> RS2
    IS --> DR2
    IS --> CR

    PG4["PostgreSQL"] -.-> DR2
    PG4 -.-> CR
    PGVEC["pgvector"] -.-> VS
    S3["Object Store"] -.-> OS
    EMBAPI["Embedding API"] -.-> EP
```

---

## 6. Voice Service — Components

```mermaid
flowchart TB
    subgraph VoiceService["Voice Service"]
        direction TB
        subgraph Interface5["Interface Layer"]
            VR["Voice Router<br/>/api/v1/voice/*"]
            VWS["WebSocket Handler<br/>/ws/v1/voice/*"]
        end
        
        subgraph Application5["Application Layer"]
            VSS["VoiceSessionService<br/>create, manage sessions"]
            VPP["VoicePipeline<br/>STT → Agent → TTS"]
        end
        
        subgraph Domain5["Domain Layer"]
            SESS["VoiceSession Entity"]
            UTT["Utterance Entity"]
            TRANS["Transcript VO"]
        end
        
        subgraph Infrastructure5["Infrastructure Layer"]
            STT2["STTProvider<br/>(Whisper / Deepgram)"]
            TTS2["TTSProvider<br/>(Coqui / ElevenLabs)"]
            VAD["VADProcessor<br/>(Voice Activity Detection)"]
            SSTORE["SessionStore<br/>(Redis)"]
            ABUF["AudioBuffer<br/>(chunking & encoding)"]
        end
    end

    VR --> VSS
    VWS --> VPP
    VPP --> SESS
    VPP --> UTT
    VPP --> TRANS
    VPP --> STT2
    VPP --> TTS2
    VPP --> VAD
    VSS --> SSTORE
    VPP --> ABUF

    REDIS5["Redis"] -.-> SSTORE
    AGENTSVC["Agent Engine"] -.->|"HTTP"| VPP
```

---

## 7. Multimodal Service — Components

```mermaid
flowchart TB
    subgraph MMService["Multimodal Service"]
        direction TB
        subgraph Interface6["Interface Layer"]
            MMR["Multimodal Router<br/>/api/v1/multimodal/*"]
        end
        
        subgraph Application6["Application Layer"]
            IA["ImageAnalysisService"]
            OCR2["OCRService"]
            VA["VideoAnalysisService"]
            AT["AudioTranscriptionService"]
        end
        
        subgraph Domain6["Domain Layer"]
            MAE["MediaAsset Entity"]
            ARE["AnalysisResult Entity"]
            MT["MediaType Enum"]
        end
        
        subgraph Infrastructure6["Infrastructure Layer"]
            VIS["VisionLLM<br/>(GPT-4o, Gemini, LLaVA)"]
            TESS["TesseractOCR"]
            FFM["FFmpegProcessor<br/>(video frame extraction)"]
            WPER["WhisperTranscriber"]
            OS2["ObjectStore<br/>(media storage)"]
            JQ["JobQueue<br/>(Celery for batch)"]
        end
    end

    MMR --> IA
    MMR --> OCR2
    MMR --> VA
    MMR --> AT
    IA --> MAE
    IA --> ARE
    OCR2 --> MAE
    IA --> VIS
    OCR2 --> TESS
    VA --> FFM
    VA --> VIS
    AT --> WPER
    IA --> OS2
    VA --> JQ

    LLM5["LLM APIs"] -.-> VIS
    S3_5["Object Store"] -.-> OS2
    CELERY["Celery Workers"] -.-> JQ
```

---

## 8. Edge Manager — Components

```mermaid
flowchart TB
    subgraph EdgeManager["Edge Manager"]
        direction TB
        subgraph Interface7["Interface Layer"]
            ER["Edge Router<br/>/api/v1/edge/*"]
            GS["gRPC Server<br/>(model distribution)"]
            MB["MQTT Broker<br/>(telemetry ingestion)"]
        end
        
        subgraph Application7["Application Layer"]
            DS["DeviceService<br/>register, manage, monitor"]
            MSS["ModelSyncService<br/>distribute, version, rollback"]
            TS["TelemetryService<br/>ingest, aggregate, alert"]
        end
        
        subgraph Domain7["Domain Layer"]
            DEV["EdgeDevice Entity"]
            DM["DeployedModel Entity"]
            SS["SyncStatus VO"]
            DC["DeviceCapabilities VO"]
        end
        
        subgraph Infrastructure7["Infrastructure Layer"]
            DR3["DeviceRepository"]
            MR["ModelRepository"]
            MOS["ModelObjectStore<br/>(ONNX files)"]
            MQ["MQTTClient"]
            GC["gRPCService"]
        end
    end

    ER --> DS
    GS --> MSS
    MB --> TS
    DS --> DEV
    MSS --> DM
    MSS --> SS
    DS --> DC
    DS --> DR3
    MSS --> MR
    MSS --> MOS
    TS --> MQ

    PG7["PostgreSQL"] -.-> DR3
    PG7 -.-> MR
    S3_7["Object Store"] -.-> MOS
    EDGE_DEV["Edge Devices"] -.->|"gRPC/MQTT"| GS & MB
```

---

## 9. MLOps Service — Components

```mermaid
flowchart TB
    subgraph MLOpsService["MLOps Service"]
        direction TB
        subgraph Interface8["Interface Layer"]
            MR2["MLOps Router<br/>/api/v1/mlops/*"]
            PM["Prometheus Endpoint<br/>/metrics"]
        end
        
        subgraph Application8["Application Layer"]
            MES["MetricsAggregator<br/>collect, aggregate, expose"]
            CT["CostTracker<br/>per-request, per-agent, per-tenant"]
            DD["DriftDetector<br/>distribution comparison"]
            RE2["RAGASEvaluator<br/>scheduled quality checks"]
        end
        
        subgraph Domain8["Domain Layer"]
            MRE["MetricRecord Entity"]
            CRE["CostRecord Entity"]
            EVE["Evaluation Entity"]
            DRS["DriftScore VO"]
        end
        
        subgraph Infrastructure8["Infrastructure Layer"]
            MR3["MetricsRepository"]
            CRR["CostRepository"]
            PE2["PrometheusExporter"]
            MLF["MLflowClient"]
            RAGAS["RAGASClient"]
            AL["AlertManager<br/>webhook/email dispatch"]
        end
    end

    MR2 --> MES
    MR2 --> CT
    MR2 --> DD
    MR2 --> RE2
    PM --> PE2
    MES --> MRE
    CT --> CRE
    RE2 --> EVE
    DD --> DRS
    MES --> MR3
    CT --> CRR
    MES --> PE2
    RE2 --> MLF
    RE2 --> RAGAS
    DD --> AL

    PG8["PostgreSQL"] -.-> MR3
    PG8 -.-> CRR
    PROM["Prometheus"] -.-> PE2
    MLFLOW["MLflow Server"] -.-> MLF
```

---

## 10. Audit Service — Components

```mermaid
flowchart TB
    subgraph AuditService["Audit Service"]
        direction TB
        subgraph Interface9["Interface Layer"]
            AUR["Audit Router<br/>/api/v1/audit/*"]
            ASC["Audit Event Consumer<br/>(Redis Streams)"]
        end
        
        subgraph Application9["Application Layer"]
            AUS["AuditService<br/>record, query, export"]
            HC["HashChainVerifier<br/>tamper detection"]
        end
        
        subgraph Domain9["Domain Layer"]
            AEE["AuditEvent Entity"]
            AA["AuditAction Enum"]
            AO["AuditOutcome Enum"]
            HCE["HashChainEntry VO"]
        end
        
        subgraph Infrastructure9["Infrastructure Layer"]
            AUR2["AuditRepository<br/>(append-only)"]
            HCS["HashChainStore"]
            AEX["AuditExporter<br/>(CSV, JSON, SIEM)"]
        end
    end

    AUR --> AUS
    ASC --> AUS
    AUS --> AEE
    AUS --> HC
    HC --> HCE
    AUS --> AUR2
    HC --> HCS
    AUS --> AEX

    PG9["PostgreSQL<br/>(append-only table)"] -.-> AUR2
    REDIS9["Redis Streams"] -.-> ASC
```

---

## 11. Frontend — Component Architecture

```mermaid
flowchart TB
    subgraph NextApp["Next.js Application"]
        direction TB
        subgraph Pages["App Router (Pages)"]
            LP["Login Page"]
            DP["Dashboard Page"]
            ABP["Agent Builder Page"]
            REP["RAG Explorer Page"]
            ANP["Analytics Page"]
            SP["Settings Page"]
            ALP["Audit Log Page"]
        end
        
        subgraph Features["Feature Modules"]
            AF["Auth Feature<br/>login, register, SSO"]
            AGF["Agent Feature<br/>builder, executor, monitor"]
            RF["RAG Feature<br/>upload, search, evaluate"]
            VF["Voice Feature<br/>session, controls"]
            ANF["Analytics Feature<br/>charts, cost, usage"]
            SF["Settings Feature<br/>org, team, user, roles"]
        end
        
        subgraph Shared["Shared Layer"]
            API["API Client<br/>(axios + interceptors)"]
            STORE["Zustand Stores<br/>(auth, agents, rag, ui)"]
            HOOKS["Custom Hooks<br/>(useAgent, useRAG, etc.)"]
            UI["UI Components<br/>(Design System)"]
            WS2["WebSocket Client<br/>(agent stream, voice)"]
        end
    end

    LP --> AF
    DP --> ANF
    ABP --> AGF
    REP --> RF
    ANP --> ANF
    SP --> SF
    ALP --> SF

    AF --> API
    AGF --> API
    AGF --> WS2
    RF --> API
    VF --> WS2
    ANF --> API

    AF --> STORE
    AGF --> STORE
    RF --> STORE

    AGF --> UI
    RF --> UI
    ANF --> UI

    BACKEND["Backend API"] -.->|"HTTPS/WSS"| API & WS2
```

---

## 12. Cross-Cutting: Observability Pipeline

```mermaid
flowchart LR
    subgraph Services["All Platform Services"]
        S1["Auth"]
        S2["Agent"]
        S3["RAG"]
        S4["Voice"]
        S5["Others..."]
    end

    subgraph Collection["Collection Layer"]
        OTEL["OpenTelemetry<br/>Collector"]
        FL["Fluentd / Vector<br/>(Log Shipper)"]
        PROM2["Prometheus<br/>(Scrape)"]
    end

    subgraph Storage2["Storage Layer"]
        JAEGER["Jaeger<br/>(Traces)"]
        LOKI["Loki<br/>(Logs)"]
        PROMDB["Prometheus<br/>TSDB (Metrics)"]
        AUDITDB2["Audit Store<br/>(Events)"]
    end

    subgraph Visualization["Visualization Layer"]
        GRAF2["Grafana<br/>(Unified)"]
    end

    subgraph Alerting["Alerting Layer"]
        AM["Alertmanager"]
        PD["PagerDuty"]
        SL["Slack"]
        EMAIL2["Email"]
    end

    S1 & S2 & S3 & S4 & S5 -->|"OTel SDK"| OTEL
    S1 & S2 & S3 & S4 & S5 -->|"Structured JSON"| FL
    S1 & S2 & S3 & S4 & S5 -->|"/metrics"| PROM2

    OTEL --> JAEGER
    FL --> LOKI
    PROM2 --> PROMDB

    JAEGER --> GRAF2
    LOKI --> GRAF2
    PROMDB --> GRAF2
    AUDITDB2 --> GRAF2

    PROMDB --> AM
    AM --> PD & SL & EMAIL2
```

---

*Document Owner: Solutions Architect*  
*Next Review: Upon stakeholder approval of Phase 2*
