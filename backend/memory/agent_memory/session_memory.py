import sqlite3
import json
import os
import threading
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("MotherSystem.SessionMemory")

class SessionMemory:
    """
    Global session memory based on SQLite, thread-safe, multi-agent.
    Supports environment variables, browser cookies, 
    and data isolation by session type.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path="session_store.db", *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SessionMemory, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path="session_store.db"):
        if self._initialized:
            return
            
        self.db_path = db_path
        self.lock = threading.Lock()
        self.secret_keywords = ["key", "token", "password", "secret", "auth", "webhook", "cookie"]
        
        # SQL tables initialization
        self._init_db()
        self._initialized = True

    def _get_connection(self):
        """Creates an SQLite connection. timeout=20 handles concurrent writes by waiting its turn."""
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        return conn

    # ==========================================
    # COMPATIBILITY: CONNECTION EXPOSURE
    # ==========================================
    def get_connection(self):
        """
        Publicly exposes the SQLite connection retrieval method.
        Resolves the error: AttributeError: 'SessionMemory' object has no attribute 'get_connection'
        """
        return self._get_connection()

    def _init_db(self):
        """Creates the SQL structure if it does not exist."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Main table for generic session variables, by type (ex: 'browser', 'env', 'global')
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS session_variables (
                        session_type TEXT NOT NULL,       -- 'global', 'browser', 'env', 'custom_agent'
                        session_id TEXT NOT NULL,         -- Unique ID of the session or agent
                        key TEXT NOT NULL,                -- Variable name
                        value_json TEXT NOT NULL,         -- Value serialized in JSON
                        updated_by TEXT DEFAULT 'System',  -- Which agent wrote the info
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (session_type, session_id, key)
                    )
                """)
                
                # Index to optimize search during prompt injections
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_lookup ON session_variables(session_type, session_id)")
                conn.commit()
                logger.info("[SQL Memory] Session database initialized successfully.")

    # ==========================================
    # SYSTEM CORE: GET / SET SUITE TO SQL
    # ==========================================

    def set(self, session_type: str, session_id: str, key: str, value: Any, agent_id: str = "System"):
        """
        Stores or updates a variable in a thread-safe manner in a specific context.
        """
        value_json = json.dumps(value, ensure_ascii=False)
        with self.lock:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO session_variables (session_type, session_id, key, value_json, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(session_type, session_id, key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_by = excluded.updated_by,
                        updated_at = CURRENT_TIMESTAMP
                """, (session_type.lower(), session_id, key, value_json, agent_id))
                conn.commit()
                logger.info(f"[SQL Memory] [{session_type.upper()} / {session_id}] Variable '{key}' updated by [{agent_id}].")

    def get(self, session_type: str, session_id: str, key: str, default: Any = None) -> Any:
        """Retrieves a specific variable in a specific framework."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT value_json FROM session_variables 
                    WHERE session_type = ? AND session_id = ? AND key = ?
                """, (session_type.lower(), session_id, key))
                row = cursor.fetchone()
                if row:
                    return json.loads(row["value_json"])
                return default

    # ==========================================
    # SPECIFIC REQUEST MANAGEMENT (ENV, BROWSER)
    # ==========================================

    def set_env(self, key: str, value: str, agent_id: str = "System"):
        """Specific framework to load/save environment variables."""
        # Use ID 'global_env' because environment variables concern everyone
        self.set(session_type="env", session_id="global_env", key=key, value=value, agent_id=agent_id)

    def get_env_dict(self) -> Dict[str, str]:
        """Returns a standard Python dictionary to update os.environ."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value_json FROM session_variables WHERE session_type = 'env'")
                return {row["key"]: json.loads(row["value_json"]) for row in cursor.fetchall()}

    def set_browser_cookie(self, browser_session_id: str, domain: str, cookies_list: list, agent_id: str = "BrowserAgent"):
        """Specific framework to store the state (cookies/storage) of a web browser."""
        self.set(session_type="browser", session_id=browser_session_id, key=f"cookies:{domain}", value=cookies_list, agent_id=agent_id)

    # ==========================================
    # ADDITION: RESOLVING THE 'get_llm_view' BUG
    # ==========================================
    def get_llm_view(self, current_agent_id: str = "main", include_env: bool = False) -> str:
        """
        Returns the formatted and cleaned textual view of active session variables.
        This method resolves the critical AttributeError 'get_llm_view' encountered by the orchestrator.
        """
        return self.get_context_for_llm(current_agent_id=current_agent_id, include_env=include_env)

    # ==========================================
    # SECURE EXTRACTION FOR LLM PROMPTS
    # ==========================================
    def get_context_for_llm(self, current_agent_id: str, include_env: bool = False) -> str:
        """
        Generates a VERY STRICTLY isolated stringified JSON view for the LLM.
        Masking uses independent strings to prevent base replacement.
        """
        compiled_data = {}
        
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Retrieval of raw SQL rows
                cursor.execute("""
                    SELECT session_type, key, value_json FROM session_variables
                    WHERE (session_type = 'global' AND session_id = 'main')
                       OR (session_type = 'browser' AND session_id = ?)
                       OR (session_type = 'agent_private' AND session_id = ?)
                """, (current_agent_id, current_agent_id))
                
                rows = cursor.fetchall()
                
                if include_env:
                    cursor.execute("SELECT session_type, key, value_json FROM session_variables WHERE session_type = 'env'")
                    rows.extend(cursor.fetchall())

                if not rows:
                    return "No context data available for this session."

                for row in rows:
                    stype = row["session_type"]
                    key = row["key"]
                    
                    # ABSOLUTE SECURITY: Extract the value in an isolated manner
                    raw_val = json.loads(row["value_json"])
                    
                    if stype not in compiled_data:
                        compiled_data[stype] = {}
                        
                    # Anti-secret leak filtering WITHOUT overwriting the original RAM
                    if any(secret in key.lower() for secret in self.secret_keywords):
                        # Write the tag only in the text dictionary intended for the LLM
                        compiled_data[stype][key] = "[PROTECTED_SECRET_REDACTED_BY_SYSTEM]"
                    else:
                        compiled_data[stype][key] = raw_val
                        
                return json.dumps(compiled_data, indent=2, ensure_ascii=False)

    def delete(self, key: str, session_type: str = "env", session_id: str = "global_env", scope: Optional[str] = None) -> bool:
        """Properly deletes a key from the SQLite database by accepting session_type or scope."""
        # Automatic alignment if the caller uses 'scope' instead of 'session_type'
        final_type = scope if scope is not None else session_type
        
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM session_variables 
                    WHERE session_type = ? AND session_id = ? AND key = ?
                """, (final_type.lower(), session_id, key))
                conn.commit()
                return cursor.rowcount > 0

    def clear_all(self):
        """Completely empties the session database in a robust manner."""
        with self.lock:
            conn = None
            try:
                conn = self._get_connection()
                conn.isolation_level = None  # Disable autocommit to be able to execute VACUUM
                cursor = conn.cursor()
                
                # RECTIFICATION: Use 'session_variables' which is the real table name
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_variables'")
                if cursor.fetchone():
                    cursor.execute("DELETE FROM session_variables")
                    cursor.execute("VACUUM")
                    logger.info("[SQL Memory] Session data purged from the 'session_variables' table.")
                else:
                    logger.warning("[SQL Memory] The 'session_variables' table did not exist. Nothing to purge.")
                    
            except Exception as e:
                logger.error(f"[SQL Memory] Error purging tables: {e}")
            finally:
                if conn:
                    conn.close() # Immediate and explicit closure to free the file under Windows

            # 2. Force connection release by the Garbage Collector
            import gc
            gc.collect()
            
            # Micro-delay to let the operating system free the file descriptor
            import time
            time.sleep(0.15)

            # 3. Secure physical deletion of the file
            if os.path.exists(self.db_path):
                try:
                    os.remove(self.db_path)
                    logger.info("[SQL Memory] SQLite base file deleted from disk.")
                except IOError as e:
                    logger.error(f"[SQL Memory] Cannot delete the physical file: {e}")
        # ==========================================
    # NEW: DATA SHARING BETWEEN AGENTS
    # ==========================================

    def save_shared_data(self, key: str, data: dict, agent_id: str = "System"):
        """
        Saves shared data between agents.
        Uses session_type='shared' and session_id='global'
        """
        self.set(
            session_type="shared", 
            session_id="global", 
            key=key, 
            value=data, 
            agent_id=agent_id
        )
        logger.info(f"[Shared] Data '{key}' saved by [{agent_id}]")

    def get_shared_data(self, key: str, default: Any = None) -> Any:
        """
        Retrieves shared data between agents.
        """
        return self.get(
            session_type="shared", 
            session_id="global", 
            key=key, 
            default=default
        )

    def clear_shared_data(self, key: str = None):
        """
        Clears shared data.
        If key is None, clears all shared data.
        """
        with self.lock:
            with self._get_connection() as conn:
                if key:
                    conn.execute("""
                        DELETE FROM session_variables 
                        WHERE session_type = 'shared' AND session_id = 'global' AND key = ?
                    """, (key,))
                    logger.info(f"[Shared] Data '{key}' cleared")
                else:
                    conn.execute("""
                        DELETE FROM session_variables 
                        WHERE session_type = 'shared' AND session_id = 'global'
                    """)
                    logger.info("[Shared] All shared data cleared")
                conn.commit()

    def get_shared_context_for_llm(self) -> str:
        """
        Retrieves all shared data formatted for the LLM.
        """
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT key, value_json FROM session_variables 
                    WHERE session_type = 'shared' AND session_id = 'global'
                """)
                rows = cursor.fetchall()
                
                if not rows:
                    return "No shared data available."
                
                context = "**SHARED DATA BETWEEN AGENTS:**\n"
                for row in rows:
                    key = row["key"]
                    value = json.loads(row["value_json"])
                    context += f"\n**{key}:**\n{json.dumps(value, indent=2, ensure_ascii=False)[:1000]}\n"
                
                return context
if __name__ == "__main__":
    # Quick configuration of clean log display in the console
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    print("\n" + "="*60)
    print("STARTING UNIT AND INTEGRATION TESTS - SESSIONMEMORY")
    print("="*60 + "\n")

    # 1. Singleton Pattern Test (Unique instance)
    db_name = "test_session_store.db"
    
    # Force deletion of any possible old test database
    if os.path.exists(db_name):
        try: os.remove(db_name)
        except: pass

    memory_instance_1 = SessionMemory(db_path=db_name)
    memory_instance_2 = SessionMemory(db_path=db_name)
    
    # Integrity assertions
    assert memory_instance_1 is memory_instance_2, "FAILURE: The Singleton did not return the same instance!"
    print("SUCCESS: Singleton Pattern validated.")

    # 2. Basic writes and reads
    memory_instance_1.set(session_type="global", session_id="main", key="user_greet", value="hello", agent_id="MotherAgent")
    val = memory_instance_2.get(session_type="global", session_id="main", key="user_greet")
    assert val == "hello", f"FAILURE: Expected value 'hello', received '{val}'"
    print("SUCCESS: Read/Write validated.")

    # 3. Test of get_llm_view and get_connection
    view = memory_instance_1.get_llm_view(current_agent_id="main")
    assert "user_greet" in view, "FAILURE: The LLM view did not include the global variable."
    print("SUCCESS: Compatibility method 'get_llm_view' validated.")

    conn_test = memory_instance_1.get_connection()
    assert isinstance(conn_test, sqlite3.Connection), "FAILURE: get_connection() did not return an SQLite object."
    conn_test.close()
    print("SUCCESS: Compatibility method 'get_connection' validated.")

    # 4. Final cleanup
    print("\n[Final TEST] Cleanup and session deletion...")
    memory_instance_1.clear_all()
    assert os.path.exists(db_name) is False, "FAILURE: The database file was not deleted by clear_all()."
    print("SUCCESS: Database cleaned from hard drive.\n")

    print("="*60)
    print("ALL TESTS PASSED SUCCESSFULLY (100% OK)!")
    print("="*60)