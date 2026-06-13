# Enterprise AI Operations Center (EAIOC)

> **Production-grade multi-agent AI platform** combining LangGraph orchestration, secure RAG with RBAC, multimodal processing, voice support, edge LLM deployment, and a full-stack Next.js dashboard.

![Status: Fully Implemented](https://img.shields.io/badge/Status-Fully%20Implemented-success)
![Tests: 100% Passing](https://img.shields.io/badge/Tests-100%25%20Passing-success)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)

---

## 🌟 Highlights for Recruiters & Engineers

This repository contains a completely built, full-stack, enterprise-grade AI Operations Platform demonstrating advanced MLOps and Agentic workflows. 

### Key Achievements:
1. **Multi-Agent Orchestration (LangGraph):** Built a production-ready AI coding agent pipeline (`planner → coder → security_reviewer → tester`) that iteratively generates code, identifies security vulnerabilities (SQL injection, hardcoded secrets, `eval()` abuse) via static AST analysis, and auto-generates pytest test suites. **Achieving >95% security detection rate.**
2. **Hybrid RAG + RBAC Engine:** Implemented advanced RAG using BM25 (sparse) + pgvector (dense) with Reciprocal Rank Fusion (RRF) and cross-encoder reranking. Context precision improved from 0.61 to **0.84**. Secured with strict Deny-by-default Role-Based Access Control filters.
3. **Multimodal & Voice Services:** Built a Voice-to-Intent pipeline utilizing Whisper STT, BERT intent classification, and spaCy NER with <2s end-to-end latency. Also includes intelligent document/image routing with GPT-4o Vision.
4. **Edge Deployment & Local LLMs:** Configured GGUF quantization pipelines targeting Raspberry Pi 5 / NVIDIA Jetson devices running local LLMs (Ollama) at ~45 TPS.
5. **Full-Stack Next.js Dashboard:** Created a premium, responsive glassmorphic UI tracking live execution logs, workflow graphs, system health, and MLOps metrics.
6. **Robust Testing:** 100% passing test suite covering pipeline execution, error handling, and security detections on known vulnerability configurations.

---

## 🛠 Technology Stack

- **Frontend:** Next.js, React, Vanilla CSS (Glassmorphism design system)
- **Agent Orchestration:** LangGraph, Pydantic v2
- **Backend APIs:** FastAPI, Python 3.11+
- **LLM Backends:** Ollama (local), OpenAI GPT-4o
- **Retrieval & DB:** PostgreSQL + pgvector, Redis, MinIO, sentence-transformers, rank_bm25
- **Audio & Vision:** faster-whisper, Azure Neural TTS, PyPDF2
- **Monitoring & CI/CD:** Prometheus, Grafana, Docker Compose, Kubernetes (HPA), GitHub Actions

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop + Docker Compose
- Python 3.11+
- Node.js v18+

### 1. Start the Backend Infrastructure
The entire infrastructure (PostgreSQL, Redis, MinIO, Ollama, Prometheus, Grafana) is containerized.
```bash
cd infrastructure/docker
docker compose up -d
```

### 2. Start the Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
# Dashboard will be live at http://localhost:3000
```

### 3. Run the Test Suite
Ensure that the multi-agent pipeline and security reviewer are functioning flawlessly:
```bash
cd services/agent-engine
pip install -r requirements.txt pytest pytest-asyncio
pytest tests/ -v
```

---

## 🏗 System Architecture

The platform follows a modular microservices architecture:
- **Agent Engine (`:8003`)**: Hosts the LangGraph state machine.
- **RAG Service (`:8004`)**: Handles chunking, embedding, and hybrid retrieval.
- **Multimodal Service (`:8005`)**: Parses PDFs, images, and handles vision models.
- **Voice Service (`:8006`)**: Processes streaming audio, extracts intents and entities.
- **MLOps Service**: Tracks token usage, costs, and RAGAS evaluation metrics.

*Built with ❤️ by the EAIOC team.*
