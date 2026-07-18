import os
import sys
import platform
import subprocess
import threading
import uuid
import logging
import shutil
import time
from typing import Dict, Any, Tuple, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TerminalDriver")

class TerminalDriver:
    """
    Advanced Terminal Driver for AI Agent (Claude Code / Hermes style).
    Manages environment persistence, asynchronous background tasks,
    security and context anti-saturation.
    """
    
    def __init__(self):
        # Persistence of the current working directory
        self.current_dir = os.getcwd()
        
        # Persistence and copy of system environment variables
        self.environment = dict(os.environ)
        
        # Asynchronous background task manager
        self.background_tasks: Dict[str, Dict[str, Any]] = {}
        
        # List of strictly forbidden interactive commands at startup
        self.forbidden_commands = ["nano", "vim", "vi", "emacs", "top", "htop", "ssh", "ftp"]

    def get_environment_info(self) -> Dict[str, Any]:
        """Returns the fingerprint with real verification of Python modules"""
        import platform
        import shutil
        import subprocess

        system_os = platform.system()
        
        if system_os == "Windows":
            shell_active = "powershell.exe" if shutil.which("powershell.exe") else "cmd.exe"
            username = os.environ.get("USERNAME", "Unknown")
        else:
            shell_active = os.environ.get("SHELL", "/bin/bash")
            username = os.environ.get("USER", "Unknown")

        # REAL VERIFICATION OF PYTHON MODULES
        # We directly ask Python if the package is importable
        python_modules = ["pytest", "requests", "playwright", "fastapi"]
        installed_modules = {}
        
        for module in python_modules:
            try:
                # Execute a silent subprocess to test the import
                res = subprocess.run(
                    f'python -c "import {module}"', 
                    shell=True, 
                    capture_output=True
                )
                installed_modules[module] = (res.returncode == 0)
            except Exception:
                installed_modules[module] = False

        # Global system tools
        global_tools = ["git", "docker", "node", "npm", "curl"]
        installed_tools = {tool: shutil.which(tool) is not None for tool in global_tools}

        return {
            "os": system_os,
            "os_release": platform.release(),
            "active_shell": shell_active,
            "current_user": username,
            "initial_working_directory": self.current_dir,
            # Merge global tools and real Python modules
            "available_tools": {**installed_tools, **installed_modules},
            "python_version": platform.python_version()
        }


    def _truncate_output(self, text: str, max_lines: int = 60, max_chars: int = 4000) -> str:
        """
        [INTERNAL FUNCTION] Prevents the LLM context window from exploding.
        If logs are huge, keeps the first 30 lines and the last 30.
        """
        if not text:
            return ""
            
        lines = text.splitlines()
        if len(lines) <= max_lines and len(text) <= max_chars:
            return text

        logger.warning(f"Log too large ({len(lines)} lines). Semantic truncation applied.")
        
        half_max = max_lines // 2
        first_part = "\n".join(lines[:half_max])
        last_part = "\n".join(lines[-half_max:])
        truncated_count = len(lines) - max_lines
        
        return f"{first_part}\n\n[... SEMANTIC OMISSION: {truncated_count} log lines were truncated by the Driver to avoid context saturation ...]\n\n{last_part}"

    def execute_sync(self, command_str: str, timeout: float = 30.0) -> Tuple[str, int]:
        """
        [FUNCTION 2] Executes a standard synchronous command in a straight line.
        Maintains the working directory state (cwd) across successive calls.
        """
        command_str = command_str.strip()
        if not command_str:
            return "", 0

        # 1. Input security validation
        first_word = command_str.split()[0].lower() if command_str.split() else ""
        if first_word in self.forbidden_commands:
            return f"Error: The interactive command '{first_word}' is forbidden in this mode.", 1

        # 2. Native and semantic interception of 'cd' directory change
        if command_str.startswith("cd "):
            target_dir = command_str[3:].strip().strip('"').strip("'")
            if target_dir == "~":
                target_dir = os.path.expanduser("~")
            
            potential_path = os.path.abspath(os.path.join(self.current_dir, target_dir))
            if os.path.exists(potential_path) and os.path.isdir(potential_path):
                self.current_dir = potential_path
                return f"Working directory changed to: {self.current_dir}", 0
            else:
                return f"Error: The directory '{target_dir}' does not exist.", 1

        # 3. Physical execution via Subprocess
        try:
            process = subprocess.run(
                command_str,
                shell=True,
                cwd=self.current_dir,
                env=self.environment,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Intelligent merging of output and error streams
            combined_logs = process.stdout if process.stdout else ""
            if process.stderr:
                if combined_logs:
                    combined_logs += "\n"
                combined_logs += f"[STDERR]\n{process.stderr}"

            # Cleanup and log size limitation
            safe_logs = self._truncate_output(combined_logs.strip())
            return safe_logs, process.returncode

        except subprocess.TimeoutExpired:
            return f"Error: The command exceeded the execution time limit of {timeout}s (Timeout).", -1
        except Exception as e:
            return f"Fatal system driver error: {str(e)}", -2

    def execute_background(self, command_str: str) -> str:
        """
        [FUNCTION 3] Launches a heavy process as a background task (ex: web server, async script).
        Generates a unique ID and isolates execution to avoid freezing the main system.
        """
        command_str = command_str.strip()
        task_id = str(uuid.uuid4())[:8] # Short and readable ID for the agent
        
        logger.info(f"[Background] Launching task [{task_id}]: {command_str}")

        # Automatic non-interactive environment configuration
        # (Injects the standard non-interaction argument under Linux/Mac)
        modified_env = dict(self.environment)
        modified_env["DEBIAN_FRONTEND"] = "noninteractive"

        try:
            # Asynchronous launch without blocking (stdout and stderr redirected to a pipe)
            process = subprocess.Popen(
                command_str,
                shell=True,
                cwd=self.current_dir,
                env=modified_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1, # Line-buffered streaming
                universal_newlines=True
            )

            # Storage structure for the active task
            self.background_tasks[task_id] = {
                "id": task_id,
                "command": command_str,
                "process": process,
                "logs": [],
                "started_at": time.time(),
                "status": "running"
            }

            # Launch lightweight sub-threads to continuously collect logs without blocking
            threading.Thread(target=self._stream_reader, args=(process.stdout, task_id), daemon=True).start()
            threading.Thread(target=self._stream_reader, args=(process.stderr, task_id, "[STDERR]"), daemon=True).start()

            return task_id

        except Exception as e:
            logger.error(f"Background task instantiation failed: {e}")
            return f"ERROR: {str(e)}"

    def _stream_reader(self, pipe, task_id: str, prefix: str = ""):
        """[INTERNAL FUNCTION] Continuously consumes the output stream and records it."""
        if not pipe:
            return
        try:
            for line in iter(pipe.readline, ""):
                if task_id in self.background_tasks:
                    log_line = f"{prefix} {line.strip()}".strip()
                    self.background_tasks[task_id]["logs"].append(log_line)
            pipe.close()
        except Exception:
            pass

    def list_background_tasks(self) -> list:
        """
        [FUNCTION 4] Returns the current and dynamic state of all background processes.
        """
        cleaned_list = []
        for task_id, task in list(self.background_tasks.items()):
            # Check the actual process status
            poll_status = task["process"].poll()
            if poll_status is None:
                task["status"] = "running"
            else:
                task["status"] = f"finished (exit code: {poll_status})"

            cleaned_list.append({
                "task_id": task_id,
                "command": task["command"],
                "status": task["status"],
                "execution_time_seconds": round(time.time() - task["started_at"], 1)
            })
        return cleaned_list

    def get_task_logs(self, task_id: str) -> str:
        """
        [FUNCTION 5] Allows the agent to read on the fly the accumulated logs of an asynchronous task.
        """
        if task_id not in self.background_tasks:
            return f"Error: The background task [{task_id}] does not exist."
            
        compiled_logs = "\n".join(self.background_tasks[task_id]["logs"])
        if not compiled_logs:
            return f"[Task {task_id}] No log output generated yet."
            
        return self._truncate_output(compiled_logs)

    def kill_task(self, task_id: str) -> bool:
        """
        [FUNCTION 6] Elite kill-switch: Cleanly and forcefully eliminates a process 
        and ALL its child process tree (avoids blocked ports and ghost processes).
        """
        if task_id not in self.background_tasks:
            logger.warning(f"Invalid termination request for task [{task_id}] (non-existent ID).")
            return False

        task = self.background_tasks[task_id]
        process = task["process"]
        pid = process.pid

        # If the process is already dead, no need to go further
        if process.poll() is not None:
            logger.info(f"Task [{task_id}] (PID: {pid}) already stopped.")
            task["status"] = f"finished (exit code: {process.poll()})"
            return False

        logger.info(f"[Kill-Switch] Destroying process tree for task [{task_id}] (Parent PID: {pid})")
        
        try:
            if platform.system() == "Windows":
                # /T kills the specified process and all its child processes (the complete tree)
                # /F forces termination
                subprocess.run(
                    f"taskkill /F /T /PID {pid}", 
                    shell=True, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
            else:
                # Under Linux/Mac, we try to kill the process group (PGID)
                # First use pkill -P to eliminate direct children
                subprocess.run(
                    f"pkill -P {pid}", 
                    shell=True, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
                # Then cleanly terminate the parent
                process.terminate()
                try:
                    process.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    # In case of resistance, brute force (SIGKILL)
                    process.kill()
            
            task["status"] = "killed"
            logger.info(f"Task [{task_id}] (PID: {pid}) and its dependencies have been eliminated.")
            return True

        except Exception as e:
            logger.error(f"Error killing task [{task_id}] (PID: {pid}): {e}")
            # Fallback to the basic native method if the system command fails
            try:
                process.kill()
                task["status"] = "killed"
                return True
            except Exception:
                return False

if __name__ == "__main__":
    driver = TerminalDriver()
    
    # 1. Environment perception test
    print("\n--- TEST 1: ENVIRONMENT MAP ---")
    info = driver.get_environment_info()
    print(f"Detected system: {info['os']}")
    print(f"User: {info['current_user']}")
    print(f"Available tools: {info['available_tools']}")

    # 2. Simple synchronous execution test
    print("\n--- TEST 2: SIMPLE SYNCHRONOUS COMMAND ---")
    logs, code = driver.execute_sync("git --version" if info['os'] != "Windows" else "echo 'Hello World'")
    print(f"Exit code: {code}\nLogs:\n{logs}")

    # 3. Working directory persistence test (The classic trap)
    print("\n--- TEST 3: DIRECTORY CHANGE PERSISTENCE ---")
    driver.execute_sync("cd ..")
    logs, code = driver.execute_sync("pwd" if info['os'] != "Windows" else "Get-Location")
    print(f"New persistent directory: {logs.strip()}")

    # 4. Asynchronous command test (Background task)
    print("\n--- TEST 4: BACKGROUND PROCESS ---")
    # Simulate a continuous ping or a waiting loop depending on the OS
    cmd = "ping 127.0.0.1 -c 5" if info['os'] != "Windows" else "ping 127.0.0.1 -n 5"
    task_id = driver.execute_background(cmd)
    print(f"Asynchronous task launched with ID: {task_id}")
    
    # Wait 2 seconds and read the logs on the fly
    time.sleep(2)
    print(f"\nReading active tasks: {driver.list_background_tasks()}")
    print(f"\nLogs captured on the fly:\n{driver.get_task_logs(task_id)}")
    
    # Prematurely stop the background process via the Kill-switch
    driver.kill_task(task_id)
    print(f"\nFinal status after Kill: {driver.list_background_tasks()}")