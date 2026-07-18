# driver/browser_driver.py - Version avec playwright-stealth v2.x (API correcte)

import os
import json
import logging
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth  # ✅ Bon import

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BrowserDriver")

class BrowserDriver:
    """Driver with unlimited multi-tab support - Stealth v2"""
    
    def __init__(self, headless: bool = False, width: int = 1280, height: int = 720):
        self.headless = headless
        self.width = width
        self.height = height
        self.state_file = "browser_session_state.json"
        
        # Playwright
        self.playwright = None
        self.browser = None
        self.context = None
        self.stealth_context = None  # 🔥 Pour garder le contexte Stealth
        
        # Tab management
        self.pages = {}  # {name: page}
        self.current_page_name = None
        self.is_running = False
        
        # Screenshots directory
        self.screenshots_dir = None

    async def _handle_route_interception(self, route):
        """Block advertisements."""
        excluded_types = ["image", "media", "font"]
        excluded_domains = ["analytics", "google-analytics", "doubleclick", "facebook", "pixel", "adsystem"]
        
        request = route.request
        url = request.url.lower()
        resource_type = request.resource_type
        
        if resource_type in excluded_types or any(dom in url for dom in excluded_domains):
            await route.abort()
        else:
            await route.continue_()

    async def launch_browser(self):
        """Launch the browser with Stealth v2 (once for all tabs)."""
        if self.is_running:
            logger.info("🌐 Browser already launched")
            return self.context
            
        # 🔥 UTILISER L'API CORRECTE : Stealth().use_async()
        self.stealth_context = Stealth()
        self.playwright = await self.stealth_context.use_async(async_playwright())
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox"
            ]
        )
        
        context_kwargs = {
            "viewport": {"width": self.width, "height": self.height},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if os.path.exists(self.state_file):
            context_kwargs["storage_state"] = self.state_file
            logger.info("💾 [Session] Previous state detected.")
        
        self.context = await self.browser.new_context(**context_kwargs)
        await self.context.route("**/*", self._handle_route_interception)
        
        self.is_running = True
        logger.info("🌐 Browser launched with Stealth v2")
        return self.context

    async def take_screenshot(self, tab_name: str, filename: str = None) -> str:
        """
        Take a screenshot of the visible viewport only (not full page).
        Returns the file path.
        """
        if tab_name not in self.pages:
            return None
        
        page = self.pages[tab_name]
        
        # Setup screenshots directory
        if not self.screenshots_dir:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.screenshots_dir = os.path.join(root_dir, "screenshots")
            os.makedirs(self.screenshots_dir, exist_ok=True)
        
        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{tab_name}_{timestamp}.png"
        
        filepath = os.path.join(self.screenshots_dir, filename)
        
        try:
            # full_page=False to capture only visible viewport
            await page.screenshot(path=filepath, full_page=False)
            logger.info(f"📸 Screenshot: {filepath} (viewport only)")
            return filepath
        except Exception as e:
            logger.error(f"❌ Screenshot error: {e}")
            return None

    async def create_tab(self, name: str) -> object:
        """Create a dedicated tab for an agent."""
        if not self.is_running:
            await self.launch_browser()
            
        if name in self.pages:
            logger.warning(f"⚠️ Tab '{name}' already exists")
            return self.pages[name]
        
        # 🔥 Le stealth est déjà actif automatiquement sur toutes les pages !
        # Pas besoin d'appeler quoi que ce soit, Stealth().use_async() l'applique globalement
        page = await self.context.new_page()
        
        self.pages[name] = page
        self.current_page_name = name
        
        logger.info(f"🆕 [Tab] '{name}' created ({len(self.pages)} active tabs)")
        return page

    def get_tab(self, name: str) -> object:
        """Retrieve a tab by its name."""
        if name not in self.pages:
            raise ValueError(f"Tab '{name}' does not exist")
        return self.pages[name]

    async def switch_tab(self, name: str) -> object:
        """Switch active tab."""
        if name not in self.pages:
            raise ValueError(f"Tab '{name}' does not exist")
        
        self.current_page_name = name
        logger.info(f"🔄 [Tab] Switched to: {name}")
        return self.pages[name]

    def get_current_page(self):
        """Return the active page."""
        if self.current_page_name and self.current_page_name in self.pages:
            return self.pages[self.current_page_name]
        return None

    async def close_tab(self, name: str):
        """Close ONLY the specified tab."""
        if name not in self.pages:
            logger.warning(f"⚠️ Tab '{name}' does not exist")
            return
        
        page = self.pages[name]
        await page.close()
        del self.pages[name]
        
        logger.info(f"❌ [Tab] '{name}' closed ({len(self.pages)} tabs remaining)")
        
        if self.current_page_name == name:
            if self.pages:
                self.current_page_name = list(self.pages.keys())[0]
                logger.info(f"🔄 [Tab] Switched to: {self.current_page_name}")
            else:
                self.current_page_name = None

    async def close_all_tabs_except(self, keep_name: str):
        """Close all tabs except one."""
        if keep_name not in self.pages:
            logger.warning(f"⚠️ Tab '{keep_name}' does not exist")
            return
        
        for name in list(self.pages.keys()):
            if name != keep_name:
                await self.close_tab(name)
        
        self.current_page_name = keep_name
        logger.info(f"🔄 [Tab] Kept only: {keep_name}")

    async def goto(self, url: str, tab_name: str = None, timeout: int = 30000, wait_until: str = "domcontentloaded"):
        """Navigate to a URL on a specific tab."""
        if tab_name is None:
            tab_name = self.current_page_name
        
        if tab_name not in self.pages:
            raise ValueError(f"Tab '{tab_name}' does not exist")
        
        page = self.pages[tab_name]
        try:
            await page.goto(url, wait_until=wait_until, timeout=timeout)
            await page.wait_for_timeout(1000)
            await self._auto_dismiss_cookies(page)
            logger.info(f"🚀 [{tab_name}] Navigated to: {url[:60]}...")
        except Exception as e:
            logger.error(f"❌ [{tab_name}] Navigation error: {e}")
            raise

    async def _auto_dismiss_cookies(self, page):
        """Close cookies on a page."""
        if not page:
            return
            
        cookie_selectors = [
            "button:has-text('Accept')", "button:has-text('Accept all')", 
            "button:has-text('Allow')", "#accept-choices", ".accept-all",
            "button[id*='cookie']", "button[class*='accept']", "[aria-label*='cookie'] button"
        ]
        try:
            for selector in cookie_selectors:
                elements = await page.locator(selector).all()
                for el in elements:
                    if await el.is_visible():
                        await el.click(timeout=1000)
                        return
        except Exception:
            pass

    async def extract_semantic_dom(self, tab_name: str = None) -> list:
        """Extract the DOM from a tab (visible elements only)."""
        if tab_name is None:
            tab_name = self.current_page_name
        
        if tab_name not in self.pages:
            return []
        
        page = self.pages[tab_name]
        
        js_dom_script = """
        () => {
            const tree = [];
            // Focus on interactive elements and content elements
            const selectors = 'input, button, a, [role="button"], textarea, .price, [class*="price"], h1, h2, h3, [class*="title"], [class*="description"], p';
            const elements = document.querySelectorAll(selectors);
            let counter = 1;
            const viewportHeight = window.innerHeight;
            const viewportWidth = window.innerWidth;
            
            elements.forEach(el => {
                const rect = el.getBoundingClientRect();
                // Only include elements visible in the viewport
                if (rect.width > 10 && rect.height > 10 && 
                    rect.top >= -50 && rect.left >= -50 && 
                    rect.bottom <= viewportHeight + 50 && 
                    rect.right <= viewportWidth + 50) {
                    
                    let text = (el.innerText || el.placeholder || el.value || el.ariaLabel || el.title || "").trim();
                    text = text.replace(/\\s+/g, ' ').substring(0, 200);
                    
                    if (text.length > 1) {
                        const className = el.className ? el.className.toString() : "";
                        const idName = el.id || "";
                        const tagName = el.tagName ? el.tagName.toLowerCase() : "";
                        
                        // Detect prices
                        const isPrice = /[\\$€£]\\s*[\\d,.]+|[\\d,.]+\\s*[\\$€£]/.test(text);
                        const isNumber = /^[\\d,.]+$/.test(text.trim());
                        const isCurrency = /[\\$€£]/.test(text);
                        
                        // Detect titles
                        const isTitle = /^h[1-6]$/i.test(tagName) || 
                                       className.toLowerCase().includes('title') ||
                                       idName.toLowerCase().includes('title');
                        
                        // Detect descriptions
                        const isDescription = className.toLowerCase().includes('description') ||
                                             className.toLowerCase().includes('desc') ||
                                             idName.toLowerCase().includes('description');
                        
                        el.setAttribute('data-agent-target-id', counter);
                        
                        tree.push({
                            "id": counter,
                            "tag": tagName,
                            "text": text,
                            "is_price": isPrice,
                            "is_number": isNumber,
                            "is_currency": isCurrency,
                            "is_title": isTitle,
                            "is_description": isDescription,
                            "class_name": className.substring(0, 100),
                            "id_name": idName.substring(0, 100),
                            "coordinates": {
                                "x": Math.round(rect.left + rect.width / 2),
                                "y": Math.round(rect.top + rect.height / 2)
                            }
                        });
                        counter++;
                    }
                }
            });
            
            // Prioritize important elements
            if (tree.length > 100) {
                const prioritized = tree.filter(el => 
                    el.is_price || el.is_title || el.is_description
                );
                if (prioritized.length > 0) {
                    return prioritized.slice(0, 50);
                }
                return tree.slice(0, 50);
            }
            
            return tree;
        }
        """
        try:
            return await page.evaluate(js_dom_script)
        except Exception as e:
            logger.error(f"⚠️ [{tab_name}] DOM extraction failed: {e}")
            return []

    async def click_element(self, target_id: int, dom_tree: list, tab_name: str = None):
        """Click on an element in a tab."""
        if tab_name is None:
            tab_name = self.current_page_name
        
        if tab_name not in self.pages:
            return
        
        page = self.pages[tab_name]
        selector = f'[data-agent-target-id="{target_id}"]'
        
        try:
            await page.wait_for_selector(selector, timeout=3000)
            await page.click(selector, timeout=2000)
            logger.info(f"🎯 [{tab_name}] Click on ID: {target_id}")
        except Exception:
            for item in dom_tree:
                if item["id"] == int(target_id):
                    coords = item["coordinates"]
                    await page.mouse.click(coords["x"], coords["y"])
                    logger.info(f"🎯 [{tab_name}] Coordinate click")

    async def type_text(self, target_id: int, text: str, tab_name: str = None):
        """Type text in a tab."""
        if tab_name is None:
            tab_name = self.current_page_name
        
        if tab_name not in self.pages:
            return
        
        page = self.pages[tab_name]
        selector = f'[data-agent-target-id="{target_id}"]'
        await page.wait_for_selector(selector, timeout=3000)
        await page.fill(selector, text)
        await page.press(selector, "Enter")
        logger.info(f"⌨️ [{tab_name}] Input completed")

    async def wait(self, milliseconds: int = 2000, tab_name: str = None):
        """Wait in a tab."""
        if tab_name is None:
            tab_name = self.current_page_name
        
        if tab_name in self.pages:
            await self.pages[tab_name].wait_for_timeout(milliseconds)

    async def get_current_url(self, tab_name: str = None) -> str:
        """Get the URL of a tab."""
        if tab_name is None:
            tab_name = self.current_page_name
        
        if tab_name in self.pages:
            return self.pages[tab_name].url
        return ""

    async def save_session(self):
        """Save the session."""
        if self.context:
            try:
                await self.context.storage_state(path=self.state_file)
                logger.info(f"💾 Session saved")
            except Exception as e:
                logger.warning(f"⚠️ Cannot save: {e}")

    async def close_browser(self):
        """Completely close the browser."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.is_running = False
            self.pages = {}
            logger.info("🔚 Browser completely closed")
        except Exception as e:
            logger.warning(f"⚠️ Closing error: {e}")