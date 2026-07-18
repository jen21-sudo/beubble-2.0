# core/mother.py - Advanced orchestrator with resilience and data flow

import sys
import os

# ============================================================
# 1. ABSOLUTE PATHS CONFIGURATION (USING CONFIG)
# ============================================================

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import config first to use its paths
from config import config

# Use config paths with fallback to original behavior
DATABASE_DIR = str(config.DATABASE_DIR) if hasattr(config, 'DATABASE_DIR') else os.path.join(ROOT_DIR, "database")
WORKSPACE_DIR = str(config.WORKSPACE_DIR) if hasattr(config, 'WORKSPACE_DIR') else os.path.join(ROOT_DIR, "workspace")
LOGS_DIR = str(config.LOGS_DIR) if hasattr(config, 'LOGS_DIR') else os.path.join(ROOT_DIR, "logs")

# Create directories if they don't exist
for dir_path in [DATABASE_DIR, WORKSPACE_DIR, LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Database paths
SESSION_DB_PATH = os.path.join(DATABASE_DIR, "session_store.db")
CONVERSATION_DB_PATH = os.path.join(DATABASE_DIR, "conversation_memory.db")
QDRANT_PATH = os.path.join(DATABASE_DIR, "qdrant_db")

# ============================================================
# 2. IMPORTS
# ============================================================

import json
import queue
import threading
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from enum import Enum

from AI_models.qwen.qwen_version import UniversalAgent
from memory.agent_memory.working_memo import WorkingMemory
from memory.agent_memory.session_memory import SessionMemory
from memory.LTM.long_term_memory import LongTermMemory
from memory.conversation_memory import ConversationMemory

from sub_agent.terminal_agent import TerminalAgent
from sub_agent.navigator import MultiAgentNavigator
from sub_agent.api_agent import APIAgent
from driver.terminal_driver import TerminalDriver

# ============================================================
# 3. LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(threadName)s] - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "mother.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MotherSystem")

# ============================================================
# 4. ACTION PLAN
# ============================================================

class ActionStatus(Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    SKIPPED = "Skipped"

class ActionStep:
    def __init__(self, step_id: int, description: str, agent: str, action_type: str, details: dict = None):
        self.id = step_id
        self.description = description
        self.agent = agent
        self.action_type = action_type
        self.details = details or {}
        self.status = ActionStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "agent": self.agent,
            "action_type": self.action_type,
            "status": self.status.value,
            "result": self.result,
            "error": self.error
        }

    def mark_started(self):
        self.status = ActionStatus.IN_PROGRESS
        self.start_time = datetime.now()

    def mark_completed(self, result=None):
        self.status = ActionStatus.COMPLETED
        self.result = result
        self.end_time = datetime.now()

    def mark_failed(self, error):
        self.status = ActionStatus.FAILED
        self.error = error
        self.end_time = datetime.now()

    def mark_skipped(self):
        self.status = ActionStatus.SKIPPED

class ActionPlan:
    def __init__(self, user_objective: str):
        self.user_objective = user_objective
        self.steps: List[ActionStep] = []
        self.current_step_index = 0
        self.created_at = datetime.now()
        self.completed_at = None

    def add_step(self, description: str, agent: str, action_type: str, details: dict = None) -> int:
        step_id = len(self.steps) + 1
        step = ActionStep(step_id, description, agent, action_type, details)
        self.steps.append(step)
        return step_id

    def get_current_step(self) -> Optional[ActionStep]:
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance(self):
        self.current_step_index += 1
        if self.current_step_index >= len(self.steps):
            self.completed_at = datetime.now()

    def get_progress(self) -> dict:
        total = len(self.steps)
        completed = sum(1 for s in self.steps if s.status == ActionStatus.COMPLETED)
        failed = sum(1 for s in self.steps if s.status == ActionStatus.FAILED)
        pending = sum(1 for s in self.steps if s.status == ActionStatus.PENDING)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "percentage": (completed / total * 100) if total > 0 else 0
        }

    def format_for_user(self) -> str:
        lines = ["ACTION PLAN"]
        lines.append(f"Objective: {self.user_objective}")
        lines.append("")

        progress = self.get_progress()
        lines.append(f"Progress: {progress['percentage']:.0f}% ({progress['completed']}/{progress['total']} steps)")
        lines.append("")

        for step in self.steps:
            status_icon = {
                ActionStatus.PENDING: "[PENDING]",
                ActionStatus.IN_PROGRESS: "[IN PROGRESS]",
                ActionStatus.COMPLETED: "[COMPLETED]",
                ActionStatus.FAILED: "[FAILED]",
                ActionStatus.SKIPPED: "[SKIPPED]"
            }.get(step.status, "[UNKNOWN]")

            lines.append(f"{status_icon} Step {step.id}: {step.description}")
            lines.append(f"   Agent: {step.agent}")
            lines.append(f"   Status: {step.status.value}")

            if step.result:
                result_preview = str(step.result)[:100] + ("..." if len(str(step.result)) > 100 else "")
                lines.append(f"   Result: {result_preview}")

            if step.error:
                lines.append(f"   Error: {step.error}")

            lines.append("")

        return "\n".join(lines)


