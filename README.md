# 🎵 Auralith

### AI-Powered Music Generation & Intelligent Audio Processing Platform

Auralith is a **self-hosted AI music platform** designed to combine conversational AI, Retrieval-Augmented Generation (RAG), asynchronous task processing, music generation, and audio enhancement into a modular microservice-based architecture.

The platform is designed to run primarily with **open-source and locally hosted AI models**, using Ollama for local LLM inference and dedicated services for audio processing.

---

## ✨ Features

* 🤖 **AI-powered conversational interface**
* 🧠 **RAG-based knowledge retrieval**
* 🎼 **AI-assisted music and song generation**
* 💬 Conversational chat with intent detection
* ⚡ **Asynchronous background processing** with Celery
* 🐇 RabbitMQ-based task queue
* 🔴 Redis for caching and Celery support
* 🗄️ PostgreSQL for persistent application data
* 🔎 Qdrant vector database for semantic search
* 🧠 Local LLM inference using Ollama
* 🎧 Audio enhancement using DeepFilterNet
* 🎚️ Audio mastering using Matchering
* 📦 S3-compatible object storage using MinIO
* 🔐 Subscription and token management service
* 🔌 **gRPC-based microservice communication**
* 🐳 Fully containerized development environment using Docker Compose

---

# 🏗️ Architecture

Auralith follows a modular service-oriented architecture.

```text
                           ┌─────────────────────┐
                           │       Client        │
                           │   Web / API Client   │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │      FastAPI        │
                           │        API          │
                           └──────────┬──────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
              ┌──────────┐      ┌──────────┐     ┌───────────┐
              │   RAG    │      │  Ollama  │     │  Celery   │
              │ Pipeline │      │   LLM    │     │  Workers  │
              └────┬─────┘      └──────────┘     └─────┬─────┘
                   │                                    │
                   ▼                                    ▼
              ┌──────────┐                       ┌─────────────┐
              │  Qdrant  │                       │  RabbitMQ   │
              │  Vector  │                       │ Task Queue  │
              │    DB    │                       └─────────────┘
              └──────────┘
                                                        │
                         ┌──────────────────────────────┼────────────────────┐
                         │                              │                    │
                         ▼                              ▼                    ▼
                  ┌────────────┐                ┌────────────┐       ┌────────────┐
                  │ DeepFilter │                │ Matchering │       │    MinIO   │
                  │    Net     │                │   Master   │       │   Storage  │
                  └────────────┘                └────────────┘       └────────────┘

                         ┌──────────────────────────────┐
                         │      Subscription Service    │
                         │         FastAPI + gRPC      │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                                  ┌───────────┐
                                  │ PostgreSQL│
                                  └───────────┘
```

---

# 🧩 Core Services

## API Service

The main application service built with **FastAPI**.

Responsibilities include:

* REST API
* Authentication and application logic
* Chat orchestration
* RAG pipeline orchestration
* Song generation requests
* Job creation
* Audio processing orchestration
* Communication with internal services

Default port:

```text
8000
```

---

## Celery Worker

Auralith uses **Celery** for asynchronous background jobs.

Long-running operations such as:

* Music generation
* Audio enhancement
* Audio processing
* File processing

can be moved away from the request/response cycle.

This prevents expensive operations from blocking API requests.

---

## RabbitMQ

RabbitMQ acts as the **message broker** for Celery.

```text
FastAPI
   │
   ▼
Celery Task
   │
   ▼
RabbitMQ
   │
   ▼
Celery Worker
```

This allows Auralith to process expensive workloads asynchronously.

---

## Redis

Redis is used for:

* Celery backend/supporting infrastructure
* Caching
* Fast temporary data access

Redis persistence is enabled using append-only mode.

---

# 🤖 Local AI with Ollama

Auralith uses **Ollama** to run LLMs locally.

This allows the system to perform AI inference without requiring an external paid LLM API.

```text
User
 │
 ▼
FastAPI
 │
 ▼
Chat Service
 │
 ├── Intent Detection
 │
 ├── RAG Pipeline
 │
 └── Ollama
       │
       ▼
     Local LLM
```

