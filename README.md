# Beubble 2.0 - Multi-Agent System

Beubble 2.0 is an advanced multi-agent application designed to orchestrate automated complex tasks through a FastAPI backend, an integrated static frontend, and several specialized sub-agents for web navigation, terminal execution, API interaction, and vector-based memory management.

---

*Find demo result here: [https://github.com/jen21-sudo/beubble-2.0/tree/master/backend/Ai_result_video_demo](https://github.com/jen21-sudo/beubble-2.0/tree/master/backend/Ai_result_video_demo)*

---

## 1. Overview

This project seamlessly combines:
- A Python backend powered by FastAPI to expose REST and WebSocket APIs
- An integrated static user interface built with HTML/CSS/JavaScript served directly by the backend
- A central orchestrator called MotherAgent
- Multiple sub-agents specializing in browser automation, API calls, and terminal operations
- A multi-layered memory architecture with optional long-term vector memory powered by Qdrant
- **Interface Mode**: Optional no-authentication mode for development and demonstrations
- **Cookie-based Authentication**: Secure session management for production deployments

---

## 2. Multi-Agent Architecture

### 2.1 Backend Server
The backend entry point is located in `backend/server.py`. It initializes the FastAPI application, manages WebSocket routes, authentication sessions, and loads the active agent orchestration matrix. The server supports both REST API endpoints and real-time WebSocket communication for streaming logs and agent responses.

### 2.2 Authentication System
Beubble 2.0 features a flexible dual-mode authentication system:

- **Interface Mode** (`INTERFACE_MODE=True`): Allows access without API key authentication - ideal for development and demonstrations
- **Secure Mode** (`INTERFACE_MODE=False`): Requires API key or session cookie authentication for all endpoints

The authentication system supports:
- API key validation via `X-API-Key` header
- Session-based authentication via secure cookies
- WebSocket authentication via query parameters

### 2.3 The Core: MotherAgent
Located in `backend/core/mother.py`, the MotherAgent acts as the supreme orchestrator of the system. Instead of processing low-level commands monolithically, it breaks down human intentions into a structured action plan and delegates precise sub-tasks to specialized sub-agents.

#### Why this architecture matters
This approach moves the system from a single monolithic agent to a true multi-agent organization. Instead of one component trying to do everything, Beubble distributes tasks according to the nature of the request:
- Web searches for fresh contextual information
- API calls for structured and real-time data
- Terminal executions for file mutations and scripting tasks
- Shared memory for state continuity across complex interactions

#### Innovation brought by this design
The main innovation of this architecture is the unified combination of parallelized asynchronous workers overseen by an autonomous controller. Data from various sources is instantly fused into an active working memory context. This allows Beubble to tackle multi-step logic without requiring human intervention at every stage.

### 2.4 Specialized Sub-Agents
Located in `backend/sub_agent/`:
- `api_agent.py`: Executes and interprets external API calls
- `navigator.py`: Drives autonomous web-scavenging workflows
- `terminal_agent.py`: Safe evaluation and execution of system shell commands

### 2.5 Resource Drivers
Located in `backend/driver/`:
- `browser_driver.py`: Browser automation via Playwright and Playwright-Stealth
- `api_driver.py`: High-performance asynchronous HTTP network calling
- `terminal_driver.py`: Subprocess shell execution interface
- `file_driver.py`: Safe workspace file manipulation

### 2.6 Advanced Memory Architecture & Synchronization Matrix
Located in `backend/memory/`, the system implements a sophisticated three-layer memory infrastructure. This layered approach ensures that context is preserved, shared, and retrieved efficiently across all operational scopes without causing data-stale states.

#### The Three Memory Layers:
1. **Session Memory (Short-Term Context & Data Transport)**: Manages the immediate conversation log between the user and the system. Crucially, it acts as the data highway that transports state variables between threads, allowing concurrent or sequential sub-agents to securely swap execution payloads.

2. **Working Memory (Agent Collaboration Space)**: Acts as a dynamic, non-persistent whiteboard shared across active agents and heavily utilized by the Terminal Agent. This layout allows the terminal worker to execute system scripts with higher fluidity, providing immediate step-by-step action visibility and operational recall across multi-stage commands. It prevents data duplication and keeps concurrent operations synchronized.

3. **Long-Term Memory (Vector-Based Storage)**: Powered natively by Qdrant Vector Database, this layer handles persistent knowledge retrieval. Important summaries, past execution patterns, and structural insights are vectorized via Jina AI Embeddings and stored securely. This enables semantic search across past sessions, avoiding a fresh start at every interaction.

#### Dual Execution Paradigms:
- **Parallel Execution Flow**: When the user prompt requires multiple independent investigations (e.g., scraping a web page via the Navigator while pulling data from an API endpoint), workers are spawned concurrently. Sub-agents read from the shared Working Memory at the same time to gain instant context, performing non-blocking executions to maximize operational throughput.

- **Sequential Dependency Flow**: When a sub-task directly depends on the outcome of another (e.g., the Terminal Agent needs a file setup that must first be extracted by the Navigator), execution switches to a deterministic sequence. The first agent commits its structural findings directly into the shared state. The subsequent agent instantly inherits this freshly updated context from Session & Working Memory, preventing execution drift.

### 2.7 Frontend Layer
Located in `frontend/public/`. The FastAPI backend natively exposes these static web assets, removing any requirement for external Node.js hosting infrastructure during deployment. The frontend communicates with the backend via both REST API calls and WebSocket connections for real-time updates.

---

## 3. Project Directory Structure

```text
your-github-repo/
├── backend/                  # Application root
│   ├── AI_models/           # AI model configurations
│   ├── core/                # Main MotherAgent logic
│   ├── database/            # Database files
│   ├── driver/              # Resource drivers (browser, API, terminal, file)
│   ├── logs/                # Application logs
│   ├── memory/              # Memory modules (session, working, long-term)
│   ├── sub_agent/           # Specialized sub-agents
│   ├── workspace/           # User workspace for file operations
│   ├── .env.example         # Environment template (visible on GitHub)
│   ├── config.py            # Configuration management
│   ├── auth.py              # Authentication and session management
│   ├── Dockerfile           # Container build instructions
│   ├── server.py            # Application entry point
│   └── requirements.txt     # Python dependencies
├── frontend/
│   └── public/              # UI Static files served by the backend
├── .gitignore               # Secret safety file
└── README.md                # Main documentation page
```

---

## 4. Environment Configuration

The application requires several environment variables to operate, including server settings and external API keys for Qwen/DashScope, Brave Search, and Jina AI.

### Required API Keys:
- **DASHSCOPE_API_KEY**: For Qwen model access (required)
- **BRAVE_SEARCH_API_KEY**: For web search capabilities (optional but recommended)
- **JINA_API_KEY**: For embeddings and RAG capabilities (optional)

### Configuration Steps:
1. Locate the secure template file at `backend/.env.example`
2. Create a private `.env` file inside the `backend/` directory
3. Copy the variables from the template and fill in the actual private credentials

```bash
cd backend
cp .env.example .env
nano .env  # Add your actual API keys
```

**Important**: The real `.env` file is strictly protected by the `.gitignore` policy and will never be pushed to GitHub.

### Interface Mode Configuration
The `INTERFACE_MODE` flag in `backend/config.py` controls authentication requirements:

```python
# In config.py
INTERFACE_MODE = True   # No API key required (development/demo)
INTERFACE_MODE = False  # API key required (production)
```

---

## 5. Installation & Running Instructions

### 5.1 Prerequisites
- Docker and Docker Compose
- Python 3.9+ (for local development)
- Playwright browsers (automatically installed via Docker)

### 5.2 Local Development Setup

To run Beubble 2.0 locally for development and testing:

#### Step 1: Clone the repository
```bash
git clone https://github.com/jen21-sudo/beubble-2.0.git
cd beubble-2.0
```

#### Step 2: Configure environment variables
```bash
cd backend
cp .env.example .env
nano .env  # Add your actual API keys
```

#### Step 3: Build the Docker image
```bash
# Clean build (recommended to avoid cache issues)
sudo DOCKER_BUILDKIT=0 docker build -t beubble-app .
```

#### Step 4: Run the container
```bash
docker run -d -p 8000:8000 --env-file .env --name beubble-backend beubble-app
```

#### Step 5: View logs (monitor application startup)
```bash
docker logs -f beubble-backend
```

#### Step 6: Access the application
Open your browser: **http://localhost:8000**

### 5.3 Local Development (Without Docker)

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Install Playwright browsers
playwright install

# Run the server
cd backend
python server.py
```

---

## 6. API Documentation

Once the server is running, API documentation is available at:
- **Swagger UI**: http://localhost:8000/api/docs (when DEBUG=True)
- **ReDoc**: http://localhost:8000/api/redoc (when DEBUG=True)

### Key Endpoints:

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/health` | GET | Health check with system status | Optional |
| `/api/chat` | POST | Send a prompt to the MotherAgent | Required (unless Interface Mode) |
| `/api/auth/login` | POST | Login and set session cookie | Public |
| `/api/auth/logout` | POST | Logout and clear session | Public |
| `/api/auth/status` | GET | Check authentication status | Public |
| `/api/sessions` | GET | List all sessions | Required |
| `/api/session/current` | GET | Get current session info | Required |
| `/api/workspace` | GET | Get workspace file tree | Required |
| `/api/workspace/upload` | POST | Upload file to workspace | Required |
| `/ws/agent` | WebSocket | Real-time agent communication | Required (unless Interface Mode) |

### WebSocket Connection
```javascript
// Connect with API key
const ws = new WebSocket('ws://localhost:8000/ws/agent?api_key=YOUR_API_KEY');

// Connect with session cookie (in Interface Mode)
const ws = new WebSocket('ws://localhost:8000/ws/agent');

// Send a message
ws.send(JSON.stringify({ prompt: "Hello, agent!" }));

// Receive messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data.type, data.content);
};
```

---

## 7. Quick Commands Reference

```bash
# Clone and setup
git clone https://github.com/your-username/beubble-2.0.git
cd beubble-2.0/backend

# Docker build and run (local)
sudo DOCKER_BUILDKIT=0 docker build -t beubble-app .
docker run -d -p 8000:8000 --env-file .env --name beubble-backend beubble-app

# Monitor logs
docker logs -f beubble-backend

# Stop and remove container
docker stop beubble-backend
docker rm beubble-backend

# Access application
# Open http://localhost:8000 in your browser

# Without Docker (local development)
pip install -r requirements.txt
playwright install
python server.py
```

---

## 8. Troubleshooting

### Common Issues and Solutions

#### Port Already in Use
```bash
# Find and kill process using port 8000
sudo lsof -i :8000
sudo kill -9 <PID>
```

#### Docker Build Failing
```bash
# Clear Docker cache and rebuild
docker system prune -a
sudo DOCKER_BUILDKIT=0 docker build --no-cache -t beubble-app .
```

#### Playwright Issues
```bash
# Reinstall Playwright browsers inside container
docker exec -it beubble-backend playwright install

# Or for local development
playwright install
```

#### Environment Variables Not Loading
```bash
# Verify .env file exists
ls -la backend/.env

# Check variables are loaded in container
docker exec beubble-backend env | grep DASHSCOPE

# Ensure .env is properly formatted (no quotes around values)
```

#### Authentication Issues
```bash
# Check if Interface Mode is enabled
curl http://localhost:8000/api/auth/status

# Test API key authentication
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/health

# Login to get session cookie
curl -X POST -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/auth/login
```

#### WebSocket Connection Refused
```bash
# Ensure WebSocket endpoint is accessible
# Check if authentication is required (try with api_key parameter)
# Verify CORS settings in production
```

---

## 9. Features Summary

- **Multi-Agent Orchestration**: Central MotherAgent coordinates specialized sub-agents
- **Real-time Communication**: WebSocket support for live logging and agent interaction
- **Flexible Authentication**: Interface Mode for development, secure mode for production
- **Session Management**: Multiple conversation sessions with persistent memory
- **Workspace Management**: File upload, download, and folder operations
- **Browser Automation**: Playwright-based web navigation and screenshot capture
- **Vector Memory**: Qdrant-powered long-term memory with semantic search
- **RESTful API**: Comprehensive API for all system functions
- **Static Frontend**: Integrated UI served directly from the backend
- **Docker Support**: Easy deployment with containerization

---

## 10. Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Guidelines:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 11. License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 12. Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Playwright](https://playwright.dev/) - Browser automation
- [Qdrant](https://qdrant.tech/) - Vector database
- [DashScope](https://dashscope.aliyun.com/) - Qwen AI models
- [Jina AI](https://jina.ai/) - Embeddings and RAG
- [Brave Search](https://brave.com/search/api/) - Web search API

---

*Beubble 2.0 - Advanced Multi-Agent Orchestration Platform*