# ============================================================
# 5. WORKER THREADS
# ============================================================

class BrowserWorkerThread(threading.Thread):
    """Browser thread that collects raw data and returns it without alteration."""

    def __init__(self, objective: str, targets: dict, session_context: str, result_queue: queue.Queue):
        super().__init__(name="Thread-Agent-Browser")
        self.objective = objective
        self.targets = targets if (targets and isinstance(targets, dict) and len(targets) > 0) else {"GeneralSearch": objective}
        self.result_queue = result_queue
        self._loop = None

    def run(self):
        logger.info(f"Starting Navigator with {len(self.targets)} search queries...")

        try:
            session = SessionMemory(db_path=SESSION_DB_PATH)
        except:
            class DummySession:
                def get_env_dict(self): return {}
                def save_shared_data(self, key, val): pass
            session = DummySession()

        os.environ.update(session.get_env_dict())

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            browser_results = self._loop.run_until_complete(self._run_navigation())

            logger.info(f"Browser results: status={browser_results.get('status')}, data_count={len(browser_results.get('data', []))}")

            # Direct save of raw data without restrictive validation
            try:
                session.save_shared_data("browser_data", {
                    "extracted_at": datetime.now().isoformat(),
                    "thread_name": self.name,
                    "search_queries": self.targets,
                    "raw_data": browser_results
                })
                logger.info(f"[Shared] Browser data saved")
            except Exception as e:
                logger.error(f"Save error: {e}")

            # Send result to queue
            self.result_queue.put({
                "agent": "browser",
                "status": browser_results.get("status", "error"),
                "raw_data": browser_results,
                "search_queries_used": self.targets
            })

        except Exception as e:
            logger.error(f"Navigator Thread Error: {e}")
            import traceback
            traceback.print_exc()
            self.result_queue.put({
                "agent": "browser",
                "status": "error",
                "raw_data": None,
                "error_message": str(e)
            })
        finally:
            if self._loop:
                self._loop.close()

    async def _run_navigation(self):
        navigator = None
        try:
            navigator = MultiAgentNavigator(headless=True)
            await navigator.initialize_browser()

            added_count = 0
            for name, query in self.targets.items():
                try:
                    if query and isinstance(query, str):
                        await navigator.add_agent(name, query)
                        added_count += 1
                except Exception as e:
                    logger.error(f"Error adding agent {name}: {e}")

            if added_count == 0:
                return {"status": "error", "message": "No agents added", "data": []}

            await asyncio.sleep(0.1)

            try:
                browser_results = await asyncio.wait_for(
                    navigator.execute_parallel(objective=self.objective, max_steps=12),
                    timeout=60
                )
                return browser_results
            except asyncio.TimeoutError:
                return {"status": "error", "message": "Search timeout", "data": []}

        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}
        finally:
            if navigator:
                try:
                    await navigator.close_browser()
                except:
                    pass


