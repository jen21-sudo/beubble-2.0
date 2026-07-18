import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger("WorkingMemory")

class WorkingMemory:
    """
    Dynamic and Physical State Memory dedicated to the Terminal Agent.
    Manages the lifecycle of asynchronous tasks and the state of real network ports.
    Avoids loops and amnesia from previous rounds.
    """
    
    def __init__(self):
        self.objective: str = ""
        self.facts: Dict[str, Any] = {
            "operating_system": "Unknown",
            "active_network_ports": {},  # ex: {"8000": "occupied by uvicorn"}
            "active_tasks": {}       # ex: {"task_id": "associated_command"}
        }
        self.history: List[Dict[str, Any]] = []
        
        self.status = {
            "actions_succeeded": [],  # Pure list of successful actions
            "actions_failed": [],     # Pure list of failed actions
            "last_action": None,      # Dictionary of the last executed action
            "errors_logs": []         # Textual register of raw failures
        }

    def set_objective(self, objective: str):
        """Initializes the main objective of the mission."""
        self.objective = objective.strip()
        logger.info(f"[Memory] Objective set: {self.objective[:50]}...")

    def set_os(self, os_name: str):
        """Records the detected OS to adapt commands."""
        self.facts["operating_system"] = os_name

    def add_active_port(self, port: str, service_name: str):
        """Declares a network port as occupied."""
        self.facts["active_network_ports"][str(port)] = service_name
        logger.info(f"[Memory] Port {port} marked as OCCUPIED ({service_name})")

    def remove_active_port(self, port: str):
        """Frees a network port from memory."""
        if str(port) in self.facts["active_network_ports"]:
            del self.facts["active_network_ports"][str(port)]
            logger.info(f"[Memory] Port {port} marked as FREE")

    def add_active_task(self, task_id: str, command: str):
        """Adds an active background task."""
        self.facts["active_tasks"][task_id] = command

    def remove_active_task(self, task_id: str):
        """Removes an asynchronous task (whether completed or killed)."""
        if task_id in self.facts["active_tasks"]:
            del self.facts["active_tasks"][task_id]

    def add_action(self, action: str, result: str = "success", details: str = ""):
        """Records the execution of a direct action (File, Tool, Command)."""
        action_clean = action.strip()
        entry = {
            "action": action_clean,
            "result": result.lower(),
            "details": details.strip(),
            "timestamp": datetime.now().isoformat()
        }
        self.history.append(entry)
        self.status["last_action"] = entry

        if "success" in entry["result"]:
            if action_clean not in self.status["actions_succeeded"]:
                self.status["actions_succeeded"].append(action_clean)
            # If it finally succeeds, clean up any old similar failure reports
            if action_clean in self.status["actions_failed"]:
                self.status["actions_failed"].remove(action_clean)
        else:
            if action_clean not in self.status["actions_failed"]:
                self.status["actions_failed"].append(action_clean)
            if entry["details"]:
                self.status["errors_logs"].append(
                    f"CRASH ON ACTION: [{action_clean}]\nREAL SYSTEM RETURN TIMEOUT/STDERR:\n{entry['details']}"
                )

    def update_background_task_failure(self, action_command: str, error_details: str):
        """
        Forces the reclassification of a successful launch into a Real Failure 
        after an asynchronous crash has been detected when reading the logs.
        """
        action_clean = action_command.strip()
        
        # 1. Remove from successes
        if action_clean in self.status["actions_succeeded"]:
            self.status["actions_succeeded"].remove(action_clean)
            
        # 2. Firmly add to failures
        if action_clean not in self.status["actions_failed"]:
            self.status["actions_failed"].append(action_clean)
            
        # 3. Direct injection of the real error log
        error_msg = f"ASYNCHRONOUS CRASH DETECTED ON: [{action_clean}]\nREAL TERMINAL LOG STREAM:\n{error_details.strip()}"
        if error_msg not in self.status["errors_logs"]:
            self.status["errors_logs"].append(error_msg)
            
        logger.warning(f"[Memory] State updated following an asynchronous crash for: {action_clean}")

    def get_context(self) -> str:
        """Generates the complete dynamic context block for the system prompt."""
        context_blocks = [f"GLOBAL MISSION OBJECTIVE: {self.objective}"]

        # 1. Physical system state
        active_ports = self.facts["active_network_ports"]
        active_tasks = self.facts["active_tasks"]
        
        sys_state = [f"  - Detected OS: {self.facts['operating_system']}"]
        if active_ports:
            ports_str = ", ".join([f"Port {p} ({srv})" for p, srv in active_ports.items()])
            sys_state.append(f"  - Occupied ports: {ports_str}")
        else:
            sys_state.append("  - Network ports: No port currently in use by your tasks.")
            
        if active_tasks:
            tasks_str = ", ".join([f"[{tid}] {cmd}" for tid, cmd in active_tasks.items()])
            sys_state.append(f"  - Tracked background tasks: {tasks_str}")
        
        context_blocks.append("PHYSICAL ENVIRONMENT STATE:\n" + "\n".join(sys_state))

        # 2. Definitive successes section
        if self.status["actions_succeeded"]:
            succeeded_str = "\n".join([f"  - {act}" for act in self.status["actions_succeeded"]])
            context_blocks.append(
                f"SUCCESSFUL STEPS AND COMMANDS (NO NEED TO REDO THEM UNLESS THE SYSTEM HAS CHANGED):\n{succeeded_str}"
            )

        # 3. Last direct feedback
        last = self.status["last_action"]
        if last:
            context_blocks.append(
                f"REAL RESULT OF YOUR VERY LAST ACTION:\n"
                f"  - Attempted action: {last['action']}\n"
                f"  - Result: {last['result'].upper()}\n"
                f"  - Console output (excerpt): {last['details']}"
            )

        # 4. Real error register (the last 3 max to avoid context pollution)
        if self.status["errors_logs"]:
            errors_str = "\n\n".join(self.status["errors_logs"][-3:])
            context_blocks.append(
                f"CALL FOR CORRECTION: SYSTEM ERRORS ENCOUNTERED THAT MUST ABSOLUTELY BE AVOIDED OR CORRECTED:\n{errors_str}"
            )

        return "\n\n".join(context_blocks)
    def get_llm_view(self) -> Dict[str, Any]:
        """
        Returns a structured view for the Mother Agent.
        Version compatible with the interface expected by MotherAgent.
        """
        return {
            "objective": self.objective,
            "facts": self.facts,
            "history": self.history,
            "status": {
                "actions_succeeded": self.status["actions_succeeded"],
                "actions_failed": self.status["actions_failed"],
                "last_action": self.status["last_action"],
                "errors_logs": self.status["errors_logs"][-5:]  # Last 5 errors
            },
            "executed_commands": [a["action"] for a in self.history if a["result"] == "success"],
            "failed_commands": [a["action"] for a in self.history if a["result"] != "success"],
            "summary": {
                "total_actions": len(self.history),
                "successful": len(self.status["actions_succeeded"]),
                "failed": len(self.status["actions_failed"])
            }
        }