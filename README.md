# Nexus HR Agent

An AI-powered internal operations assistant built with AWS Bedrock, RAG, and FastAPI. Ask questions about company documentation or create support tickets — the agent routes your request to the right skill automatically.

## Architecture

- **Frontend:** Next.js 14 + TypeScript + Tailwind
- **Backend:** FastAPI + Python
- **LLM:** AWS Bedrock (Claude Sonnet)
- **Embeddings:** AWS Bedrock (Amazon Titan)
- **Vector Store:** ChromaDB
- **Session Storage:** Local file-based JSON

## Features

- RAG pipeline over fictional company documentation (Nexus HR)
- Tool calling — `search_docs` and `create_ticket`
- Intent-based skill routing (documentation vs support)
- Stateful multi-turn conversations with session persistence
- Conversation summarization for long sessions
- LLM-as-judge evaluation pipeline

## Prerequisites

- Python 3.11+
- Node.js 22.13+
- AWS account with Bedrock access enabled for Claude Sonnet and Amazon Titan models

## Setup

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd nexus-hr-agent
```

### 2. Set up Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_session_token
AWS_REGION=us-east-1
MODEL_ID=us.anthropic.claude-sonnet-4-5-20251001-v1:0
AWS_CA_BUNDLE=/path/to/.venv/lib/python3.11/site-packages/certifi/cacert.pem
```

To find your certifi path run:
```bash
python -c "import certifi; print(certifi.where())"
```

### 4. Ingest documents

```bash
python -m rag.ingest
```

### 5. Start the backend

```bash
uvicorn backend.api.main:app --reload --port 8001
```

### 6. Start the frontend

```bash
cd frontend
yarn install
yarn dev
```

Open [http://localhost:3000](http://localhost:3000)

## Running Evaluations

```bash
python -m evals.run_evals
```

Runs the golden dataset against the agent and scores each response using an LLM judge.

## Project Structure

```
nexus-hr-agent/
├── backend/
│   ├── api/
│   │   └── main.py          # FastAPI endpoints
│   └── session_store.py     # File-based session persistence
├── rag/
│   ├── agent.py             # Bedrock agent with tool calling
│   ├── ingest.py            # Document chunking and embedding
│   ├── query.py             # Vector search
│   ├── skills.py            # Intent-based skill routing
│   ├── summarizer.py        # Conversation summarization
│   └── tools.py             # Tool implementations
├── evals/
│   ├── golden_dataset.json  # Evaluation questions and expected answers
│   └── run_evals.py         # Evaluation pipeline
├── docs/                    # Company documentation (markdown)
├── frontend/                # Next.js chat UI
└── sessions/                # Session files (gitignored)
```