The model can be configured through environment variables.

Example:

```env
OLLAMA_MODEL=your-model-name
```

Before starting Auralith, make sure the configured model is available to Ollama.

---

# 🧠 RAG Pipeline

Auralith includes a Retrieval-Augmented Generation pipeline for providing relevant context to the LLM.

The general flow is:

```text
Documents
   │
   ▼
Chunking
   │
   ▼
Embeddings
   │
   ▼
Qdrant
   │
   ▼
Retriever
   │
   ▼
Relevant Context
   │
   ▼
Ollama
   │
   ▼
Generated Response
```

The RAG system is organized around components such as:

```text
backend/app/services/rag/

├── chunker.py
├── embeddings.py
├── indexer.py
├── pipeline.py
├── retriever.py
└── vector_store.py
```

This separation allows individual components of the retrieval pipeline to evolve independently.

---

# 🎵 Music Generation

Auralith is designed to accept music-related requests through a conversational interface.

A typical flow is:

```text
User
 │
 ▼
Chat API
 │
 ▼
Intent Detection
 │
 ▼
Music Generation Job
 │
 ▼
Celery
 │
 ▼
Music Processing
 │
 ▼
Audio Files
 │
 ▼
MinIO
 │
 ▼
Download / Playback
```

The system is designed around asynchronous jobs because music generation and audio processing can be computationally expensive.

---

# 🎧 Audio Processing

Auralith separates audio processing into dedicated services.

## DeepFilterNet

DeepFilterNet is used for audio enhancement/noise reduction.

The architecture avoids sending large audio files directly through gRPC.

Instead:

```text
Backend
   │
   │ Upload audio
   ▼
 MinIO
   │
   │ Object key
   ▼
Audio Job
   │
   ▼
Celery Worker
   │
   ▼
DeepFilterNet
   │
   │ Download input
   ▼
Enhanced Audio
   │
   ▼
MinIO
```

This keeps gRPC communication lightweight and avoids transferring large audio payloads through service-to-service RPC calls.

DeepFilterNet exposes:

```text
HTTP: 8001
gRPC: 50053
```

---

## Matchering

Matchering is used for audio mastering/reference-based processing.

The service works with separate directories for:

```text
input/
reference/
output/
temp/
```

The service exposes:

```text
HTTP: 8003
```

A health endpoint is also configured for Docker health monitoring.

---

# 💾 Storage Architecture

Auralith uses **MinIO** as S3-compatible object storage.

Audio and generated files are stored as objects rather than keeping large binary files inside PostgreSQL.

```text
                  ┌───────────────┐
                  │   FastAPI     │
                  └───────┬───────┘
                          │
                          ▼
                     ┌─────────┐
                     │  MinIO  │
                     └────┬────┘
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
           Audio        MIDI         Other
           Files        Files        Assets
```

MinIO provides:

* S3-compatible object storage
* Persistent Docker volume
* Separate storage from application database
* Internal service-to-service access

The MinIO API runs on:

```text
9000
```

The MinIO console runs on:

```text
9001
```

---

# 🔎 Vector Database

Auralith uses **Qdrant** for vector storage and semantic retrieval.

Qdrant stores embeddings generated by the RAG pipeline.

```text
Text
 │
 ▼
Embedding Model
 │
 ▼
Vector
 │
 ▼
Qdrant
```

Qdrant runs on:

```text
6333
```

---

# 💳 Subscription Service

Auralith includes a dedicated subscription microservice.

The service is responsible for subscription-related functionality such as:

* Subscription plans
* Subscription durations
* Token-based usage
* Token wallets
* Token transactions
* User subscriptions

The service exposes:

```text
HTTP: 8002
gRPC: 50052
```

The application is designed so that subscription functionality can evolve independently from the main API.

---

# 🔌 gRPC Communication

Auralith uses **gRPC** for internal service communication where appropriate.

The architecture uses protocol buffer contracts shared between services.

