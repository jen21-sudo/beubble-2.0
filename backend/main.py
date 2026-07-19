# backend/server.py
import os
import sys
import time
import json
import asyncio
import base64
import io
import logging
import shutil
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile, Depends, HTTPException, Request, Response, Cookie
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

# ============================================================
# 1. CONFIGURATION
# ============================================================

from config import config
from auth import get_api_key, optional_api_key, AuthManager, CookieAuth

# Add to PYTHONPATH
ROOT_DIR = config.BASE_DIR
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Directories
DATABASE_DIR = config.DATABASE_DIR
WORKSPACE_DIR = config.WORKSPACE_DIR
LOGS_DIR = config.LOGS_DIR
FRONTEND_DIR = ROOT_DIR / "frontend" / "public"

# Database paths
SESSION_DB_PATH = config.get_db_path("session_store.db")
CONVERSATION_DB_PATH = config.get_db_path("conversation_memory.db")

# ============================================================
# 2. MODULE IMPORTS
# ============================================================

from core.mother import MotherAgent
from driver.browser_driver import BrowserDriver
from sub_agent.navigator import MultiAgentNavigator
from memory.conversation_memory import ConversationMemory

# ============================================================
# 3. LOGGING
# ============================================================

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - [%(threadName)s] - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Server")

# ============================================================
# 4. GLOBAL STATE
# ============================================================

mother = None
browser_driver = None
conv_memory = None
latest_browser_screenshot = None
browser_screenshot_history = []
connected_websockets = set()

# ============================================================
# 5. PYDANTIC MODELS
# ============================================================

class ChatRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None

class SessionSwitchRequest(BaseModel):
    session_id: str

class ChatResponse(BaseModel):
    response: str
    files: List[str] = []
    plan: Optional[str] = None
    session_id: str
    execution_time: float

class CreateFolderRequest(BaseModel):
    name: str

# ============================================================
# 6. WEBSOCKET LOG HANDLER
# ============================================================

class WebSocketLogHandler(logging.Handler):
    def __init__(self, websocket=None, loop=None):
        super().__init__()
        self.websocket = websocket
        self.loop = loop
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def set_websocket(self, websocket, loop):
        self.websocket = websocket
        self.loop = loop
    
    def emit(self, record):
        if not self.websocket or not self.loop:
            return
        
        try:
            log_entry = self.format(record)
            log_message = log_entry
            
            level = record.levelname
            if level == 'ERROR':
                log_message = f"ERROR: {record.getMessage()}"
            elif level == 'WARNING':
                log_message = f"WARNING: {record.getMessage()}"
            elif 'Sub-Agent' in record.name or 'Navigator' in record.name:
                log_message = f"[SUB-AGENT] {record.getMessage()}"
            elif 'TabAgent' in record.name:
                log_message = f"[TAB] {record.getMessage()}"
            
            asyncio.run_coroutine_threadsafe(
                self.websocket.send_json({
                    "type": "log",
                    "content": log_message,
                    "level": level,
                    "timestamp": datetime.now().isoformat()
                }),
                self.loop
            )
        except Exception as e:
            print(f"WebSocketLogHandler error: {e}")

ws_log_handler = WebSocketLogHandler()

# Configure loggers
root_logger = logging.getLogger()
root_logger.addHandler(ws_log_handler)

for logger_name in ['NavigationAgent', 'TabAgent', 'MultiAgentNavigator', 
                    'BrowserDriver', 'MotherSystem', 'TerminalAgent']:
    logger_obj = logging.getLogger(logger_name)
    logger_obj.addHandler(ws_log_handler)
    logger_obj.setLevel(logging.INFO)

ws_log_handler.setLevel(logging.INFO)

# ============================================================
# 7. CALLBACKS
# ============================================================

def on_browser_screenshot(data: dict):
    global latest_browser_screenshot
    
    image_base64 = ""
    if data.get("filepath") and os.path.exists(data["filepath"]):
        with open(data["filepath"], "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    screenshot_data = {
        "filename": data.get("filename", ""),
        "tab_name": data.get("tab_name", ""),
        "url": data.get("url", ""),
        "title": data.get("title", ""),
        "timestamp": datetime.now().isoformat(),
        "image": image_base64
    }
    
    latest_browser_screenshot = screenshot_data
    browser_screenshot_history.append(screenshot_data)
    
    if len(browser_screenshot_history) > 50:
        browser_screenshot_history.pop(0)
    
    for ws in connected_websockets.copy():
        try:
            asyncio.run_coroutine_threadsafe(
                ws.send_json({
                    "type": "screenshot", 
                    "data": {
                        "tab_name": screenshot_data["tab_name"],
                        "url": screenshot_data["url"],
                        "timestamp": screenshot_data["timestamp"]
                    }
                }),
                asyncio.get_event_loop()
            )
        except Exception as e:
            print(f"DEBUG: WebSocket send error: {e}")
            connected_websockets.discard(ws)

