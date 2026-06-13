# Enterprise AI Operations Center — API Specification

## 1. Authentication & RBAC

All endpoints require a valid JWT token passed in the `Authorization: Bearer <token>` header, except for public endpoints like `/health` and `/docs`.
The JWT token must contain the user's `roles` and `sensitivity_clearance`.

*   **Rate Limiting:** 100 requests per minute per user (sliding window).
*   **Response Headers:** Every response includes `X-Request-ID` and `X-Response-Time-Ms`.

---

## 2. API Gateway Endpoints

Base URL: `http://localhost:8000/api/v1`

### 2.1 Agent Orchestration (`/agents`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/issues/review` | Triggers the agent pipeline to analyze a codebase issue. | Admin, Engineer, Analyst |
| `GET` | `/workflows/{exec_id}` | Gets the status and logs of a running workflow execution. | Admin, Engineer, Analyst |

### 2.2 Knowledge Base / RAG (`/rag`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/rag/query` | Submits a query to the hybrid RAG engine. RBAC filters are applied automatically based on JWT. | All |
| `POST` | `/rag/ingest` | Uploads a document (PDF/TXT/MD) for chunking and vector storage. | Admin |
| `GET` | `/rag/documents` | Lists all indexed documents. | All |

### 2.3 Multimodal Analysis (`/multimodal`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/multimodal/analyze` | Uploads a file (PDF/Image) for parsing or vision model analysis. | Admin, Engineer, Analyst |
| `POST` | `/multimodal/analyze/url` | Submits a URL for multimodal analysis. | Admin, Engineer, Analyst |

### 2.4 Voice Agent (`/voice`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/voice/session` | Starts or continues a text-based turn in a voice session. | Admin, Support, Analyst |
| `POST` | `/voice/session/audio` | Submits audio for STT → Intent → LLM → TTS pipeline processing. | Admin, Support, Analyst |
| `WS` | `/voice/stream` | WebSocket endpoint for real-time bidirectional audio streaming. | Admin, Support |

### 2.5 Edge Devices & LLMs (`/edge`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/edge/models` | Lists available GGUF quantized models deployed on edge nodes. | Admin, Engineer |
| `GET` | `/edge/nodes` | Returns telemetrics (RAM, TPS, uptime) of connected edge devices. | Admin, Engineer |

---

## 3. Example Workflows

### Scenario 1: Submitting a RAG Query

**Request:**
```http
POST /api/v1/rag/query
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "query": "What is the RBAC policy for medical records?",
  "top_k": 5,
  "rerank": true
}
```

**Response (200 OK):**
```json
{
  "data": {
    "query_id": "782b-4b2a",
    "answer": "Medical records require the 'medical' role clearance...",
    "sources": [
      { "doc_id": "doc-003", "score": 0.923 }
    ],
    "citations": [
      { "claim": "Medical role required", "source_doc": "doc-003" }
    ],
    "rbac_applied": true,
    "latency_ms": 310
  }
}
```
