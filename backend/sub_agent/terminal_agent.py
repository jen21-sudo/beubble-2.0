# sub_agent/terminal_agent.py - Version corrigée avec workspace_dir et config

import sys
import os

# 1. Dynamically go back to the parent root folder ("beubble 2.0")
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 2. Add it to Python's search path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import json
import logging
import asyncio
from datetime import datetime
from typing import Optional
from AI_models.qwen.qwen_version import UniversalAgent
from driver.terminal_driver import TerminalDriver
from memory.agent_memory.working_memo import WorkingMemory
from memory.agent_memory.session_memory import SessionMemory
from driver.file_driver import FileDriver

# Import config for centralized paths
from config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TerminalAgent")

class TerminalAgent:
    """Elite autonomous agent - TOUJOURS dans le workspace"""
    
    def __init__(self, workspace_dir: Optional[str] = None):
        self.llm = UniversalAgent()
        self.driver = TerminalDriver()
        self.is_completed = False
        self.memory = WorkingMemory()
        
        # ============================================================
        # 🔥 GESTION DU WORKSPACE - AVEC CONFIG
        # ============================================================
        
        if workspace_dir:
            # Utiliser le workspace passé en paramètre (priorité)
            self.workspace_dir = os.path.abspath(workspace_dir)
            logger.info(f"[Workspace] Using provided workspace: {self.workspace_dir}")
        elif hasattr(config, 'WORKSPACE_DIR'):
            # Utiliser le workspace de config
            self.workspace_dir = str(config.WORKSPACE_DIR)
            logger.info(f"[Workspace] Using config workspace: {self.workspace_dir}")
        else:
            # Fallback: calcul automatique (comportement original)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.workspace_dir = os.path.join(base_dir, "workspace")
            self.workspace_dir = os.path.abspath(self.workspace_dir)
            logger.info(f"[Workspace] Workspace auto-calculated: {self.workspace_dir}")
        
        # Créer le workspace avec tous les droits
        os.makedirs(self.workspace_dir, exist_ok=True)
        
        # 🔥 FORCER le FileDriver à utiliser UNIQUEMENT ce chemin
        self.file_driver = FileDriver(self.workspace_dir)
        
        # 🔥 FORCER le TerminalDriver dans ce répertoire
        self.driver.current_dir = self.workspace_dir
        
        # ⚠️ NE PAS FORCER os.chdir() - Évite les problèmes de répertoire courant
        # os.chdir(self.workspace_dir)  # À COMMENTER
        
        # 🔥 STOCKER dans une variable de classe pour accès global
        TerminalAgent.WORKSPACE = self.workspace_dir
        
        # 🔥 OVERRIDE des méthodes de FileDriver pour garantir le workspace
        original_write = self.file_driver.write_file
        original_read = self.file_driver.read_file
        
        def workspace_write(filepath, content):
            """Forcer l'écriture dans le workspace"""
            if not os.path.isabs(filepath):
                filepath = os.path.join(self.workspace_dir, filepath)
            return original_write(filepath, content)
        
        def workspace_read(filepath):
            """Forcer la lecture dans le workspace"""
            if not os.path.isabs(filepath):
                filepath = os.path.join(self.workspace_dir, filepath)
            return original_read(filepath)
        
        self.file_driver.write_file = workspace_write
        self.file_driver.read_file = workspace_read
        
        logger.info(f"✅ [TERMINAL AGENT] Workspace FORCED: {self.workspace_dir}")
        logger.info(f"✅ [TERMINAL AGENT] Driver current_dir: {self.driver.current_dir}")
        logger.info(f"✅ [TERMINAL AGENT] FileDriver root: {self.file_driver.workspace_root}")
        
        # Environment fingerprint
        self.env_info = self.driver.get_environment_info()
        self.memory.set_os(self.env_info['os'])
        
        logger.info(f"[Scanner] OS: {self.env_info['os']} | User: {self.env_info['current_user']}")
        logger.info(f"[Scanner] Tools: {self.env_info['available_tools']}")
    
    def _ensure_workspace(self):
        """🔥 Vérification et correction automatique du workspace"""
        # Vérifier le FileDriver
        if self.file_driver.workspace_root != self.workspace_dir:
            logger.warning(f"⚠️ FileDriver corrected: {self.file_driver.workspace_root} -> {self.workspace_dir}")
            self.file_driver.workspace_root = self.workspace_dir
        
        # Vérifier le TerminalDriver
        if self.driver.current_dir != self.workspace_dir:
            logger.warning(f"⚠️ TerminalDriver corrected: {self.driver.current_dir} -> {self.workspace_dir}")
            self.driver.current_dir = self.workspace_dir
        
        # NE PAS forcer os.chdir() - Évite les problèmes
        # if os.getcwd() != self.workspace_dir:
        #     logger.warning(f"⚠️ Process CWD corrigé: {os.getcwd()} -> {self.workspace_dir}")
        #     os.chdir(self.workspace_dir)
        
        # Vérifier que le workspace existe
        if not os.path.exists(self.workspace_dir):
            os.makedirs(self.workspace_dir, exist_ok=True)
            logger.info(f"✅ Workspace recreated: {self.workspace_dir}")

    def _build_system_prompt(self, current_dir: str) -> str:
        """Builds the system prompt - TOUJOURS avec le workspace"""
        
        # 🔥 Forcer l'utilisation du workspace
        current_dir = self.workspace_dir
        
        tools_status = ", ".join([tool for tool, status in self.env_info['available_tools'].items() if status])
        cartography = self.file_driver.get_folder_cartography()
        active_tasks = self.driver.list_background_tasks()
        
        return f"""You are an Elite System Agent. You MUST create ALL files in: {self.workspace_dir}

⚠️ CRITICAL: All file paths MUST be relative to {self.workspace_dir}
Example: "app.py" not "C:/Users/.../app.py"

WORKSPACE: {self.workspace_dir}
Current directory: {current_dir}

WORKING MEMORY:
{self.memory.get_context()}

WORKSPACE STATE:
- Tree structure: {json.dumps(cartography, ensure_ascii=False)}
- Installed tools: {tools_status}

BACKGROUND TASKS:
{json.dumps(active_tasks, indent=2) if active_tasks else "No active background tasks."}

INSTRUCTIONS:
1. ALL files are created in: {self.workspace_dir}
2. Use relative paths ONLY (ex: "app.py", "website/index.html")
3. The workspace is ALREADY the current directory
4. Do NOT use absolute paths
5. All WRITE_FILE operations go to: {self.workspace_dir}

TOOLBOX:
1. "WRITE_FILE": Create file in workspace
   - "command": "relative/path/file.py"
   - "file_content": "code here"

2. "READ_FILE": Read from workspace
   - "command": "relative/path/file.py"

3. "SEARCH_IN_FILES": Search in workspace

4. "SYNC": Execute command in workspace

5. "BACKGROUND": Launch task in workspace

6. "READ_TASK_LOGS": Read task logs

7. "KILL_TASK": Stop task

8. "FINISH": End mission

Generate ONLY JSON:
{{
    "analysis": "Analysis",
    "operation": "WRITE_FILE | READ_FILE | SEARCH_IN_FILES | SYNC | BACKGROUND | READ_TASK_LOGS | KILL_TASK | FINISH",
    "command": "command",
    "file_content": "content (only for WRITE_FILE)"
}}"""

    async def run_mission(self, objective: str, max_steps: int = 15):
        """Main ReAct control loop - TOUJOURS dans le workspace"""
        
        # 🔥 FORCER le workspace au début
        self._ensure_workspace()
        
        logger.info(f"🚀 Terminal mission: {objective}")
        logger.info(f"📁 Workspace FORCED: {self.workspace_dir}")
        
        self.memory.set_objective(objective)
        current_dir = self.workspace_dir  # 🔥 TOUJOURS le workspace

        for step in range(max_steps):
            if self.is_completed:
                logger.info("Mission completed.")
                break
            
            # 🔥 Vérifier à chaque itération
            self._ensure_workspace()
            
            logger.info(f"[Round {step + 1}/{max_steps}] Agent Reflection...")

            # Decision
            prompt = self._build_system_prompt(current_dir)
            decision = self.llm.execute(prompt)
            
            logger.info(f"Agent Analysis: {decision.get('analysis', '')}")
            
            op = decision.get("operation", "FINISH")
            command = decision.get("command")
            file_content = decision.get("file_content", "")

            # Stop condition
            if op == "FINISH" or not command:
                logger.info("Mission ended by agent.")
                self.memory.add_action("FINISH", "success", "Mission validated.")
                self.is_completed = True
                break

            # Routing
            logs = ""
            exit_code = 0
            
            # --- FILE ACTIONS (FORCÉES dans workspace) ---
            if op == "WRITE_FILE":
                # 🔥 FORCER le chemin dans le workspace
                if not os.path.isabs(command):
                    full_path = os.path.join(self.workspace_dir, command)
                else:
                    full_path = command
                
                logger.info(f"[WRITE_FILE] Creating in workspace: {full_path}")
                logs, exit_code = self.file_driver.write_file(full_path, file_content)
                status = "success" if exit_code == 0 else "failure"
                self.memory.add_action(action=f"Writing {command}", result=status, details=logs)

            elif op == "READ_FILE":
                # 🔥 FORCER la lecture dans le workspace
                if not os.path.isabs(command):
                    full_path = os.path.join(self.workspace_dir, command)
                else:
                    full_path = command
                
                logger.info(f"[READ_FILE] Reading from workspace: {full_path}")
                logs, exit_code = self.file_driver.read_file(full_path)
                status = "success" if exit_code == 0 else "failure"
                self.memory.add_action(action=f"Reading {command}", result=status, details=logs[:400])

            elif op == "SEARCH_IN_FILES":
                logger.info(f"[SEARCH_IN_FILES] Searching in workspace: {command}")
                logs, exit_code = self.file_driver.search_in_files(command)
                status = "success" if exit_code == 0 else "failure"
                self.memory.add_action(action=f"Grep '{command}'", result=status, details=logs[:400])

            # --- TERMINAL ACTIONS (FORCÉES dans workspace) ---
            elif op == "SYNC":
                # 🔥 FORCER l'exécution dans le workspace
                original_dir = self.driver.current_dir
                self.driver.current_dir = self.workspace_dir
                
                logger.info(f"[SYNC EXEC] In workspace: {command}")
                logs, exit_code = self.driver.execute_sync(command)
                
                # 🔥 Remettre dans le workspace
                self.driver.current_dir = self.workspace_dir
                self.file_driver.workspace_root = self.workspace_dir
                
                # Sauvegarde
                if exit_code == 0:
                    clean_output = logs.strip()
                    if clean_output:
                        try:
                            session = SessionMemory()
                            session.save_shared_data("terminal_result", {
                                "command": command,
                                "output": clean_output,
                                "exit_code": exit_code,
                                "executed_at": datetime.now().isoformat()
                            })
                            logger.info(f"[Shared] Terminal result saved: {clean_output[:100]}...")
                        except Exception as e:
                            logger.warning(f"⚠️ DB save error: {e}")
                        
                        self.memory.add_action(action=command, result="success", details=clean_output[:400])
                    else:
                        self.memory.add_action(action=command, result="failure", details="Empty output")
                else:
                    self.memory.add_action(action=command, result="failure", details=logs)

            elif op == "BACKGROUND":
                # 🔥 FORCER le background dans le workspace
                self.driver.current_dir = self.workspace_dir
                
                logger.info(f"[BACKGROUND] In workspace: {command}")
                task_id = self.driver.execute_background(command)
                await asyncio.sleep(1.0)
                
                if task_id.startswith("ERROR:"):
                    self.memory.add_action(action=command, result="failure", details=task_id)
                    logs, exit_code = task_id, -1
                else:
                    self.memory.add_active_task(task_id, command)
                    if "8000" in command:
                        self.memory.add_active_port("8000", "FastAPI / Uvicorn")
                    self.memory.add_action(action=command, result="success", details=f"Task ID: {task_id}")
                    logs, exit_code = f"Async task started. ID: {task_id}", 0

            elif op == "READ_TASK_LOGS":
                logger.info(f"[READ_TASK_LOGS] Task: {command}")
                logs = self.driver.get_task_logs(command)
                active_tasks_ids = [t["task_id"] for t in self.driver.list_background_tasks()]
                is_still_running = command in active_tasks_ids
                has_critical_error = ("is not recognized" in logs or "Traceback" in logs) and not is_still_running
                
                if has_critical_error:
                    exit_code = 1
                    task_command = self.memory.facts["active_tasks"].get(command, f"Task {command}")
                    self.memory.update_background_task_failure(task_command, logs)
                    self.memory.remove_active_task(command)
                    self.memory.remove_active_port("8000")
                else:
                    exit_code = 0
                    self.memory.add_action(action=f"Reading logs of {command}", result="success", details=logs[:400])

            elif op == "KILL_TASK":
                logger.info(f"[KILL_TASK] Stopping: {command}")
                success = self.driver.kill_task(command)
                if success:
                    logs = f"Task [{command}] stopped."
                    exit_code = 0
                    self.memory.remove_active_task(command)
                    self.memory.remove_active_port("8000")
                else:
                    logs = f"Failed to stop task [{command}]."
                    exit_code = 1
                self.memory.add_action(action=f"Kill task {command}", result="success" if success else "failure", details=logs)

            print(f"\n[CONSOLE OUTPUT (Code: {exit_code})]:\n{logs}\n" + "-"*40)
            await asyncio.sleep(0.5)

        logger.info(f"✅ Mission completed. All files are in: {self.workspace_dir}")