# backend/config.py
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# Charger .env
load_dotenv()

class Config:
    """Configuration centralisée avec toutes les clés API"""
    
    # ============================================================
    # ENVIRONNEMENT
    # ============================================================
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # ============================================================
    # SERVER
    # ============================================================
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    WORKERS = int(os.getenv("WORKERS", 1))
    RELOAD = os.getenv("RELOAD", "True").lower() == "true"
    
    # ============================================================
    # MODE INTERFACE (NOUVEAU)
    # ============================================================
    # Si True, permet l'accès sans clé API (pour développement/demo)
    # Si False, exige une authentification (production)
    INTERFACE_MODE = os.getenv("INTERFACE_MODE", "True").lower() == "true"
    
    # ============================================================
    # API KEYS - BEUBBLE
    # ============================================================
    API_KEY = os.getenv("API_KEY", "")
    API_KEY_HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")
    
    # ============================================================
    # EXTERNAL SERVICES
    # ============================================================
    
    # DASHSCOPE (Aliyun Qwen)
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
    
    # BRAVE SEARCH
    BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "")
    
    # JINA AI
    JINA_API_KEY = os.getenv("JINA_API_KEY", "")
    
    # ============================================================
    # DATABASE & STORAGE
    # ============================================================
    BASE_DIR = Path(__file__).parent
    DATABASE_DIR = BASE_DIR / os.getenv("DATABASE_DIR", "database")
    WORKSPACE_DIR = BASE_DIR / os.getenv("WORKSPACE_DIR", "workspace")
    LOGS_DIR = BASE_DIR / os.getenv("LOGS_DIR", "logs")
    
    # ============================================================
    # QDRANT (Vector DB)
    # ============================================================
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "beubble_memory")
    
    # ============================================================
    # MODEL CONFIGURATION
    # ============================================================
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen-plus")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "jina-embeddings-v2")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 4096))
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))
    
    # ============================================================
    # COOKIE CONFIGURATION
    # ============================================================
    COOKIE_NAME = os.getenv("COOKIE_NAME", "beubble_session")
    COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE", 86400))  # 24 hours
    COOKIE_HTTPONLY = os.getenv("COOKIE_HTTPONLY", "True").lower() == "true"
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "False").lower() == "true"
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
    
    # ============================================================
    # MÉTHODES UTILITAIRES
    # ============================================================
    
    @classmethod
    def ensure_directories(cls):
        """Crée les dossiers nécessaires"""
        for dir_path in [cls.DATABASE_DIR, cls.WORKSPACE_DIR, cls.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_db_path(cls, name: str) -> str:
        """Retourne le chemin complet d'une base de données"""
        return str(cls.DATABASE_DIR / name)
    
    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """Retourne la configuration LLM pour MotherAgent"""
        return {
            "model": cls.DEFAULT_MODEL,
            "temperature": cls.TEMPERATURE,
            "max_tokens": cls.MAX_TOKENS,
            "dashscope_api_key": cls.DASHSCOPE_API_KEY,
            "jina_api_key": cls.JINA_API_KEY,
            "brave_api_key": cls.BRAVE_SEARCH_API_KEY
        }
    
    @classmethod
    def check_keys(cls) -> Dict[str, bool]:
        """Vérifie si toutes les clés API sont présentes"""
        return {
            "DASHSCOPE_API_KEY": bool(cls.DASHSCOPE_API_KEY),
            "BRAVE_SEARCH_API_KEY": bool(cls.BRAVE_SEARCH_API_KEY),
            "JINA_API_KEY": bool(cls.JINA_API_KEY),
            "API_KEY": bool(cls.API_KEY)
        }
    
    @classmethod
    def get_missing_keys(cls) -> list:
        """Retourne la liste des clés API manquantes"""
        missing = []
        if not cls.DASHSCOPE_API_KEY:
            missing.append("DASHSCOPE_API_KEY")
        if not cls.BRAVE_SEARCH_API_KEY:
            missing.append("BRAVE_SEARCH_API_KEY")
        if not cls.JINA_API_KEY:
            missing.append("JINA_API_KEY")
        return missing
    
    @classmethod
    def is_interface_mode(cls) -> bool:
        """Vérifie si on est en mode interface (sans authentification)"""
        return cls.INTERFACE_MODE

# Instance globale
config = Config()
config.ensure_directories()

# Afficher un warning si des clés sont manquantes
if config.get_missing_keys():
    print(f"⚠️  ATTENTION: Clés API manquantes: {', '.join(config.get_missing_keys())}")
    print("   Certaines fonctionnalités peuvent ne pas fonctionner correctement.")

# Afficher le mode
if config.INTERFACE_MODE:
    print("🌐 MODE INTERFACE ACTIVÉ - Authentification désactivée")
    print("   (Pour la production, définissez INTERFACE_MODE=False)")
else:
    print("🔒 MODE SÉCURISÉ - Authentification requise")