class TerminalWorkerThread(threading.Thread):
    def __init__(self, objective: str, session_context: str, result_queue: queue.Queue):
        super().__init__(name="Thread-Agent-Terminal")
        self.objective = objective
        self.session_context = session_context
        self.result_queue = result_queue
        self.driver = TerminalDriver()

    def run(self):
        logger.info("Starting Terminal Agent Thread...")

        try:
            session = SessionMemory(db_path=SESSION_DB_PATH)
        except:
            session = SessionMemory()

        real_env = session.get_env_dict()
        os.environ.update(real_env)
        self.driver.environment.update(real_env)

        browser_data = session.get_shared_data("browser_data")
        api_data = session.get_shared_data("api_result")

        shared_context = ""
        if api_data and api_data.get("raw_data"):
            shared_context += f"\nAPI Data:\n{json.dumps(api_data.get('raw_data'), indent=2, ensure_ascii=False)[:1500]}"
        if browser_data and browser_data.get("raw_data"):
            shared_context += f"\nBrowser Data:\n{json.dumps(browser_data.get('raw_data'), indent=2, ensure_ascii=False)[:1500]}"

        enriched_objective = f"{self.objective}\n\n{shared_context}"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            agent = TerminalAgent(workspace_dir=WORKSPACE_DIR)
            agent.driver = self.driver
            terminal_result = loop.run_until_complete(agent.run_mission(enriched_objective, max_steps=15))

            session.save_shared_data("terminal_result", {
                "extracted_at": datetime.now().isoformat(),
                "thread_name": self.name,
                "raw_data": terminal_result
            })

            self.result_queue.put({
                "agent": "terminal",
                "status": "success",
                "raw_data": terminal_result
            })
        except Exception as e:
            logger.error(f"TerminalAgent Error: {e}")
            self.result_queue.put({
                "agent": "terminal",
                "status": "error",
                "raw_data": None,
                "error_message": str(e)
            })
        finally:
            loop.close()


class APIWorkerThread(threading.Thread):
    def __init__(self, objective: str, session_context: str, result_queue: queue.Queue):
        super().__init__(name="Thread-Agent-API")
        self.objective = objective
        self.session_context = session_context
        self.result_queue = result_queue

    def run(self):
        logger.info("Starting API Agent Thread...")

        try:
            session = SessionMemory(db_path=SESSION_DB_PATH)
        except:
            session = SessionMemory()
        os.environ.update(session.get_env_dict())

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            agent = APIAgent()
            api_results = loop.run_until_complete(agent.run_mission(self.objective, max_steps=5))

            session.save_shared_data("api_result", {
                "extracted_at": datetime.now().isoformat(),
                "thread_name": self.name,
                "raw_data": api_results
            })

            status = "blocked" if isinstance(api_results, dict) and api_results.get("status") == "blocked" else "success"
            self.result_queue.put({
                "agent": "api",
                "status": status,
                "raw_data": api_results
            })
        except Exception as e:
            logger.error(f"APIAgent Error: {e}")
            self.result_queue.put({
                "agent": "api",
                "status": "error",
                "raw_data": None,
                "error_message": str(e)
            })
        finally:
            loop.close()


# ============================================================
# 6. MAIN COMPONENT: MOTHER AGENT (ADVANCED ORCHESTRATOR)
# ============================================================

