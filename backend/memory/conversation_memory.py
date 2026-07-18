# memory/conversation_memory.py
import os
import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("MotherSystem.ConversationMemory")

class ConversationMemory:
    """
    Mémoire persistante des conversations.
    Stocke l'historique des interactions même après fermeture.
    """
    
    def __init__(self, db_path: str = "conversation_memory.db"):
        self.db_path = db_path
        self.max_history = 10  # Nombre d'interactions à garder en mémoire
        self._init_db()
    
    def _init_db(self):
        """Initialise la base de données SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des conversations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        ''')
        
        # Table des sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                context TEXT
            )
        ''')
        
        # Index pour les recherches rapides
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_timestamp 
            ON conversations(session_id, timestamp DESC)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Conversation memory initialized at {self.db_path}")
    
    def get_or_create_session(self, session_id: str = None) -> str:
        """Récupère ou crée une session."""
        if session_id is None:
            # Générer un ID de session basé sur la date
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vérifier si la session existe
        cursor.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            # Créer une nouvelle session
            cursor.execute(
                "INSERT INTO sessions (session_id, created_at, last_updated) VALUES (?, ?, ?)",
                (session_id, datetime.now().isoformat(), datetime.now().isoformat())
            )
            conn.commit()
            logger.info(f"📝 New session created: {session_id}")
        
        conn.close()
        return session_id
    
    def add_interaction(self, session_id: str, role: str, content: str, metadata: dict = None):
        """Ajoute une interaction à l'historique."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute(
            """INSERT INTO conversations 
               (session_id, role, content, timestamp, metadata) 
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, role, content, timestamp, metadata_json)
        )
        
        # Mettre à jour la session
        cursor.execute(
            "UPDATE sessions SET last_updated = ? WHERE session_id = ?",
            (timestamp, session_id)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"💬 Interaction added: {role} ({len(content)} chars)")
    
    def get_recent_history(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Récupère l'historique récent d'une session."""
        if limit is None:
            limit = self.max_history
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT role, content, timestamp, metadata 
               FROM conversations 
               WHERE session_id = ? 
               ORDER BY timestamp DESC 
               LIMIT ?""",
            (session_id, limit * 2)  # On prend plus pour avoir les dernières
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        # Inverser pour avoir l'ordre chronologique
        history = []
        for row in reversed(rows):
            history.append({
                "role": row[0],
                "content": row[1],
                "timestamp": row[2],
                "metadata": json.loads(row[3]) if row[3] else {}
            })
        
        return history
    
    def get_last_n_interactions(self, session_id: str, n: int = 3) -> List[Dict[str, str]]:
        """Récupère les dernières N interactions (format simplifié)."""
        history = self.get_recent_history(session_id, limit=n)
        return [
            {"role": h["role"], "content": h["content"]}
            for h in history
        ]
    
    def get_conversation_context(self, session_id: str, n: int = 3) -> str:
        """Récupère le contexte de la conversation sous forme de texte."""
        interactions = self.get_last_n_interactions(session_id, n)
        if not interactions:
            return "No previous conversation."
        
        lines = []
        for i, interaction in enumerate(interactions):
            role = interaction["role"]
            content = interaction["content"]
            lines.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(lines)
    
    def clear_session(self, session_id: str):
        """Efface une session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        logger.info(f"🗑️ Session cleared: {session_id}")
    
    def get_all_sessions(self) -> List[Dict[str, str]]:
        """Récupère toutes les sessions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT session_id, created_at, last_updated 
               FROM sessions 
               ORDER BY last_updated DESC"""
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "session_id": row[0],
                "created_at": row[1],
                "last_updated": row[2]
            }
            for row in rows
        ]
    
    def get_session_stats(self, session_id: str) -> dict:
        """Récupère les statistiques d'une session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*), COUNT(DISTINCT role) FROM conversations WHERE session_id = ?",
            (session_id,)
        )
        total, roles = cursor.fetchone()
        
        cursor.execute(
            "SELECT role, COUNT(*) FROM conversations WHERE session_id = ? GROUP BY role",
            (session_id,)
        )
        role_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "total_messages": total,
            "unique_roles": roles,
            "role_counts": role_counts
        }