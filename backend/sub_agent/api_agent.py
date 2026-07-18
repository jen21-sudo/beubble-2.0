import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import json
import logging
import asyncio
from typing import Dict, Any, List
from AI_models.qwen.qwen_version import UniversalAgent
from driver.api_driver import APIDriver

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("APIAgent")

class APIAgent:
    """Intelligent API Agent with universal and adaptive parsing."""

    def __init__(self):
        self.llm = UniversalAgent()
        self.driver = APIDriver()
        self.is_completed = False
        self.thought_memory = {
            "actions": 0,
            "successful_apis": [],
            "failed_apis": [],
        }
        self.api_database = self._load_api_database()
        logger.info(f"{len(self.api_database)} APIs loaded")

    def _load_api_database(self) -> List[Dict[str, Any]]:
        """Loads available APIs."""
        all_apis = []
        api_liste_dir = os.path.join(os.path.dirname(__file__), "api_liste")
        
        if os.path.exists(api_liste_dir):
            for filename in os.listdir(api_liste_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(api_liste_dir, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                all_apis.extend([a for a in data if isinstance(a, dict) and a.get("name")])
                    except:
                        pass
        
        if not all_apis:
            all_apis = [
                {"name": "Open-Meteo", "url": "https://api.open-meteo.com/v1/forecast", "category": "Weather"},
                {"name": "CoinGecko", "url": "https://api.coingecko.com/api/v3", "category": "Crypto"},
            ]
        
        return all_apis

    def _build_prompt(self, objective: str, last_result: dict = None) -> str:
        """Intelligent prompt with failure/success context."""
        
        failed = self.thought_memory["failed_apis"]
        success = self.thought_memory["successful_apis"]
        
        failed_str = f"\nFailed APIs: {', '.join(failed)}" if failed else ""
        success_str = f"\nSuccessful APIs: {', '.join(success)}" if success else ""

        # If we already have parsed data, show it
        data_section = ""
        if last_result and last_result.get("parsed_data"):
            data_section = f"""
OBTAINED DATA:
{json.dumps(last_result['parsed_data'], indent=2, ensure_ascii=False)}

SUCCESS - Respond with FINISH
"""
        elif last_result and last_result.get("raw_structure"):
            data_section = f"""
DETECTED STRUCTURE: {json.dumps(last_result['raw_structure'], indent=2, ensure_ascii=False)[:500]}
The parser did not recognize this structure - try another API or FINISH
"""

        return f"""You are an API Agent. Choose an API and build an HTTP request.
Respond with a JSON object.

OBJECTIVE: {objective}
{failed_str}{success_str}
{data_section}

Available APIs: {', '.join([a['name'] for a in self.api_database[:10]])}

JSON examples:
- Weather: {{"operation": "API_CALL", "method": "GET", "url": "https://api.open-meteo.com/v1/forecast", "parameters": {{"latitude": 48.85, "longitude": 2.35, "current_weather": "true"}}}}

JSON format: {{"operation": "API_CALL or FINISH", "method": "GET", "url": "https://...", "parameters": {{}}}}"""

    def _parse_api_response(self, logs: str, exit_code: int, url: str) -> dict:
        """INTELLIGENT parser that adapts to all JSON structures."""
        
        if exit_code != 200:
            return {"status": "error", "error": f"HTTP {exit_code}"}

        # Extract the body
        if "RESPONSE BODY:" in logs:
            body_text = logs.split("RESPONSE BODY:\n", 1)[1].strip()
        else:
            body_text = logs

        # Try to parse the JSON
        try:
            data = json.loads(body_text)
        except json.JSONDecodeError:
            return {"status": "error", "error": "Invalid JSON"}

        # INTELLIGENT PARSER: automatically detect structure
        parsed = self._smart_extract(data)
        
        if parsed:
            return {
                "status": "success",
                "data": data,
                "parsed_data": parsed,
                "api_name": url.split("/")[2] if url else "unknown",
            }
        else:
            # No data extracted, but return the structure to help the LLM
            structure = self._describe_structure(data)
            return {
                "status": "unknown_structure",
                "error": "Unrecognized structure",
                "raw_structure": structure,
                "data": data,
            }

    def _smart_extract(self, data: dict, depth: int = 0) -> dict:
        """Intelligently extracts data regardless of structure.
        
        Strategies:
        1. Look for known patterns (current_weather, prices, etc.)
        2. If list of numerical values -> take the latest points
        3. Take the most relevant numerical fields
        """
        if depth > 3:
            return {}
        
        result = {}
        
        # PATTERN 1: Weather data
        if "current_weather" in data:
            w = data["current_weather"]
            return {"temperature": f"{w.get('temperature')}°C", "wind": f"{w.get('windspeed')} km/h"}
        
        # PATTERN 2: Crypto prices (CoinGecko market_chart)
        if "prices" in data and isinstance(data["prices"], list) and len(data["prices"]) > 0:
            prices = data["prices"]
            last_points = prices[-5:]  # 5 latest points
            result["prices"] = [
                {"date": self._timestamp_to_date(p[0]), "price_usd": p[1]} 
                for p in last_points
            ]
            result["number_of_points"] = len(prices)
            result["first_price"] = prices[0][1]
            result["last_price"] = prices[-1][1]
            if len(prices) >= 2:
                variation = ((prices[-1][1] - prices[0][1]) / prices[0][1]) * 100
                result["variation_%"] = round(variation, 2)
            return result
        
        # PATTERN 3: Simple price (CoinGecko simple/price)
        for key in data:
            if isinstance(data[key], dict):
                for subkey in data[key]:
                    if subkey in ["usd", "eur", "btc"]:
                        result[f"{key}_{subkey}"] = data[key][subkey]
        if result:
            return result
        
        # PATTERN 4: OpenWeatherMap
        if "main" in data:
            return {
                "temperature": f"{data['main'].get('temp')}°C",
                "humidity": f"{data['main'].get('humidity')}%"
            }
        
        # PATTERN 5: Data list
        if "data" in data and isinstance(data["data"], list):
            items = data["data"][:3]
            result["total_items"] = len(data["data"])
            result["sample"] = items
            return result
        
        # PATTERN 6: Simple numerical values
        for k, v in data.items():
            if isinstance(v, (int, float)) and not k.startswith("_"):
                result[k] = v
            elif isinstance(v, str) and len(v) < 100:
                result[k] = v
        
        if len(result) >= 2:
            return dict(list(result.items())[:5])
        
        # PATTERN 7: Dive into the first sub-object
        for k, v in data.items():
            if isinstance(v, dict):
                sub_result = self._smart_extract(v, depth + 1)
                if sub_result:
                    return sub_result
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                sub_result = self._smart_extract(v[0], depth + 1)
                if sub_result:
                    return {"total": len(v), "first": sub_result}
        
        return {}

    def _describe_structure(self, data: dict) -> dict:
        """Describes the structure to help the LLM understand."""
        structure = {}
        for k, v in data.items():
            if isinstance(v, dict):
                structure[k] = f"dict({len(v)} keys: {list(v.keys())[:3]})"
            elif isinstance(v, list):
                structure[k] = f"list({len(v)} elements)"
                if len(v) > 0 and isinstance(v[0], list):
                    structure[f"{k}[0]"] = f"list({len(v[0])} values: {v[0][:3]})"
            elif isinstance(v, (int, float)):
                structure[k] = type(v).__name__
            else:
                structure[k] = type(v).__name__
        return structure

    def _timestamp_to_date(self, ts: int) -> str:
        """Converts a Unix timestamp to readable date."""
        from datetime import datetime
        return datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")

    async def run_mission(self, objective: str, max_steps: int = 5) -> Dict[str, Any]:
        """Main loop with intelligent parsing."""
        logger.info(f"Mission start: {objective}")
        self.thought_memory = {"actions": 0, "successful_apis": [], "failed_apis": []}
        self.is_completed = False

        last_result = None
        last_full_data = None

        for step in range(max_steps):
            if self.is_completed:
                break

            logger.info(f"[Round {step + 1}/{max_steps}]")

            prompt = self._build_prompt(objective, last_result)
            
            try:
                decision = self.llm.execute(prompt)
            except Exception as e:
                logger.error(f"LLM Error: {e}")
                break

            op = decision.get("operation", "FINISH")

            if op == "FINISH":
                logger.info("Mission completed")
                self.is_completed = True
                break

            if op == "API_CALL":
                method = decision.get("method", "GET")
                url = decision.get("url", "")
                params = decision.get("parameters", {})

                logger.info(f"HTTP {method} -> {url}")

                logs, exit_code = await self.driver.execute_request(
                    method=method, url=url, params=params
                )

                self.thought_memory["actions"] += 1

                # INTELLIGENT PARSER
                parsed = self._parse_api_response(logs, exit_code, url)

                if parsed["status"] == "success" and parsed.get("parsed_data"):
                    api_name = parsed["api_name"]
                    self.thought_memory["successful_apis"].append(api_name)
                    last_result = parsed
                    last_full_data = parsed["data"]
                    logger.info(f"Data: {json.dumps(parsed['parsed_data'], ensure_ascii=False)[:200]}")
                    self.is_completed = True
                    break
                elif parsed["status"] == "unknown_structure":
                    # Unknown structure but valid response
                    api_name = parsed.get("api_name", url.split("/")[2] if url else "unknown")
                    last_result = parsed  # Pass the structure to the LLM
                    logger.warning(f"Unknown structure: {json.dumps(parsed.get('raw_structure', {}), ensure_ascii=False)[:200]}")
                    # Do not mark as failure, let the LLM decide
                else:
                    api_name = url.split("/")[2] if url else "unknown"
                    self.thought_memory["failed_apis"].append(api_name)
                    logger.warning(f"Failure: {parsed.get('error')}")

            await asyncio.sleep(0.2)

        logger.info("End of mission")
        await self.driver.close()

        if last_result and last_result.get("parsed_data"):
            return {
                "status": "success",
                "data": last_full_data,
                "parsed_data": last_result["parsed_data"],
                "api_used": self.thought_memory["successful_apis"][-1] if self.thought_memory["successful_apis"] else None,
                "thought_memory": self.thought_memory,
            }
        else:
            return {
                "status": "partial",
                "data": last_full_data,
                "parsed_data": last_result.get("parsed_data") if last_result else None,
                "api_used": None,
                "thought_memory": self.thought_memory,
            }

