import time
from playwright.sync_api import sync_playwright

class MajsoulWindow:
    def __init__(self, account: str, password: str):
        """Initialize Majsoul window and perform login"""
        try:
            self.pw = sync_playwright().start()
            self.browser = self.pw.chromium.launch(
                headless=False,
                args=['--window-size=1440,920'],
                timeout=0
            )
            self.context = self.browser.new_context(
                viewport={'width': 1440, 'height': 900},
                no_viewport=True
            )
            self.page = self.context.new_page()
            
            # Navigate and login
            self.page.goto("https://game.maj-soul.com/1/")
            print("Waiting for Majsoul to load...")
            time.sleep(40)
            self.page.locator("html").click()
            self.page.locator("#layaCanvas").click(position={"x":926,"y":214})
            time.sleep(0.5)
            self.page.get_by_role("textbox").fill(account)
            self.page.locator("#layaCanvas").click(position={"x":922,"y":300})
            time.sleep(0.5)
            self.page.get_by_role("textbox").fill(password)
            self.page.locator("#layaCanvas").click(position={"x":914,"y":465})
            
        except Exception as e:
            print(f"Failed to initialize Majsoul window: {e}")
            self.cleanup()
            raise

    def get_box(self):
        """Get the game window position and size
        Returns: tuple (left, top, right, bottom)
        """
        try:
            viewport_size = self.page.viewport_size
            if viewport_size:
                width = viewport_size['width']
                height = viewport_size['height']
                return (0, 0, width, height)
        except Exception as e:
            print(f"Error getting window box: {e}")
            return None

    def __call__(self):
        """Magic method as shortcut for get_box"""
        return self.get_box()

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'browser'):
            self.browser.close()
        if hasattr(self, 'pw'):
            self.pw.stop()

    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
