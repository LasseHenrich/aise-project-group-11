from playwright.sync_api import Page, Locator, sync_playwright
from typing import List, Optional

from src.chromosome import UIElement, UIElementType


class Crawler:
    """
    Scans a web page to identify interactive UI elements.
    """

    def scan_page(self, page: Page) -> List[UIElement]:
        """
        Scans a web page to identify interactive UI elements.
        Returns a list of UIElement instances.
        """
        found_elements: List[UIElement] = []

        # UIElementType to CSS selector
        mappings = [
            (UIElementType.BUTTON, "button"),
            (UIElementType.INPUT, "input, textarea"),
            (UIElementType.LINK, "a"),
        ]

        for element_type, selector in mappings:
            handles = page.query_selector_all(selector)
            for handle in handles:
                element_id = handle.get_attribute("id") or ""
                element_class = handle.get_attribute("class") or ""

                if not element_id and not element_class:
                    print("Warning: Found element without id or class, which is currently not supported. Skipping...")
                    continue

                ui_element = UIElement(element_id, element_class, element_type)
                found_elements.append(ui_element)

        return found_elements

if __name__ == "__main__":
    url = "https://the-internet.herokuapp.com/login"
    print(f"Crawling {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        crawler = Crawler()
        elements = crawler.scan_page(page)

        print(f"\nFound {len(elements)} UI elements:")
        for element in elements:
            print(element)

        browser.close()