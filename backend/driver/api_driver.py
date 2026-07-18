import httpx
import logging
import os
import json
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("APIDriver")

class APIDriver:
    """Universal and generic asynchronous network driver, driven by the LLM's authentication structure"""
    
    def __init__(self):
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache"
        }
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=False, headers=self.default_headers)
    
    async def execute_request(self, method: str, url: str, auth_env_var: Optional[str] = None, **kwargs) -> tuple[str, int]:
        """Executes a request generically following the authentication instructions passed in kwargs"""
        
        auth_mode = kwargs.pop("auth_mode", "HEADER")
        auth_param_name = kwargs.pop("auth_param_name", "key")

        # 1. Authentication
        if auth_env_var:
            api_key = os.getenv(auth_env_var)
            if not api_key:
                logger.warning(f"Missing environment variable: {auth_env_var}")
                return f"ERROR: The required authentication key '{auth_env_var}' is not found.", 401

            if str(auth_mode).upper() == "QUERY_PARAM":
                kwargs["params"] = kwargs.get("params", {})
                final_param_name = auth_param_name if auth_param_name else "appid"
                kwargs["params"][final_param_name] = api_key.strip()
                logger.info(f"[Driver] Injecting parameter '{final_param_name}'.")
            else:
                kwargs["headers"] = kwargs.get("headers", {})
                if "Authorization" not in kwargs["headers"]:
                    kwargs["headers"]["Authorization"] = f"Bearer {api_key.strip()}"

        # 2. Payload Routing
        if "payload" in kwargs:
            payload_data = kwargs.pop("payload")
            if isinstance(payload_data, dict) and payload_data:
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    if "json" not in kwargs and "data" not in kwargs:
                        kwargs["json"] = payload_data
                else:
                    if "params" not in kwargs:
                        kwargs["params"] = payload_data

        # 3. Retry Policy and Execution
        max_retries = 3
        backoff_factor = 1.0
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[HTTP] ({attempt + 1}/{max_retries}) -> {method.upper()} {url}")
                response = await self.client.request(method, url, **kwargs)
                
                # Redirect handling
                if response.is_redirect:
                    redirect_url = response.headers.get("Location", "")
                    if "html" in redirect_url or "/ui/" in redirect_url:
                        body_formatted = f"NETWORK ERROR: The server refused to provide raw JSON and attempted to redirect to the HTML graphical interface: {redirect_url}"
                        return f"HTTP STATUS: {response.status_code}\nRESPONSE BODY:\n{body_formatted}", 406
                    response = await self.client.request(method, redirect_url, **kwargs)

                response_text = response.text
                response_text_stripped = response_text.strip()
                is_html = response_text_stripped.lower().startswith(("<!doctype", "<html"))
                
                # FIX: Parse JSON WITHOUT truncating
                if is_html:
                    body_formatted = f"FORMAT ERROR: HTML content rejected by the driver.\nStart of text: {response_text_stripped[:200]}"
                    exit_code = 406
                else:
                    try:
                        # Try to parse as JSON
                        json_data = response.json()
                        body_formatted = json.dumps(json_data, indent=2, ensure_ascii=False)
                        exit_code = response.status_code
                        logger.info(f"JSON successfully parsed: {len(body_formatted)} characters")
                    except (ValueError, TypeError, json.JSONDecodeError):
                        # If not JSON, keep the raw text but limit the size
                        if len(response_text) > 3000:
                            body_formatted = response_text[:3000] + f"\n... [TRUNCATED: {len(response_text)} characters total]"
                        else:
                            body_formatted = response_text
                        exit_code = response.status_code
                        logger.warning(f"Non-JSON response: {len(response_text)} characters")

                logs = f"HTTP STATUS: {response.status_code}\nRESPONSE BODY:\n{body_formatted}"
                return logs, exit_code

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(f"Attempt {attempt + 1}: {type(e).__name__}")
                if attempt == max_retries - 1:
                    return f"CRITICAL NETWORK ERROR: Failure after {max_retries} attempts: {str(e)}", 500
                await asyncio.sleep(backoff_factor * (2 ** attempt))
            except httpx.RequestError as e:
                return f"REQUEST ERROR: Sending failed. Details: {str(e)}", 500

    async def close(self):
        await self.client.aclose()