# ============================================================
# 8. LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mother, browser_driver, conv_memory
    
    print("\n" + "="*60)
    print("BEUBBLE 2.0 - INITIALIZATION")
    print("="*60)
    
    # Afficher le mode
    if config.INTERFACE_MODE:
        print("🌐 MODE INTERFACE ACTIVÉ - Pas de clé API requise")
        print("   ⚠️  Utilisez ce mode uniquement pour le développement ou les démonstrations")
    else:
        print("🔒 MODE SÉCURISÉ - Clé API requise")
    
    # Display API keys status
    keys_status = config.check_keys()
    print("\nAPI KEYS STATUS:")
    for key, status in keys_status.items():
        status_str = "✅ OK" if status else "❌ MISSING"
        print(f"  {status_str} {key}")
    
    missing = config.get_missing_keys()
    if missing:
        print(f"\n⚠️  Missing keys: {', '.join(missing)}")
        print("   Some features may be limited.")
    
    print("\n" + "="*60)
    
    try:
        print("\n[System] Initializing Conversation Memory...")
        conv_memory = ConversationMemory(db_path=CONVERSATION_DB_PATH)
        print("[System] Conversation Memory ready.")
        
        print("[System] Initializing Mother Agent...")
        mother = MotherAgent()
        print("[System] Mother Agent ready.")
        print(f"[System] Session ID: {mother.session_id}")
        print(f"[System] Model: {config.DEFAULT_MODEL}")
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        mother = None
    
    print("\n" + "="*60)
    print("🚀 SERVER READY")
    print(f"📍 URL: http://{config.HOST}:{config.PORT}")
    if config.INTERFACE_MODE:
        print("🌐 Interface Mode: ON (no API key required)")
    else:
        print("🔒 Interface Mode: OFF (API key required)")
    print("="*60 + "\n")
    
    yield
    
    print("\n🛑 Shutting down server...")
    if browser_driver:
        await browser_driver.close_browser()
    if mother and hasattr(mother, 'ltm') and mother.ltm:
        try:
            mother.ltm.client.close()
        except:
            pass

# ============================================================
# 9. APPLICATION
# ============================================================

