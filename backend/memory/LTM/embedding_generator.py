# memory/LTM/embedding_generator.py
import sys
import os
import json
import logging
import aiohttp
import asyncio
from typing import List, Optional
from dotenv import load_dotenv
from pathlib import Path

# Charger .env
load_dotenv()

# 1. Dynamic sys.path alignment
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

logger = logging.getLogger("MotherSystem.EmbeddingJina")

class CloudEmbeddingGenerator:
    """Managed embedding generator via Jina AI API (Free - 0 MB local)"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: int = 1024,
        timeout: int = 30
    ):
        """
        Initialise le générateur d'embeddings.
        
        Args:
            api_key: Clé API Jina (si None, utilise JINA_API_KEY de l'environnement)
            model: Modèle d'embedding (par défaut: jina-embeddings-v5-text-small)
            dimension: Dimension des embeddings (par défaut: 1024)
            timeout: Timeout en secondes pour les requêtes API
        """
        # ============================================================
        # 1. CHARGEMENT DE LA CLÉ API (comportement original)
        # ============================================================
        # Si api_key est None, utiliser la variable d'environnement (comme avant)
        self.api_key = api_key or os.getenv("JINA_API_KEY", "")
        
        # ============================================================
        # 2. CONFIGURATION DU MODÈLE
        # ============================================================
        # Permettre de changer le modèle via paramètre ou variable d'environnement
        self.model = model or os.getenv("JINA_EMBEDDING_MODEL", "jina-embeddings-v5-text-small")
        
        # ============================================================
        # 3. CONFIGURATION DE LA DIMENSION
        # ============================================================
        self._dimension = dimension
        self._timeout = timeout
        self.base_url = "https://api.jina.ai/v1/embeddings"
        self._session = None
        
        # ============================================================
        # 4. LOGGING
        # ============================================================
        if not self.api_key:
            logger.warning("⚠️ JINA_API_KEY not set in environment variables")
        else:
            # Cacher partiellement la clé pour la sécurité
            masked_key = self.api_key[:8] + "..." + self.api_key[-4:] if len(self.api_key) > 12 else "***"
            logger.info(f"✅ JINA_API_KEY loaded (length: {len(self.api_key)})")
            logger.info(f"✅ Using model: {self.model}")
            logger.info(f"✅ Embedding dimension: {self._dimension}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def generate(self, text: str) -> List[float]:
        """
        Generates embedding via Jina API directly.
        Returns a list of floats with dimension 1024.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self._dimension
        
        if not self.api_key:
            logger.warning("No API key provided for Jina embeddings")
            return [0.0] * self._dimension
        
        try:
            session = await self._get_session()
            
            # Tronquer le texte si trop long (8000 caractères max)
            text_to_embed = text[:8000] if len(text) > 8000 else text
            
            payload = {
                "model": self.model,
                "input": text_to_embed,
                "dimensions": self._dimension,
                "normalized": True,
                "embedding_type": "float"
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.debug(f"[HTTP] POST {self.base_url} - Model: {self.model}")
            
            async with session.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as response:
                status = response.status
                response_text = await response.text()
                
                # ✅ CORRECT: 200-299 = SUCCÈS
                if 200 <= status < 300:
                    try:
                        data = json.loads(response_text)
                        
                        # Vérifier la structure de la réponse
                        if "data" in data and len(data["data"]) > 0:
                            embedding = data["data"][0].get("embedding", [])
                            
                            # Vérifier la dimension
                            if len(embedding) == self._dimension:
                                logger.info(f"✅ Embedding generated: {len(embedding)} dimensions")
                                # Afficher les premières valeurs pour debug (en mode DEBUG)
                                if logger.isEnabledFor(logging.DEBUG):
                                    logger.debug(f"First 5 values: {embedding[:5]}")
                                return embedding
                            else:
                                logger.warning(f"⚠️ Unexpected dimension: {len(embedding)}, expected {self._dimension}")
                                # Ajuster la dimension
                                if len(embedding) > self._dimension:
                                    return embedding[:self._dimension]
                                elif len(embedding) > 0:
                                    return embedding + [0.0] * (self._dimension - len(embedding))
                                else:
                                    return [0.0] * self._dimension
                        else:
                            logger.error(f"❌ Invalid response structure: {json.dumps(data, indent=2)[:500]}")
                            return [0.0] * self._dimension
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse JSON: {e}")
                        logger.error(f"Response text: {response_text[:500]}")
                        return [0.0] * self._dimension
                else:
                    # ❌ VRAIE erreur HTTP
                    logger.error(f"❌ Jina API error (HTTP {status}): {response_text[:500]}")
                    return [0.0] * self._dimension
                    
        except aiohttp.ClientTimeout:
            logger.error(f"❌ Jina API timeout ({self._timeout}s)")
            return [0.0] * self._dimension
        except aiohttp.ClientError as e:
            logger.error(f"❌ Network error: {e}")
            return [0.0] * self._dimension
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return [0.0] * self._dimension
    
    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts en parallèle.
        
        Args:
            texts: Liste de textes à encoder
        
        Returns:
            Liste de vecteurs d'embedding
        """
        if not texts:
            return []
        
        # Pour éviter de surcharger l'API, limiter à 10 requêtes simultanées
        semaphore = asyncio.Semaphore(10)
        
        async def generate_with_limit(text):
            async with semaphore:
                return await self.generate(text)
        
        tasks = [generate_with_limit(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrer les erreurs
        embeddings = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error generating embedding for text {i}: {result}")
                embeddings.append([0.0] * self._dimension)
            else:
                embeddings.append(result)
        
        return embeddings
    
    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("Embedding session closed")