```text
                 contracts/
                     │
                     ▼
             ┌───────────────┐
             │ .proto files  │
             └───────┬───────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
       Subscription     Audio Service
          Service
```

gRPC is particularly useful for internal communication because it provides:

* Strongly typed contracts
* Efficient binary serialization
* Generated client/server code
* Clear service boundaries

---

# 🗄️ Database

Auralith uses **PostgreSQL** as its primary relational database.

The database stores application-level information such as:

* Users
* Conversations
* Messages
* Songs
* Song files
* Generation jobs
* Audio jobs
* Subscriptions
* Token wallets
* Token transactions

PostgreSQL runs on:

```text
5432
```

Database migrations are managed using **Alembic**.

---

# 🐳 Docker Architecture

Auralith is designed to run as a multi-container application using Docker Compose.

Main services:

```text
api
celery
postgres
redis
rabbitmq
ollama
qdrant
minio
minio-init
deepfilternet
matchering
subscription
```

All services communicate through the Docker bridge network:

```text
backend-network
```

Persistent data is stored using Docker volumes.

---

# 📁 Project Structure

A simplified project structure:

```text
auralith/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   └── rag/
│   │   ├── tasks/
│   │   └── workers/
│   │
│   └── alembic/
│
├── contracts/
│   └── *.proto
│
├── deepfilternet/
│
├── services/
│   └── matchering/
│
├── subscription/
│   ├── app/
│   └── generated/
│
├── docker/
│   ├── api.Dockerfile
│   ├── deepf.Dockerfile
│   ├── matchering.Dockerfile
│   └── subscription.Dockerfile
│
├── storage/
│
├── docker-compose.yml
│
├── .env.example
│
└── README.md
```

---

# ⚙️ Requirements

Before running Auralith, install:

* Docker
* Docker Compose
* Git

For local AI inference:

* Ollama-compatible environment
* A model supported by your hardware

Recommended system resources depend heavily on the LLM and audio models being used.

---

# 🚀 Getting Started

## 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/auralith.git

cd auralith
```

---

## 2. Configure environment variables

Create your environment file:

```bash
cp .env.example .env
```

Configure the required values.

For example:

```env
POSTGRES_DB=auralith
POSTGRES_USER=auralith
POSTGRES_PASSWORD=your-password

REDIS_PORT=6379

RABBITMQ_DEFAULT_USER=auralith
RABBITMQ_DEFAULT_PASS=your-password

OLLAMA_PORT=11434

QDRANT_PORT=6333

MINIO_ROOT_USER=auralith
MINIO_ROOT_PASSWORD=your-password
MINIO_BUCKET=auralith
```

Do **not** commit real credentials to Git.

---

# ▶️ Start the Platform

Build and start the services:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up -d --build
```

Check running containers:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f api
```

View Celery logs:

```bash
docker compose logs -f celery
```

---

# 🧠 Configure Ollama

After starting the Ollama container, pull the model configured for Auralith.

Example:

```bash
docker exec -it auralith-ollama ollama pull <model-name>
```

Verify installed models:

```bash
docker exec -it auralith-ollama ollama list
```

The exact model should be configured according to the hardware available.

---

# 🔗 Service Endpoints

| Service             |    Port | Purpose              |
| ------------------- | ------: | -------------------- |
| FastAPI             |  `8000` | Main API             |
| Subscription API    |  `8002` | Subscription service |
| Subscription gRPC   | `50052` | Internal RPC         |
| DeepFilterNet HTTP  |  `8001` | Audio enhancement    |
| DeepFilterNet gRPC  | `50053` | Internal RPC         |
| Matchering          |  `8003` | Audio mastering      |
| RabbitMQ            |  `5672` | Message broker       |
| RabbitMQ Management | `15672` | RabbitMQ dashboard   |
| Redis               |  `6379` | Cache/task backend   |
| PostgreSQL          |  `5432` | Relational database  |
| Ollama              | `11434` | Local LLM inference  |
| Qdrant              |  `6333` | Vector database      |
| MinIO API           |  `9000` | Object storage       |
| MinIO Console       |  `9001` | Storage dashboard    |

---

# 🔄 Example Asynchronous Workflow

An audio-processing request can follow this architecture:

```text
Client
  │
  ▼
