# src/runner.py

from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from typing import Optional
import hashlib

from src.chromosome import Chromosome, Action, ActionType, UIElement, UIElementType
from src.crawler import Crawler


class TestRunner:
    """
    Executes test sequences (Chromosomes) and collects execution data.
    """

    def __init__(self, url: str, headless: bool = True):
        self.url = url
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.crawler = Crawler()

    def start(self):
        """Initialize browser and navigate to starting URL."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        self.page.goto(self.url)
        self.page.wait_for_load_state('networkidle')

    def stop(self):
        """Clean up browser resources."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def run_chromosome(self, chromosome: Chromosome, rescan_between_actions: bool = False) -> dict:
        """
        Execute a chromosome and collect execution data, differentiating between
        application bugs and simple execution errors.
        """
        results = {
            'urls': [],
            'states': [],
            'execution_errors': [],  # For timeouts, element not found, etc.
            'js_errors': [],         # For uncaught JS exceptions
            'http_errors': [],       # For 5xx server errors
            'crashed': False,        # If the page crashes
            'action_results': [],
            'available_elements': []
        }

        # --- Event Handlers ---
        def handle_console(msg):
            if msg.type == 'error':
                results['js_errors'].append(f"JS Error: {msg.text}")

        def handle_response(response):
            if response.status >= 500:
                results['http_errors'].append(f"HTTP {response.status} on {response.url}")

        def handle_crash(page):
            results['crashed'] = True

        self.page.on('console', handle_console)
        self.page.on('response', handle_response)
        self.page.on('crash', handle_crash)

        try:
            # Record initial state
            results['urls'].append(self.page.url)
            results['states'].append(self._get_page_state())

            # Use chromosome.actions since Chromosome isn't directly iterable
            for i, action in enumerate(chromosome.actions):
                action_result = {
                    'step': i,
                    'action': str(action),
                    'success': False,
                    'error': None
                }

                try:
                    # If the page has crashed, we can't continue
                    if results['crashed']:
                        raise Exception("Page crashed, cannot continue execution.")

                    self._execute_action(action)
                    action_result['success'] = True

                    self.page.wait_for_load_state('domcontentloaded', timeout=3000)

                    # Record new state
                    current_url = self.page.url
                    current_state = self._get_page_state()

                    if current_url not in results['urls']:
                        results['urls'].append(current_url)

                    if current_state not in results['states']:
                        results['states'].append(current_state)

                    if rescan_between_actions:
                        new_elements = self.crawler.scan_page(self.page)
                        results['available_elements'] = new_elements

                except Exception as e:
                    action_result['success'] = False
                    action_result['error'] = str(e)
                    results['execution_errors'].append({
                        'step': i,
                        'action': str(action),
                        'error': str(e)
                    })
                    results['action_results'].append(action_result)
                    # Stop executing this chromosome on the first failure
                    return results

                results['action_results'].append(action_result)

            return results

        finally:
            # Clean up listeners to avoid them stacking up on subsequent runs
            self.page.remove_listener('console', handle_console)
            self.page.remove_listener('response', handle_response)
            self.page.remove_listener('crash', handle_crash)


    def _execute_action(self, action: Action):
        """
        Execute a single action on the page.
        
        Raises:
            Exception: If action fails (element not found, timeout, etc.)
        """
        selector = self._get_selector(action.target) if action.target else None

        if action.action_type == ActionType.CLICK:
            if not selector:
                raise ValueError("CLICK action requires a target element")
            self.page.wait_for_selector(selector, timeout=3000)
            self.page.click(selector)

        elif action.action_type == ActionType.EDIT:
            if not selector:
                raise ValueError("EDIT action requires a target element")
            self.page.wait_for_selector(selector, timeout=3000)
            self.page.fill(selector, action.data or "")

        elif action.action_type == ActionType.SCROLL:
            if selector:
                self.page.locator(selector).scroll_into_view_if_needed()
            else:
                self.page.mouse.wheel(0, 500)

        else:
            raise ValueError(f"Unhandled action type: {action.action_type}")

    def _get_selector(self, ui_element: UIElement) -> str:
        """
        Generate CSS selector for a UIElement.
        Hierarchy: id > name > class_name > text_content
        """
        if ui_element.id:
            return f"#{ui_element.id}"

        if ui_element.name:
            return f"[name='{ui_element.name}']"

        if ui_element.class_name:
            return f".{'.'.join(ui_element.class_name.split())}"

        if ui_element.text_content:
            safe_text = ui_element.text_content.replace("'", "\\'")
            return f"text='{safe_text}'"

        raise ValueError("UIElement has no identifiable selector")

    def _get_page_state(self) -> str:
        """
        Create a hash representing the current page state.
        Used for detecting unique states during execution.
        """
        url = self.page.url
        html = self.page.content()
        state_str = f"{url}::{html}"
        return hashlib.md5(state_str.encode()).hexdigest()

    def get_current_elements(self) -> list[UIElement]:
        """Get all interactive elements on current page."""
        return self.crawler.scan_page(self.page)

    def reset(self):
        """Navigate back to starting URL."""
        self.page.goto(self.url)
        self.page.wait_for_load_state('networkidle')


# Test the runner
if __name__ == "__main__":
    url = "https://the-internet.herokuapp.com/login"
    print(f"Testing runner on {url}\n")

    runner = TestRunner(url, headless=False)
    runner.start()

    try:
        # First, see what elements are available
        elements = runner.get_current_elements()
        print(f"Found {len(elements)} elements:")
        for elem in elements:
            print(f"  {elem}")

        # Create a simple test chromosome
        username_input = UIElement(
            element_type=UIElementType.INPUT,
            id="username"
        )
        password_input = UIElement(
            element_type=UIElementType.INPUT,
            id="password"
        )
        login_button = UIElement(
            element_type=UIElementType.BUTTON,
            class_name="radius"
        )

        test_chromosome = Chromosome(actions=[
            Action(action_type=ActionType.EDIT, target=username_input, data="tomsmith"),
            Action(action_type=ActionType.EDIT, target=password_input, data="SuperSecretPassword!"),
            Action(action_type=ActionType.CLICK, target=login_button),
        ])

        print(f"\nRunning chromosome with {len(test_chromosome)} actions...")
        results = runner.run_chromosome(test_chromosome)

        print(f"\n--- Results ---")
        print(f"URLs visited: {results['urls']}")
        print(f"Unique states: {len(results['states'])}")
        print(f"Errors: {len(results['errors'])}")

        for action_result in results['action_results']:
            status = "✓" if action_result['success'] else "✗"
            print(f"  {status} Step {action_result['step']}: {action_result['action']}")
            if action_result['error']:
                print(f"      Error: {action_result['error']}")

    finally:
        runner.stop()

    print("\nDone!")