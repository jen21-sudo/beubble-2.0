# memory/LTM/long_term_memory.py
import os
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from memory.LTM.embedding_generator import CloudEmbeddingGenerator

logger = logging.getLogger("MotherSystem.LTM")

class LongTermMemory:
    """
    Wide-Angle semantic memory system hosted on Qdrant.
    Separates data into two semantic nodes: 'user' (dialogue) and 'agent' (technical).
    """
    
    def __init__(
        self, 
        collection_name: str = "beubble_memory", 
        storage_path: Optional[str] = None,
        jina_api_key: Optional[str] = None,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
        embedding_dimension: int = 1024
    ):
        """
        Initialise la mémoire à long terme.
        
        Args:
            collection_name: Nom de la collection Qdrant
            storage_path: Chemin pour le stockage local Qdrant (None = utilise config)
            jina_api_key: Clé API Jina (None = utilise variable d'environnement)
            qdrant_host: Hôte Qdrant distant (None = mode local)
            qdrant_port: Port Qdrant distant (None = mode local)
            embedding_dimension: Dimension des vecteurs d'embedding
        """
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension
        
        # ============================================================
        # 1. INITIALISATION DE L'EMBEDDER
        # ============================================================
        # Si jina_api_key est None, CloudEmbeddingGenerator utilisera
        # la variable d'environnement JINA_API_KEY (comportement original)
        self.embedder = CloudEmbeddingGenerator(api_key=jina_api_key)
        
        # ============================================================
        # 2. INITIALISATION DU CLIENT QDRANT
        # ============================================================
        self.client = self._init_qdrant_client(
            storage_path=storage_path,
            host=qdrant_host,
            port=qdrant_port
        )
        
        # ============================================================
        # 3. INITIALISATION DE LA COLLECTION
        # ============================================================
        self._init_collection()
    
    def _init_qdrant_client(
        self, 
        storage_path: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ) -> QdrantClient:
        """
        Initialise le client Qdrant (local ou distant).
        
        Args:
            storage_path: Chemin pour le stockage local
            host: Hôte pour Qdrant distant
            port: Port pour Qdrant distant
        
        Returns:
            Client Qdrant configuré
        """
        # Si un hôte est spécifié, utiliser Qdrant distant
        if host and port:
            logger.info(f"[Qdrant] Connecting to remote Qdrant at {host}:{port}")
            return QdrantClient(
                host=host,
                port=port,
                timeout=30
            )
        
        # Sinon, utiliser Qdrant local
        if storage_path is None:
            # Chemin par défaut: ./qdrant_db (comportement original)
            storage_path = "qdrant_db"
        
        # Créer le dossier si nécessaire
        Path(storage_path).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[Qdrant] Using local storage at: {storage_path}")
        return QdrantClient(path=storage_path)

    def _init_collection(self):
        """Creates the collection in Qdrant or recreates it if the dimension has changed."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        target_dimension = self.embedding_dimension
        
        if exists:
            try:
                info = self.client.get_collection(collection_name=self.collection_name)
                current_size = info.config.params.vectors.size
                
                if current_size != target_dimension:
                    logger.warning(
                        f"[Qdrant] Inadequate dimension ({current_size} instead of {target_dimension}). "
                        f"Recreating collection '{self.collection_name}'..."
                    )
                    self.client.delete_collection(collection_name=self.collection_name)
                    exists = False
            except Exception as e:
                logger.warning(f"[Qdrant] Error checking collection: {e}. Recreating...")
                try:
                    self.client.delete_collection(collection_name=self.collection_name)
                except:
                    pass
                exists = False

        if not exists:
            logger.info(f"[Qdrant] Creating collection '{self.collection_name}'...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=target_dimension,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"[Qdrant] Collection successfully initialized")

    async def save_node(self, node_type: str, content: str, metadata: dict = None):
        """Generates the Jina embedding and inserts a point into Qdrant."""
        logger.info(f"[Qdrant] Indexing a [{node_type.upper()}] node...")
        
        # Vérifier que le contenu n'est pas vide
        if not content or not content.strip():
            logger.warning("[Qdrant] Empty content. Registration cancelled.")
            return
        
        try:
            vector = await self.embedder.generate(content)
        except Exception as e:
            logger.error(f"[Qdrant] Error generating embedding: {e}")
            return
        
        if all(v == 0.0 for v in vector) or len(vector) != self.embedding_dimension:
            logger.warning(
                f"[Qdrant] Invalid embedding (length: {len(vector)}). Registration cancelled."
            )
            return

        point_id = str(uuid.uuid4())
        
        payload = {
            "node_type": node_type,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logger.info(f"[Qdrant] Point successfully inserted. ID: {point_id}")
        except Exception as e:
            logger.error(f"[Qdrant] Error inserting point: {e}")

    async def search_grand_angle(
        self, 
        query: str, 
        threshold: float = 0.70, 
        limit: int = 3,
        node_type: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Global Wide-Angle semantic search."""
        logger.info(f"[Qdrant] Wide-Angle search for: '{query}'")
        
        try:
            query_vector = await self.embedder.generate(query)
        except Exception as e:
            logger.error(f"[Qdrant] Error generating query embedding: {e}")
            return {"user_nodes": [], "agent_nodes": []}
        
        results = {
            "user_nodes": [],
            "agent_nodes": []
        }

        if all(v == 0.0 for v in query_vector) or len(query_vector) != self.embedding_dimension:
            logger.warning("[Qdrant] Invalid query embedding.")
            return results

        try:
            # Construire le filtre si un type est spécifié
            query_filter = None
            if node_type:
                query_filter = {
                    "must": [
                        {"key": "node_type", "match": {"value": node_type}}
                    ]
                }
            
            search_results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit * 2,
                score_threshold=threshold,
                query_filter=query_filter
            ).points

            for hit in search_results:
                node_data = {
                    "content": hit.payload.get("content"),
                    "metadata": hit.payload.get("metadata", {}),
                    "score": round(hit.score, 3),
                    "created_at": hit.payload.get("created_at")
                }
                
                hit_node_type = hit.payload.get("node_type")
                if hit_node_type == "user":
                    results["user_nodes"].append(node_data)
                elif hit_node_type == "agent":
                    results["agent_nodes"].append(node_data)

            results["user_nodes"] = results["user_nodes"][:limit]
            results["agent_nodes"] = results["agent_nodes"][:limit]
            
            logger.info(
                f"[Qdrant] Found {len(results['user_nodes'])} user nodes "
                f"and {len(results['agent_nodes'])} agent nodes"
            )
            
        except Exception as e:
            logger.error(f"[Qdrant] Error during search: {e}")
        
        return results

    async def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la collection."""
        try:
            collection_info = self.client.get_collection(collection_name=self.collection_name)
            return {
                "collection_name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"[Qdrant] Error getting stats: {e}")
            return {
                "collection_name": self.collection_name,
                "error": str(e),
                "status": "error"
            }

    async def clear(self):
        """Supprime tous les points de la collection."""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            self._init_collection()
            logger.info(f"[Qdrant] Collection '{self.collection_name}' cleared and recreated.")
        except Exception as e:
            logger.error(f"[Qdrant] Error clearing collection: {e}")

    async def close(self):
        """Closes active connections."""
        try:
            await self.embedder.close()
        except Exception as e:
            logger.warning(f"[Qdrant] Error closing embedder: {e}")
        
        try:
            self.client.close()
        except Exception as e:
            logger.warning(f"[Qdrant] Error closing Qdrant client: {e}")