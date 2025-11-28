import copy
from types import CodeType

from chromosome import Chromosome, Action, UIElement, ActionType, UIElementType


class CodeGenerator:
    """
    Converts a chromosome into executable Playwright python code.
    """

    def __init__(self, url: str, headless: bool = True, print_generated_code: bool = False):
        self.url = url
        self.headless = headless
        self.print_generated_code = print_generated_code

    def generate_code(self, chromosome: Chromosome) -> CodeType:
        # imports and setup. Ref. playwright_setup_test.py
        lines = [
            f"from playwright.sync_api import sync_playwright",
            f"",
            f"with sync_playwright() as p:",
            f"    browser = p.chromium.launch(headless={self.headless})",
            f"    page = browser.new_page()",
            f"    page.goto('{self.url}')",
            ""
        ]

        # actions
        for action in chromosome:
            action_code_str = self._generate_action_code_str(action)
            for line in action_code_str.splitlines():
                lines.append(f"    {line}")

        # teardown
        lines.append("")
        lines.append(f"    page.wait_for_load_state('networkidle')") # ensure page is stable before closing
        lines.append(f"    browser.close()")

        # compile and return
        full_code_str = "\n".join(lines)
        if self.print_generated_code:
            print("\n" + "="*40 + "\n" + full_code_str + "\n" + "="*40 + "\n")
        compiled_code = compile(full_code_str, filename="<generated_code>", mode="exec")
        return compiled_code

    def _generate_action_code_str(self, action: Action) -> str:
        """
        Single action to code string
        """
        target_selector = self._get_selector(action.target) if action.target else None

        if action.action_type == ActionType.CLICK:
            if not target_selector:
                raise ValueError("CLICK action requires a target UIElement.")
            return f"page.click('{target_selector}')"

        if action.action_type == ActionType.EDIT:
            if not target_selector:
                raise ValueError("EDIT action requires a target UIElement.")

            data_content = action.data if action.data else ""
            return f"page.fill('{target_selector}', '{data_content}')"

        if action.action_type == ActionType.SCROLL:
            if not target_selector:
                return "page.mouse.wheel(0, 500)"
            return f"page.locator('{target_selector}').scroll_into_view_if_needed()"
            # todo: improve scroll handling by using content as custom scroll amount

        raise ValueError(f"Unhandled action type: {action.action_type}")

    def _get_selector(self, ui_element: UIElement) -> str:
        """
        Determines and returns the best selector for a UIElement.
        Hierarchy: id > name > class_name > text_content
        """
        if ui_element.id:
            return f"#{ui_element.id}"

        if ui_element.name:
            return f"[name='{ui_element.name}']"

        if ui_element.class_name:
            return f".{'.'.join(ui_element.class_name.split())}" # "class1 class2" -> ".class1.class2"

        if ui_element.text_content:
            safe_text_content = ui_element.text_content.replace("'", "\\'") # to avoid injection issues
            return f"text='{safe_text_content}'"

        raise ValueError("Unhandled case:\n"
                         "UIElement must have at least an id or a class name for selector generation.")


# Example usage
if __name__ == "__main__":
    input_user = UIElement(id="username", class_name="", element_type=UIElementType.INPUT)
    input_pass = UIElement(id="password", class_name="", element_type=UIElementType.INPUT)
    btn_login = UIElement(id="", class_name="radius", element_type=UIElementType.BUTTON)
    btn_logout = copy.copy(btn_login)
    success_message = UIElement(id="flash", class_name="flash success",
                                           element_type=UIElementType.LINK)

    a1 = Action(action_type=ActionType.EDIT, target=input_user, data="tomsmith")
    a2 = Action(action_type=ActionType.EDIT, target=input_pass, data="SuperSecretPassword!")
    a3 = Action(action_type=ActionType.CLICK, target=btn_login)
    a4 = Action(action_type=ActionType.CLICK, target=btn_logout)
    sample_chromosome = Chromosome(actions=[a1, a2, a3, a4])

    generator = CodeGenerator("https://the-internet.herokuapp.com/login", headless=False, print_generated_code=True)
    generated_code = generator.generate_code(sample_chromosome)

    print("Running generated Playwright code")
    exec(generated_code)
    print("DONE")