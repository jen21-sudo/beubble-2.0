# sub_agent/navigator.py - Brave Search without LLM Context

import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from AI_models.qwen.qwen_version import UniversalAgent  # Used only for query planning

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NavigationAgent")

# ============================================================
# CONFIGURATION
# ============================================================

BRAVE_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "")
BRAVE_WEB_URL = "https://api.search.brave.com/res/v1/web/search"

SCREENSHOTS_DIR = os.path.join(root_dir, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


# ============================================================
# BRAVE SEARCH CLIENT (without LLM Context)
# ============================================================

class BraveSearchClient:
    """Client for Brave Search API - Raw search only"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or BRAVE_API_KEY
        self.session = None
        self.web_endpoint = BRAVE_WEB_URL
    
    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "X-Subscription-Token": self.api_key,
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip"
                }
            )
        return self.session
    
    async def search(self, query: str, count: int = 10) -> List[Dict]:
        """Brave web search - returns raw results"""
        try:
            session = await self._get_session()
            params = {"q": query, "count": min(count, 20)}
            logger.info(f"Brave Search: '{query}'")
            
            async with session.get(self.web_endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("web", {}).get("results", [])
                    
                    formatted = []
                    for i, r in enumerate(results, 1):
                        formatted.append({
                            "rank": i,
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "snippet": r.get("description", ""),
                            "description": r.get("description", ""),
                            "source": "brave_search"
                        })
                    
                    logger.info(f"Found {len(formatted)} results for '{query}'")
                    return formatted
                else:
                    error_text = await response.text()
                    logger.error(f"Brave API error {response.status}: {error_text[:200]}")
                    return []
        except Exception as e:
            logger.error(f"Brave search failed: {e}")
            return []
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


# ============================================================
# SEARCH AGENT - Raw search only
# ============================================================

class SearchAgent:
    """Brave Search agent - raw data without enrichment"""
    
    def __init__(self, name: str, brave_client: BraveSearchClient):
        self.name = name
        self.brave = brave_client
        self.extracted_data = []
        self.is_completed = False
        self.target_query = None
    
    async def initialize(self, query: str = None):
        self.target_query = query
        logger.info(f"Agent '{self.name}' initialized with: '{query}'")
    
    async def execute_search(self, objective: str = "") -> dict:
        """Executes search and returns raw results"""
        result = {
            "agent": self.name,
            "completed": False,
            "extracted": None,
            "url": f"brave_search:{self.target_query}",
            "vision_used": False
        }
        
        try:
            # Raw search only
            raw_results = await self.brave.search(self.target_query, count=5)
            
            if not raw_results:
                logger.warning(f"[{self.name}] No results for: '{self.target_query}'")
                return result
            
            # Standardized raw data
            extracted = {
                "urls": [r.get("url") for r in raw_results],
                "raw_snippets": [r.get("snippet", "") for r in raw_results],
                "titles": [r.get("title", "") for r in raw_results],
                "source": self.name,
                "_metadata": {
                    "agent": self.name,
                    "url": f"brave_search:{self.target_query}",
                    "extracted_at": datetime.now().isoformat(),
                    "method": "brave_search_raw"
                }
            }
            
            self.extracted_data.append(extracted)
            result["extracted"] = extracted
            result["completed"] = True
            self.is_completed = True
            
            logger.info(f"[{self.name}] Collected {len(raw_results)} raw results")
            return result
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return result
    
    async def close(self):
        self.is_completed = True
        logger.info(f"Agent '{self.name}' terminated")


# ============================================================
# MULTI-AGENT NAVIGATOR - Parallel search, no synthesis
# ============================================================

class MultiAgentNavigator:
    """
    Multi-agent navigator using Brave Search.
    LLM (Qwen) is used ONLY for query planning.
    Results are returned RAW, without any enrichment.
    """
    
    def __init__(self, headless: bool = True, width: int = 1280, height: int = 720):
        self.headless = headless
        self.width = width
        self.height = height
        
        self.llm = UniversalAgent()        # for planning only
        self.brave = BraveSearchClient()
        self.agents = {}
        self.results = {}
        self.is_initialized = False
    
    async def initialize_browser(self):
        if not self.is_initialized:
            if not BRAVE_API_KEY:
                raise ValueError("BRAVE_SEARCH_API_KEY is missing")
            self.is_initialized = True
            logger.info("Brave navigator initialized")
    
    async def add_agent(self, name: str, url_or_query: str = None) -> SearchAgent:
        if not self.is_initialized:
            await self.initialize_browser()
        
        if url_or_query and url_or_query.startswith(("http://", "https://")):
            query = url_or_query.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
            logger.info(f"URL converted: '{url_or_query}' -> '{query}'")
        else:
            query = url_or_query or name
        
        agent = SearchAgent(name, self.brave)
        await agent.initialize(query)
        self.agents[name] = agent
        self.results[name] = []
        logger.info(f"Agent '{name}' added (total: {len(self.agents)})")
        return agent
    
    async def plan_queries(self, objective: str, max_queries: int = 5) -> List[Dict[str, str]]:
        """Uses Qwen LLM to generate optimized search queries"""
        prompt = f"""You are a search strategist. Generate up to {max_queries} specific search queries for the objective.
Return ONLY a JSON list of objects with "name" and "query".
Example: [{{"name": "pricing", "query": "ASUS ROG Strix price 2025"}}]
OBJECTIVE: "{objective}"
"""
        try:
            result = self.llm.execute(prompt)
            if isinstance(result, str):
                import re
                json_match = re.search(r'\[.*\]', result, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    if isinstance(parsed, list):
                        return parsed
            elif isinstance(result, list):
                return result
        except Exception as e:
            logger.error(f"Planning error: {e}")
        return [{"name": "general", "query": objective}]
    
    async def execute_parallel(self, objective: str, max_steps: int = 8, auto_plan: bool = False) -> dict:
        if not self.is_initialized:
            await self.initialize_browser()
        
        if auto_plan and not self.agents:
            queries = await self.plan_queries(objective)
            for q in queries:
                await self.add_agent(q["name"], q["query"])
        
        if not self.agents:
            return {"status": "error", "message": "No agents added", "data": []}
        
        try:
            for name, agent in self.agents.items():
                if objective not in agent.target_query:
                    agent.target_query = f"{agent.target_query} {objective}"
            
            tasks = [agent.execute_search(objective) for agent in self.agents.values()]
            logger.info(f"Launching {len(tasks)} parallel searches...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            all_extracted_data = []
            for name, result in zip(self.agents.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"Agent '{name}' failed: {result}")
                elif isinstance(result, dict) and result.get("extracted"):
                    extracted = result["extracted"]
                    if "_metadata" not in extracted:
                        extracted["_metadata"] = {"agent": name}
                    all_extracted_data.append(extracted)
            
            return {
                "status": "success" if all_extracted_data else "no_data",
                "message": "Raw data collected",
                "agents": list(self.agents.keys()),
                "data": all_extracted_data,
                "summary": {
                    "total_agents": len(self.agents),
                    "total_extractions": len(all_extracted_data),
                    "completed_agents": [n for n, a in self.agents.items() if a.is_completed]
                }
            }
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            return {"status": "error", "message": str(e), "data": []}
    
    async def close_agent(self, name: str):
        if name in self.agents:
            await self.agents[name].close()
            del self.agents[name]
            logger.info(f"Agent '{name}' removed")
    
    async def close_all_agents(self):
        for name in list(self.agents.keys()):
            await self.close_agent(name)
    
    async def close_browser(self):
        await self.close_all_agents()
        await self.brave.close()
        self.is_initialized = False
        logger.info("Navigator closed")