class MotherAgent:
    def __init__(self, session_id: str = None):
        logger.info("Initializing MotherAgent with advanced orchestration...")

        # Directories
        for dir_path in [DATABASE_DIR, WORKSPACE_DIR, LOGS_DIR]:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {dir_path}: {e}")

        self.llm = UniversalAgent()
        self.result_queue = queue.Queue()
        self.workspace_path = Path(WORKSPACE_DIR)
        self.max_history = 10
        self.current_plan: Optional[ActionPlan] = None

        # Resilient SessionMemory
        try:
            self.session_memory = SessionMemory(db_path=SESSION_DB_PATH)
        except Exception as e:
            logger.error(f"SessionMemory error: {e}")
            try:
                self.session_memory = SessionMemory(db_path=os.path.join(DATABASE_DIR, "session_fallback.db"))
            except:
                self.session_memory = SessionMemory()

        # Resilient LongTermMemory
        try:
            # Use config JINA_API_KEY if available
            jina_key = getattr(config, 'JINA_API_KEY', None)
            self.ltm = LongTermMemory(
                collection_name="beubble_memory",
                storage_path=QDRANT_PATH,
                jina_api_key=jina_key
            )
        except Exception as e:
            logger.error(f"LongTermMemory error: {e}")
            self.ltm = None

        # Resilient ConversationMemory
        try:
            self.conversation_memory = ConversationMemory(db_path=CONVERSATION_DB_PATH)
        except Exception as e:
            logger.error(f"ConversationMemory error: {e}")
            try:
                self.conversation_memory = ConversationMemory(db_path=os.path.join(DATABASE_DIR, "conversation_fallback.db"))
            except:
                self.conversation_memory = None

        # Session ID
        try:
            if self.conversation_memory:
                self.session_id = session_id or self.conversation_memory.get_or_create_session()
            else:
                self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        except Exception as e:
            logger.error(f"Session ID error: {e}")
            self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # History
        try:
            if self.conversation_memory:
                self.recent_history = self.conversation_memory.get_last_n_interactions(self.session_id, n=5)
            else:
                self.recent_history = []
        except Exception as e:
            logger.error(f"History error: {e}")
            self.recent_history = []

        if not isinstance(self.recent_history, list):
            self.recent_history = []

        logger.info(f"MotherAgent ready. Session: {self.session_id}")

    # ============================================================
    # MEMORY & HISTORY
    # ============================================================

    def _add_to_history(self, role: str, content: str):
        try:
            if not isinstance(self.recent_history, list):
                self.recent_history = []
            self.recent_history.append({"role": role, "content": str(content)})
            if len(self.recent_history) > self.max_history * 2:
                self.recent_history = self.recent_history[-self.max_history * 2:]
            if self.conversation_memory:
                self.conversation_memory.add_interaction(
                    session_id=self.session_id,
                    role=role,
                    content=content,
                    metadata={"timestamp": datetime.now().isoformat()}
                )
        except Exception as e:
            logger.error(f"History save error: {e}")

    def _get_recent_history(self, n: int = 3) -> List[Dict[str, str]]:
        try:
            if self.conversation_memory:
                history = self.conversation_memory.get_last_n_interactions(self.session_id, n)
                if isinstance(history, list):
                    return history
            return self.recent_history[-n:] if self.recent_history else []
        except:
            return self.recent_history[-n:] if self.recent_history else []

    # ============================================================
    # INTELLIGENT RAW DATA EXTRACTION
    # ============================================================

    def _extract_raw_browser_data(self) -> str:
        """Extracts and formats raw browser data for synthesis prompt."""
        try:
            browser_data = self.session_memory.get_shared_data("browser_data")
            if not browser_data or not isinstance(browser_data, dict):
                return ""

            raw = browser_data.get("raw_data", {})
            if not isinstance(raw, dict):
                return ""

            data_list = raw.get("data", [])
            if not data_list:
                return ""

            parts = []
            for idx, item in enumerate(data_list, 1):
                if not isinstance(item, dict):
                    continue

                llm_context = item.get("llm_context", {})
                urls = item.get("urls", [])
                raw_snippets = item.get("raw_snippets", [])
                source = item.get("source", "unknown")
                metadata = item.get("_metadata", {})

                parts.append(f"--- Result {idx} (source: {source}) ---")

                if llm_context and isinstance(llm_context, dict):
                    parts.append(f"[Brave LLM Summary]: {json.dumps(llm_context, ensure_ascii=False)[:1500]}")
                elif llm_context and isinstance(llm_context, str):
                    parts.append(f"[Brave LLM Summary]: {llm_context[:1500]}")

                if raw_snippets:
                    parts.append(f"[Raw snippets]:")
                    for snippet in raw_snippets[:5]:
                        parts.append(f"  - {str(snippet)[:300]}")

                if urls:
                    parts.append(f"[URLs]:")
                    for url in urls[:5]:
                        parts.append(f"  - {url}")

                if metadata:
                    parts.append(f"[Metadata]: agent={metadata.get('agent')}, method={metadata.get('method')}")

                parts.append("")

            return "\n".join(parts) if parts else ""

        except Exception as e:
            logger.error(f"Error extracting raw browser data: {e}")
            return ""

    # ============================================================
    # INTELLIGENT PROMPTS
    # ============================================================

    def _build_planning_prompt(self, user_objective: str) -> str:
        recent = self._get_recent_history(3)
        context = "\n".join([f"{h.get('role', 'unknown')}: {str(h.get('content', ''))[:200]}" for h in recent])

        return f"""You are an intelligent agent orchestrator. Analyze the user request and decide the optimal agent activation sequence.

CONVERSATION HISTORY:
{context}

USER REQUEST: "{user_objective}"

AVAILABLE AGENTS:
- BROWSER: Web search (Brave Search API). Use for: prices, facts, news, product info, comparisons.
- API: External API calls. Use for: structured data, real-time info (crypto, weather, stocks).
- TERMINAL: File creation/execution. Use ONLY if user explicitly asks to save/create files.

DECISION RULES:
1. For information queries -> ONLY Browser (or Browser + API if real-time data needed)
2. For file creation requests -> Browser first (collect data), then Terminal (create files)
3. NEVER activate Terminal unless user explicitly asks for files
4. If the user mentions a specific site (e.g., Amazon), include that site in the browser objective
5. For price comparisons -> Browser with multiple targets

Respond ONLY with this JSON:
{{
    "phase_1_collect": {{
        "activate_browser": true/false,
        "browser_objective": "specific search objective",
        "browser_targets": {{"target_name": "search query"}},
        "activate_api": true/false,
        "api_objective": "API search objective"
    }},
    "phase_2_create": {{
        "activate_terminal": true/false,
        "terminal_objective": "file creation objective"
    }}
}}"""

    def _build_synthesis_prompt(self, user_objective: str, browser_raw: str = "", api_raw: str = "") -> str:
        """Builds a synthesis prompt that leverages ALL available data (LLM Context + raw snippets)."""

        if not browser_raw and not api_raw:
            return f"""No data found for: "{user_objective}". Politely ask the user to rephrase."""

        prompt = f"""You are a helpful, accurate assistant. Answer the user's question using ALL the data provided below.

USER QUESTION: "{user_objective}"

AVAILABLE DATA:
{browser_raw}

{api_raw if api_raw else ""}

INSTRUCTIONS:
1. Read ALL data carefully - both the Brave LLM summaries AND the raw snippets.
2. If the user asked about a specific site (e.g., Amazon), check ALL URLs and snippets for mentions of that site.
3. If you find the site mentioned but no price/specific data, say: "I found pages on [site] but the specific information wasn't visible in the search results. Here's what I found on other sites: [details]."
4. If prices are found, present them clearly with sources.
5. If the Brave LLM summary says "no data found" but the raw snippets contain useful information, IGNORE the summary and use the raw snippets.
6. Be honest - never invent information.
7. Respond in the same language as the user's question.
8. Be concise but complete.

YOUR RESPONSE:"""

        return prompt

    # ============================================================
    # AGENT EXECUTION
    # ============================================================

    def _execute_browser_step(self, step: ActionStep, plan: dict) -> dict:
        logger.info(f"Browser execution: {step.description}")

        # Safe queue cleanup
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except:
                break

        phase_1 = plan.get("phase_1_collect", {}) if isinstance(plan, dict) else {}
        objective = phase_1.get("browser_objective", step.description)
        targets = phase_1.get("browser_targets", {})

        try:
            thread = BrowserWorkerThread(objective, targets, "", self.result_queue)
            thread.start()
        except Exception as e:
            logger.error(f"Browser thread spawn failed: {e}")
            return {"status": "error", "error_message": str(e)}

        thread.join(timeout=120)

        if thread.is_alive():
            logger.error("Browser thread timeout")
            return {"status": "error", "error_message": "Browser thread timeout"}

        try:
            result = self.result_queue.get(timeout=2)
            if result and isinstance(result, dict):
                return result
        except queue.Empty:
            pass

        # Fallback: direct session read
        fallback = self.session_memory.get_shared_data("browser_data")
        if fallback:
            return {"status": "success", "raw_data": fallback.get("raw_data", {})}
        return {"status": "error", "error_message": "No browser data"}

    def _execute_terminal_step(self, step: ActionStep, plan: dict) -> dict:
        logger.info(f"Terminal execution: {step.description}")

        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except:
                break

        phase_2 = plan.get("phase_2_create", {}) if isinstance(plan, dict) else {}
        objective = phase_2.get("terminal_objective", step.description)

        # Enriched context
        browser_data = self.session_memory.get_shared_data("browser_data")
        api_data = self.session_memory.get_shared_data("api_result")

        shared_context = ""
        if api_data and api_data.get("raw_data"):
            shared_context += f"\nAPI Data:\n{json.dumps(api_data.get('raw_data'), indent=2, ensure_ascii=False)[:1500]}"
        if browser_data and browser_data.get("raw_data"):
            raw = browser_data.get("raw_data")
            if isinstance(raw, dict) and "data" in raw:
                raw = raw["data"]
            shared_context += f"\nBrowser Data:\n{json.dumps(raw, indent=2, ensure_ascii=False)[:1500]}"

        enriched = f"{objective}\n\n{shared_context}"

        try:
            thread = TerminalWorkerThread(enriched, "", self.result_queue)
            thread.start()
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

        thread.join(timeout=120)

        if thread.is_alive():
            return {"status": "error", "error_message": "Terminal thread timeout"}

        try:
            result = self.result_queue.get(timeout=2)
            if result and isinstance(result, dict):
                return result
        except queue.Empty:
            pass

        fallback = self.session_memory.get_shared_data("terminal_result")
        if fallback:
            return {"status": "success", "raw_data": fallback}
        return {"status": "error", "error_message": "No terminal data"}

    def _execute_api_step(self, step: ActionStep, plan: dict) -> dict:
        logger.info(f"API execution: {step.description}")

        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except:
                break

        phase_1 = plan.get("phase_1_collect", {}) if isinstance(plan, dict) else {}
        objective = phase_1.get("api_objective", step.description)

        try:
            thread = APIWorkerThread(objective, "", self.result_queue)
            thread.start()
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

        thread.join(timeout=60)

        if thread.is_alive():
            return {"status": "error", "error_message": "API thread timeout"}

        try:
            result = self.result_queue.get(timeout=2)
            if result and isinstance(result, dict):
                return result
        except queue.Empty:
            pass

        fallback = self.session_memory.get_shared_data("api_result")
        if fallback:
            return {"status": "success", "raw_data": fallback}
        return {"status": "error", "error_message": "No API data"}

    # ============================================================
    # MAIN ORCHESTRATION
    # ============================================================

    def handle_interaction(self, user_message: str) -> dict:
        print(f"\n[USER]: {user_message}\n" + "-" * 60)
        self._add_to_history("user", user_message)

        # 1. Detect if action is needed
        recent = self._get_recent_history(3)

        reception_prompt = f"""Determine if this request requires a technical action (web search, file creation, API call).

CONVERSATION HISTORY:
{recent}

USER REQUEST: "{user_message}"

Respond with [ACTACT] if action needed, or your natural response if not."""

        try:
            raw_response = self.llm.execute_string(reception_prompt)
        except:
            raw_response = "[ACTACT]"

        if "[ACTACT]" not in str(raw_response):
            response_text = str(raw_response).strip()
            for prefix in ['[BOT]:', '[RESPONSE]:']:
                if prefix in response_text:
                    response_text = response_text.split(prefix, 1)[1].strip()
            response_text = response_text.replace('[ACTACT]', '').strip()
            if not response_text:
                response_text = "Hello! How can I help you today?"
            print(f"[BOT]: {response_text}\n")
            self._add_to_history("assistant", response_text[:500])
            return {"response": response_text, "files": [], "plan": None}

        # 2. Planning
        print("\n" + "=" * 60)
        print("ANALYZING REQUEST")
        print("=" * 60)

        try:
            plan = self.llm.execute(self._build_planning_prompt(user_message))
            if not isinstance(plan, dict):
                raise ValueError("Invalid plan format")
            logger.info("Plan generated successfully")
        except Exception as e:
            logger.error(f"Planning error: {e}. Using safe default.")
            plan = {
                "phase_1_collect": {
                    "activate_browser": True,
                    "browser_objective": user_message,
                    "browser_targets": {"GeneralSearch": user_message},
                    "activate_api": False,
                    "api_objective": None
                },
                "phase_2_create": {
                    "activate_terminal": False,
                    "terminal_objective": None
                }
            }

        phase_1 = plan.get("phase_1_collect", {}) if isinstance(plan, dict) else {}
        phase_2 = plan.get("phase_2_create", {}) if isinstance(plan, dict) else {}

        activate_browser = bool(phase_1.get("activate_browser", True))
        activate_api = bool(phase_1.get("activate_api", False))
        activate_terminal = bool(phase_2.get("activate_terminal", False))

        # Build action plan
        self.current_plan = ActionPlan(user_message)

        if activate_browser:
            self.current_plan.add_step(
                description=str(phase_1.get("browser_objective", f"Search: {user_message}")),
                agent="Browser",
                action_type="browser"
            )
        if activate_api:
            self.current_plan.add_step(
                description=str(phase_1.get("api_objective", "API data")),
                agent="API",
                action_type="api"
            )
        if activate_terminal:
            self.current_plan.add_step(
                description=str(phase_2.get("terminal_objective", "Create files")),
                agent="Terminal",
                action_type="terminal"
            )

        print("\n" + "=" * 60)
        print(self.current_plan.format_for_user())
        print("=" * 60 + "\n")

        # 3. Execute steps
        all_results = {}

        for step in self.current_plan.steps:
            step.mark_started()

            try:
                if step.action_type == "browser":
                    result = self._execute_browser_step(step, plan)
                elif step.action_type == "api":
                    result = self._execute_api_step(step, plan)
                elif step.action_type == "terminal":
                    # Check if data exists before activating Terminal
                    browser_ok = self.session_memory.get_shared_data("browser_data") is not None
                    api_ok = self.session_memory.get_shared_data("api_result") is not None
                    if browser_ok or api_ok:
                        result = self._execute_terminal_step(step, plan)
                    else:
                        step.mark_skipped()
                        logger.info("Terminal skipped - no data collected")
                        continue
                else:
                    continue

                if result and isinstance(result, dict) and result.get("status") == "success":
                    step.mark_completed("Data collected")
                    all_results[step.action_type] = result
                else:
                    step.mark_failed(result.get("error_message", "Unknown error") if result else "No result")

            except Exception as e:
                logger.error(f"Step execution error: {e}")
                step.mark_failed(str(e))

            print("\n" + "=" * 60)
            print("Update")
            print(self.current_plan.format_for_user())
            print("=" * 60 + "\n")
            self.current_plan.advance()

        # 4. Final synthesis
        browser_raw = self._extract_raw_browser_data()
        api_raw = ""
        api_data = self.session_memory.get_shared_data("api_result")
        if api_data and isinstance(api_data, dict):
            api_raw = f"API Data:\n{json.dumps(api_data.get('raw_data', {}), indent=2, ensure_ascii=False)[:2000]}"

        has_data = bool(browser_raw) or bool(api_raw)

        if has_data:
            try:
                synthesis = self.llm.execute_string(
                    self._build_synthesis_prompt(user_message, browser_raw, api_raw)
                )
            except Exception as e:
                logger.error(f"Synthesis error: {e}")
                synthesis = f"I found some information but had trouble summarizing it clearly. Here's what I found:\n{browser_raw[:1000]}"
        else:
            synthesis = "I wasn't able to find specific information on that. Could you rephrase or provide more details?"

        # Final step in plan
        if self.current_plan:
            self.current_plan.add_step("Generate final response", "Mother", "synthesis")
            self.current_plan.advance()

        print("\n" + "=" * 60)
        print("COMPLETED")
        if self.current_plan:
            print(self.current_plan.format_for_user())
        print("=" * 60 + "\n")

        # Workspace files
        files = []
        try:
            if self.workspace_path.exists():
                files = [f.name for f in self.workspace_path.glob("*") if f.is_file()]
        except:
            pass

        print(f"\n[RESPONSE]:\n{synthesis}\n")
        if files:
            print(f"[FILES]: {files}")

        self._add_to_history("assistant", synthesis[:500])

        # Async LTM save
        if self.ltm:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.ltm.save_node("user", user_message, {"type": "question"}))
                loop.run_until_complete(self.ltm.save_node("agent", synthesis[:300], {"type": "response"}))
                loop.close()
            except Exception as e:
                logger.warning(f"LTM save bypassed: {e}")

        return {
            "response": synthesis,
            "files": files,
            "plan": self.current_plan.format_for_user() if self.current_plan else None
        }

    # ============================================================
    # SESSION UTILITIES
    # ============================================================

    def get_conversation_stats(self) -> dict:
        try:
            if self.conversation_memory:
                return self.conversation_memory.get_session_stats(self.session_id)
            return {"error": "Conversation memory offline"}
        except Exception as e:
            return {"error": str(e)}

    def clear_conversation(self):
        try:
            if self.conversation_memory:
                self.conversation_memory.clear_session(self.session_id)
        except:
            pass
        self.recent_history = []
        self.current_plan = None

    def switch_session(self, session_id: str):
        self.session_id = session_id
        try:
            if self.conversation_memory:
                self.recent_history = self.conversation_memory.get_last_n_interactions(session_id, n=5)
            else:
                self.recent_history = []
        except:
            self.recent_history = []
        self.current_plan = None