FastAPI
  │
  ├── Create AudioJob
  │
  ├── Upload input → MinIO
  │
  └── Queue task → RabbitMQ
                       │
                       ▼
                 Celery Worker
                       │
                       ▼
                 DeepFilterNet
                       │
                       ├── Download from MinIO
                       │
                       ├── Process audio
                       │
                       └── Upload result
                              │
                              ▼
                            MinIO
                              │
                              ▼
                         AudioJob
                          COMPLETED
```

This architecture keeps expensive processing out of the synchronous API request.

---

# 🧪 Testing

Run backend tests using the project's configured test environment.

Example:

```bash
pytest
```

For a specific backend test suite:

```bash
pytest -q backend
```

---

# 🔐 Security Notes

For production deployment:

* Never commit `.env` files
* Use strong PostgreSQL credentials
* Use strong MinIO credentials
* Restrict exposed service ports
* Put public APIs behind HTTPS
* Configure authentication and authorization
* Use secrets management instead of plain environment variables
* Restrict internal gRPC services to the private network
* Configure resource limits for AI/audio workloads
* Enable proper logging and monitoring

The Docker Compose configuration is primarily intended as a development/self-hosted environment and should be hardened before production deployment.

---

# 🛣️ Roadmap

Potential future improvements include:

* [ ] Production authentication and authorization
* [ ] Improved AI music generation pipeline
* [ ] Streaming audio generation
* [ ] Advanced RAG evaluation
* [ ] Distributed task monitoring
* [ ] Prometheus metrics
* [ ] OpenTelemetry distributed tracing
* [ ] Production Kubernetes deployment
* [ ] GPU-aware scheduling
* [ ] Improved audio generation models
* [ ] Automated CI/CD pipeline
* [ ] API rate limiting
* [ ] Advanced subscription/token enforcement
* [ ] Better observability across microservices

---

# 🎯 Engineering Goals

Auralith is built around several engineering principles:

### Modular Architecture

Each major responsibility is isolated into a dedicated service.

### Asynchronous Processing

Long-running AI and audio workloads are handled through background workers instead of blocking API requests.

### Local AI

The platform can use locally hosted models through Ollama, reducing dependence on external AI APIs.

### Object-Based Audio Storage

Large audio assets are stored in MinIO rather than directly inside PostgreSQL.

### Strong Service Contracts

gRPC and Protocol Buffers provide typed contracts between internal services.

### Scalable Components

Services such as workers, audio processors, and the API can be scaled independently.

---

# 🧰 Technology Stack

### Backend

* Python
* FastAPI
* SQLAlchemy
* Alembic
* Celery

### AI

* Ollama
* Local LLMs
* RAG
* Embeddings
* Qdrant

### Distributed Systems

* RabbitMQ
* Redis
* Celery
* gRPC
* Protocol Buffers

### Database & Storage

* PostgreSQL
* MinIO

### Audio

* DeepFilterNet
* Matchering
* FFmpeg
* MIDI/audio processing tools

### Infrastructure

* Docker
* Docker Compose

---

# 📜 License

Add your project license here.

For example:

```text
MIT License
```

---

# 👨‍💻 Author

**Sanchar Panthi**

Backend / AI Engineer

Interested in:

* Backend Engineering
* Distributed Systems
* AI/LLM Applications
* RAG Systems
* Microservices
* Real-Time Systems
* Audio/AI Infrastructure

---

## ⭐ Why Auralith?

Auralith is not simply an AI chatbot.

It is an attempt to build a complete AI-powered media platform combining:

```text
AI
+
RAG
+
LLMs
+
Microservices
+
Async Processing
+
gRPC
+
Vector Search
+
Object Storage
+
Audio Processing
+
Subscriptions
```

The goal is to explore how modern AI applications can be designed as **scalable, modular backend systems** rather than as a single monolithic application.
