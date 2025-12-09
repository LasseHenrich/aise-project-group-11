#src/crawler.py

from playwright.sync_api import Page, Locator, sync_playwright
from typing import List, Optional

from src.chromosome import UIElement, UIElementType


class Crawler:
    """
    Scans a web page to identify interactable UI elements.
    """

    def scan_page(self, page: Page) -> List[UIElement]:
        """
        Scans a web page to identify interactable UI elements.
        Returns a list of UIElement instances.
        """
        found_elements: List[UIElement] = []

        # UIElementType to CSS selector
        mappings = [
            (UIElementType.BUTTON, "button, input[type='submit'], input[type='button']"),
            (UIElementType.INPUT, "input:not([type='submit']):not([type='button']), textarea"),
            (UIElementType.LINK, "a"),
        ]

        for element_type, selector in mappings:
            handles = page.query_selector_all(selector)

            for handle in handles:
                element_id = handle.get_attribute("id")
                element_name = handle.get_attribute("name")
                element_class = handle.get_attribute("class")
                element_text_content = handle.text_content()

                if not element_id and not element_name and\
                    not element_class and not element_text_content:
                    print("Warning: Found element without any identifiable attributes, skipping...")
                    continue

                ui_element = UIElement(
                    element_type=element_type,
                    id=element_id,
                    name=element_name,
                    class_name=element_class,
                    text_content=element_text_content
                )
                found_elements.append(ui_element)

        return found_elements


#Test the crawler
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