app = FastAPI(
    title="Beubble 2.0 API",
    description="Multi-Agent System with DASHSCOPE, BRAVE, JINA",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if config.DEBUG else None,
    redoc_url="/api/redoc" if config.DEBUG else None
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if config.ENVIRONMENT == "development" else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 10. AUTHENTICATION ROUTES
# ============================================================

@app.post("/api/auth/login")
async def login(response: Response, api_key: str = Depends(get_api_key)):
    """Login - Sets a secure session cookie"""
    await CookieAuth.set_session_cookie(response, api_key)
    return {
        "status": "success",
        "message": "Logged in successfully",
        "expires_in": 86400
    }

@app.post("/api/auth/logout")
async def logout(response: Response):
    """Logout - Clears the session cookie"""
    await CookieAuth.clear_session_cookie(response)
    return {"status": "success", "message": "Logged out"}

@app.get("/api/auth/status")
async def auth_status(session: Optional[str] = Cookie(None)):
    """Check authentication status"""
    is_authenticated = session and AuthManager.verify_api_key(session)
    return {
        "authenticated": is_authenticated or config.INTERFACE_MODE,
        "environment": config.ENVIRONMENT,
        "interface_mode": config.INTERFACE_MODE
    }

# ============================================================
# 11. AUTH DEPENDENCY (MODIFIED - Support Interface Mode)
# ============================================================

async def get_auth(
    api_key: Optional[str] = Depends(get_api_key),
    session: Optional[str] = Cookie(None)
) -> str:
    """
    Get authentication from either API key or cookie.
    In INTERFACE_MODE, allows access without authentication.
    """
    # INTERFACE MODE: Allow all access without API key
    if config.INTERFACE_MODE:
        logger.debug("Interface Mode: Allowing access without authentication")
        return "interface_user"
    
    # Production mode: Require authentication
    if api_key:
        if AuthManager.verify_api_key(api_key):
            return api_key
        else:
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    if session:
        if AuthManager.verify_api_key(session):
            return session
        else:
            raise HTTPException(status_code=401, detail="Invalid session")
    
    raise HTTPException(status_code=401, detail="Unauthorized - API key or session required")

# ============================================================
# 12. API ROUTES
# ============================================================

# --- 12.1 Health Check ---
@app.get("/api/health")
async def health_check():
    """Health check with keys status"""
    return {
        "status": "healthy",
        "session_id": mother.session_id if mother else None,
        "environment": config.ENVIRONMENT,
        "interface_mode": config.INTERFACE_MODE,
        "keys_configured": {
            "dashscope": bool(config.DASHSCOPE_API_KEY),
            "brave": bool(config.BRAVE_SEARCH_API_KEY),
            "jina": bool(config.JINA_API_KEY)
        },
        "timestamp": datetime.now().isoformat()
    }

# --- 12.2 Chat API ---
@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    auth: str = Depends(get_auth)
):
    """Chat endpoint with Qwen models"""
    global mother
    
    if not mother:
        raise HTTPException(status_code=503, detail="Mother Agent unavailable")
    
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    if request.session_id and request.session_id != mother.session_id:
        try:
            mother.switch_session(request.session_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Session switch failed: {str(e)}")
    
    start_time = time.time()
    
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, mother.handle_interaction, request.prompt)
        
        execution_time = time.time() - start_time
        
        return ChatResponse(
            response=result.get("response", "Task completed."),
            files=result.get("files", []),
            plan=result.get("plan"),
            session_id=mother.session_id,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 12.3 Sessions ---
@app.get("/api/sessions")
async def get_sessions(auth: str = Depends(get_auth)):
    """Get all sessions"""
    if not conv_memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    try:
        sessions = conv_memory.get_all_sessions()
        return {"status": "success", "sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/current")
async def get_current_session(auth: str = Depends(get_auth)):
    """Get current session"""
    if not mother:
        raise HTTPException(status_code=503, detail="Mother not initialized")
    return {
        "status": "success",
        "session_id": mother.session_id,
        "history_count": len(mother.recent_history) if mother.recent_history else 0
    }

@app.post("/api/session/switch")
async def switch_session(
    request: SessionSwitchRequest,
    auth: str = Depends(get_auth)
):
    """Switch session"""
    global mother
    if not mother:
        raise HTTPException(status_code=503, detail="Mother not initialized")
    try:
        mother.switch_session(request.session_id)
        return {"status": "success", "session_id": request.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/create")
async def create_session(auth: str = Depends(get_auth)):
    """Create a new session"""
    global mother
    if not conv_memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    try:
        session_id = conv_memory.get_or_create_session()
        if mother:
            mother.switch_session(session_id)
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/session/{session_id}")
async def delete_session(
    session_id: str,
    auth: str = Depends(get_auth)
):
    """Delete a session"""
    if not conv_memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    try:
        conv_memory.clear_session(session_id)
        return {"status": "success", "message": f"Session {session_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: int = 50,
    auth: str = Depends(get_auth)
):
    """Get session history"""
    if not conv_memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    try:
        history = conv_memory.get_last_n_interactions(session_id, limit=limit)
        return {"status": "success", "session_id": session_id, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/stats")
async def get_session_stats(auth: str = Depends(get_auth)):
    """Get session statistics"""
    global mother
    if mother:
        try:
            stats = mother.get_conversation_stats()
            return {"status": "success", "stats": stats}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=503, detail="Mother not initialized")

@app.post("/api/session/clear")
async def clear_current_session(auth: str = Depends(get_auth)):
    """Clear current conversation"""
    global mother
    if mother:
        try:
            mother.clear_conversation()
            return {"status": "success", "message": "Conversation cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=503, detail="Mother not initialized")

# --- 12.4 Workspace ---
def get_workspace_tree(path: Path) -> List[Dict[str, Any]]:
    items = []
    try:
        for item in sorted(path.iterdir()):
            if item.name.startswith('.'):
                continue
            rel_path = str(item.relative_to(WORKSPACE_DIR))
            if item.is_dir():
                items.append({
                    "name": item.name,
                    "path": rel_path,
                    "type": "folder",
                    "children": get_workspace_tree(item)
                })
            else:
                size = item.stat().st_size
                items.append({
                    "name": item.name,
                    "path": rel_path,
                    "type": "file",
                    "size": size,
                    "size_str": f"{size/1024:.1f} KB" if size > 1024 else f"{size} B"
                })
    except PermissionError:
        pass
    return items

@app.get("/api/workspace")
async def get_workspace(auth: str = Depends(get_auth)):
    """Get workspace tree"""
    tree = get_workspace_tree(WORKSPACE_DIR)
    return {"status": "success", "path": str(WORKSPACE_DIR), "items": tree}

@app.post("/api/workspace/upload")
async def upload_file(
    file: UploadFile,
    auth: str = Depends(get_auth)
):
    """Upload a file to workspace"""
    safe_filename = Path(file.filename).name
    file_path = WORKSPACE_DIR / safe_filename
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        return {"status": "success", "message": f"Uploaded: {safe_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/download/{path:path}")
async def download_file(
    path: str,
    auth: str = Depends(get_auth)
):
    """Download a file from workspace"""
    file_path = WORKSPACE_DIR / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if file_path.is_dir():
        raise HTTPException(status_code=400, detail="Cannot download folder")
    return FileResponse(path=file_path, filename=file_path.name)

@app.post("/api/workspace/folder")
async def create_folder(
    request: CreateFolderRequest,
    auth: str = Depends(get_auth)
):
    """Create a new folder in workspace"""
    folder_path = WORKSPACE_DIR / request.name
    if folder_path.exists():
        raise HTTPException(status_code=400, detail="Folder already exists")
    try:
        folder_path.mkdir(parents=True, exist_ok=True)
        return {"status": "success", "message": f"Folder created: {request.name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/workspace/{path:path}")
async def delete_file(
    path: str,
    auth: str = Depends(get_auth)
):
    """Delete a file or folder from workspace"""
    file_path = WORKSPACE_DIR / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        return {"status": "success", "message": f"Deleted: {path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 12.5 Screenshots ---
@app.get("/api/screenshots/latest")
async def get_latest_screenshot(auth: str = Depends(get_auth)):
    """Get latest screenshot"""
    if latest_browser_screenshot and latest_browser_screenshot.get("image"):
        return latest_browser_screenshot
    return {"image": None, "message": "No capture"}

@app.get("/api/screenshots/history")
async def get_screenshot_history(
    limit: int = 20,
    auth: str = Depends(get_auth)
):
    """Get screenshot history"""
    return browser_screenshot_history[-limit:]

# ============================================================
# 13. WEBSOCKET AGENT (MODIFIED - Support Interface Mode)
# ============================================================

class CaptureAndRedirect:
    def __init__(self, original_stdout, websocket: WebSocket, loop: asyncio.AbstractEventLoop):
        self.original = original_stdout
        self.websocket = websocket
        self.loop = loop
        self.captured = io.StringIO()
        self.buffer = []
    
    def write(self, message):
        self.original.write(message)
        self.captured.write(message)
        
        # Nettoyer les codes ANSI pour le WebSocket
        clean_message = re.sub(r'\x1b\[[0-9;]*m', '', message)
        clean_message = clean_message.strip()
        
        if clean_message:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send_json({
                        "type": "log", 
                        "content": clean_message,
                        "level": "INFO"
                    }),
                    self.loop
                )
            except Exception:
                pass
    
    def flush(self):
        self.original.flush()
    
    def get_captured(self) -> str:
        return self.captured.getvalue()

@app.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket):
    """WebSocket with log streaming - Supports Interface Mode"""
    
    # Check API key in query params
    api_key = websocket.query_params.get("api_key")
    session_cookie = websocket.query_params.get("session")
    
    # Check authentication
    is_authenticated = False
    auth_reason = ""
    
    # INTERFACE MODE: Allow all connections
    if config.INTERFACE_MODE:
        is_authenticated = True
        auth_reason = "Interface Mode (no auth required)"
        logger.info("WebSocket: Interface mode - allowing connection without API key")
    
    # Try API key (if provided)
    elif api_key and AuthManager.verify_api_key(api_key):
        is_authenticated = True
        auth_reason = "API Key"
    
    # Try session cookie
    elif session_cookie and AuthManager.verify_api_key(session_cookie):
        is_authenticated = True
        auth_reason = "Session Cookie"
    
    # Development mode: Allow if no key (for testing)
    elif config.ENVIRONMENT == "development" and config.DEBUG:
        is_authenticated = True
        auth_reason = "Development Mode"
        logger.warning("WebSocket: Development mode - allowing connection without API key")
    
    if not is_authenticated:
        logger.warning(f"WebSocket: Authentication failed - API key missing or invalid")
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    # Accept connection
    await websocket.accept()
    connected_websockets.add(websocket)
    logger.info(f"WebSocket: Connection accepted - {auth_reason}")
    
    loop = asyncio.get_running_loop()
    ws_log_handler.set_websocket(websocket, loop)
    
    # Send connection info
    await websocket.send_json({
        "type": "info",
        "content": "✅ Connected to Beubble 2.0",
        "model": config.DEFAULT_MODEL,
        "interface_mode": config.INTERFACE_MODE,
        "auth_method": auth_reason,
        "keys_available": {
            "dashscope": bool(config.DASHSCOPE_API_KEY),
            "brave": bool(config.BRAVE_SEARCH_API_KEY),
            "jina": bool(config.JINA_API_KEY)
        }
    })
    
    if mother:
        await websocket.send_json({
            "type": "info",
            "content": f"📝 Session: {mother.session_id}"
        })
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_input = payload.get("prompt", "").strip()
            
            if not user_input:
                continue
                
            if not mother:
                await websocket.send_json({"type": "error", "content": "❌ Mother Agent unavailable."})
                continue

            await websocket.send_json({"type": "status", "content": f"⏳ Processing: '{user_input}'"})
            start_time = time.time()

            old_stdout = sys.stdout
            capture_redirect = CaptureAndRedirect(old_stdout, websocket, loop)
            sys.stdout = capture_redirect

            try:
                result = await loop.run_in_executor(None, mother.handle_interaction, user_input)
                
                bot_response = result.get("response", "Task completed successfully.")
                created_files = result.get("files", [])
                plan = result.get("plan", None)
                
                if plan:
                    await websocket.send_json({"type": "plan", "content": plan})
                
                await websocket.send_json({
                    "type": "bot_response",
                    "content": bot_response,
                    "files": created_files,
                    "model": config.DEFAULT_MODEL
                })
                
                if created_files:
                    await websocket.send_json({
                        "type": "log",
                        "content": f"📁 Files created: {', '.join(created_files)}",
                        "level": "INFO"
                    })
                
                elapsed = time.time() - start_time
                await websocket.send_json({
                    "type": "log",
                    "content": f"⏱️ Execution time: {elapsed:.2f}s",
                    "level": "INFO"
                })
                
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                await websocket.send_json({"type": "error", "content": error_msg})
                import traceback
                traceback.print_exc()
            finally:
                sys.stdout = old_stdout

    except WebSocketDisconnect:
        connected_websockets.discard(websocket)
        if ws_log_handler.websocket == websocket:
            ws_log_handler.set_websocket(None, None)
        logger.info("WebSocket: Client disconnected")
    except Exception as e:
        connected_websockets.discard(websocket)
        logger.error(f"WebSocket error: {e}")

# ============================================================
# 14. FRONTEND STATIC FILES
# ============================================================

# Serve static frontend files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="public")
    logger.info(f"Serving static files from: {FRONTEND_DIR}")

@app.get("/")
async def serve_frontend():
    """Serve HTML interface."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    else:
        return HTMLResponse("""
        <html>
            <head><title>Beubble 2.0</title></head>
            <body>
                <h1>🫧 Beubble 2.0</h1>
                <p>Frontend not found. Please place your HTML in <code>frontend/public/</code></p>
                <p>API Documentation: <a href="/api/docs">/api/docs</a></p>
                <p>Health Check: <a href="/api/health">/api/health</a></p>
            </body>
        </html>
        """)

# ============================================================
# 15. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    print(f"\n🚀 Starting Beubble 2.0 Server")
    print(f"📍 Host: {config.HOST}:{config.PORT}")
    print(f"🌐 Interface Mode: {'ON (no auth)' if config.INTERFACE_MODE else 'OFF (auth required)'}")
    print(f"🔑 API Keys: {'✅' if config.DASHSCOPE_API_KEY else '❌'} DashScope | {'✅' if config.BRAVE_SEARCH_API_KEY else '❌'} Brave | {'✅' if config.JINA_API_KEY else '❌'} Jina")
    print(f"📚 API Docs: http://{config.HOST}:{config.PORT}/api/docs\n")
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
        log_level=config.LOG_LEVEL.lower()
    )
