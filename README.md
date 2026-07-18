# Beubble 2.0 - Multi-Agent System

Beubble 2.0 is an advanced multi-agent application designed to orchestrate automated complex tasks through a FastAPI backend, an integrated static frontend, and several specialized sub-agents for web navigation, terminal execution, API interaction, and vector-based memory management.

---

## Alibaba Cloud Deployment Proof

To meet the official hackathon regulations, the complete multi-agent backend and frontend bundle is fully containerized and currently running live on an Alibaba Cloud ECS (Elastic Compute Service) Instance.

* Deployment File: Standardized through the production [backend/Dockerfile](./backend/Dockerfile).
* Live API & Web Endpoint: http://<YOUR_ECS_PUBLIC_IP>:8000/ (Replace with the real ECS Public IP)
* Infrastructure & Security Details:
  * Compute: Alibaba Cloud ECS Instance (Ubuntu Linux).
  * AI Orchestration: Backend hosted on ECS making native, secure API calls to Qwen Cloud (DashScope) via https://aliyuncs.com.
  * Zero-Leak Security: Secrets are securely injected inside the live cloud container at runtime via Docker environment flags. Credentials never touch the public GitHub repository.

---

## 1. Overview

This project seamlessly combines:
- A Python backend powered by FastAPI to expose REST and WebSocket APIs,
- An integrated static user interface built with HTML/CSS/JavaScript served directly by the backend,
- A central orchestrator called MotherAgent,
- Multiple sub-agents specializing in browser automation, API calls, and terminal operations,
- A multi-layered memory architecture and an optional long-term vector memory powered by Qdrant.

---

## 2. Multi-Agent Architecture

### 2.1 Backend Server
The backend entry point is located in `backend/main.py`. It initializes the FastAPI application, manages WebSocket routes, authentication sessions, and loads the active agent orchestration matrix.

### 2.2 The Core: MotherAgent
Located in `backend/core/mother.py`, the MotherAgent acts as the supreme orchestrator of the system. Instead of processing low-level commands monolithically, it breaks down human intentions into a structured action plan and delegates precise sub-tasks to specialized sub-agents.

#### Why this architecture matters
This approach moves the system from a single monolithic agent to a true multi-agent organization. Instead of one component trying to do everything, Beubble distributes tasks according to the nature of the request:
- Web searches for fresh contextual information,
- API calls for structured and real-time data,
- Terminal executions for file mutations and scripting tasks,
- Shared memory for state continuity across complex interactions.

#### Innovation brought by this design
The main innovation of this architecture is the unified combination of parallelized asynchronous workers overseen by an autonomous controller. Data from various sources is instantly fused into an active working memory context. This allows Beubble to tackle multi-step logic without requiring human intervention at every stage.

### 2.3 Specialized Sub-Agents
Located in `backend/sub_agent/`:
- `api_agent.py`: Executes and interprets external API calls.
- `navigator.py`: Drives autonomous web-scavenging workflows.
- `terminal_agent.py`: Safe evaluation and execution of system shell commands.

### 2.4 Resource Drivers
Located in `backend/driver/`:
- `browser_driver.py`: Browser automation via Playwright and Playwright-Stealth.
- `api_driver.py`: High-performance asynchronous HTTP network calling.
- `terminal_driver.py`: Subprocess shell execution interface.
- `file_driver.py`: Safe workspace file manipulation.

### 2.5 Advanced Memory Architecture & Synchronization Matrix
Located in `backend/memory/`, the system implements a sophisticated three-layer memory infrastructure. This layered approach ensures that context is preserved, shared, and retrieved efficiently across all operational scopes without causing data-stale states.

#### The Three Memory Layers:
1. Session Memory (Short-Term Context & Data Transport): Manages the immediate conversation log between the user and the system. Crucially, it acts as the data highway that transports state variables between threads, allowing concurrent or sequential sub-agents to securely swap execution payloads.
2. Working Memory (Agent Collaboration Space): Acts as a dynamic, non-persistent whiteboard shared across active agents and heavily utilized by the Terminal Agent. This layout allows the terminal worker to execute system scripts with higher fluidity, providing immediate step-by-step action visibility and operational recall across multi-stage commands. It prevents data duplication and keeps concurrent operations synchronized.
3. Long-Term Memory (Vector-Based Storage): Powered natively by Qdrant Vector Database, this layer handles persistent knowledge retrieval. Important summaries, past execution patterns, and structural insights are vectorized via Jina AI Embeddings and stored securely. This enables semantic search across past sessions, avoiding a fresh start at every interaction.


#### Dual Execution Paradigms:
* Parallel Execution Flow: When the user prompt requires multiple independent investigations (e.g., scraping a web page via the Navigator while pulling data from an API endpoint), workers are spawned concurrently. Sub-agents read from the shared Working Memory at the same time to gain instant context, performing non-blocking executions to maximize operational throughput.
* Sequential Dependency Flow: When a sub-task directly depends on the outcome of another (e.g., the Terminal Agent needs a file setup that must first be extracted by the Navigator), execution switches to a deterministic sequence. The first agent commits its structural findings directly into the shared state. The subsequent agent instantly inherits this freshly updated context from Session & Working Memory, preventing execution drift.

### 2.6 Frontend Layer
Located in `frontend/public/`. The FastAPI backend natively exposes these static web assets, removing any requirement for external Node.js hosting infrastructure during deployment.

---

## 3. Project Directory Structure

```text
your-github-repo/
├── backend/                  # Deployed cloud application root
│   ├── AI_models/
│   ├── core/                 # Main MotherAgent logic
│   ├── database/
│   ├── driver/
│   ├── logs/
│   ├── memory/               # Memory modules
│   ├── sub_agent/            # Specialized sub-agent directory
│   ├── workspace/
│   ├── .env.example          # SECURE TEMPLATE (Visible on GitHub)
│   ├── Dockerfile            # Container build instructions
│   ├── main.py               # Application entry point
│   └── requirements.txt      # Python dependencies
├── frontend/
│   └── public/               # UI Static files served by the backend
├── .gitignore                # Secret safety file
└── README.md                 # Main Documentation page
```

---

## 4. Environment Configuration

The application requires several environment variables to operate (including server settings and external API keys for Qwen/DashScope, Brave Search, and Jina AI).

To configure the environment:
1. Locate the secure template file at `backend/.env.example`.
2. Create a private `.env` file inside the local or ECS `backend/` directory.
3. Copy the variables from the template and fill in the actual private credentials.

*Note: The real `.env` file is strictly protected by the `.gitignore` policy and will never be pushed to GitHub.*

---

## 5. Deployment Setup (Alibaba Cloud ECS)

To compile the production container and fire up the system on the active Alibaba Cloud virtual server, follow these terminal steps:

### 1. Connect to the ECS and navigate to the project
```bash
git clone https://github.com
cd YOUR_REPOSITORY/backend
```

### 2. Configure production variables
Create the actual, secure production `.env` file right inside the `backend/` folder:
```bash
nano .env
# Paste the actual keys, then Save (Ctrl+O) and Exit (Ctrl+X)
```

### 3. Build the Docker Image
```bash
docker build -t beubble-app .
```

### 4. Run the Container on Alibaba Cloud
```bash
docker run -d -p 8000:8000 --env-file .env --name beubble-backend beubble-app
```
*Note: Ensure the Alibaba Cloud Security Group allows Inbound traffic on Port 8000.*
