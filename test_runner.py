# test_runner.py

from src.runner import TestRunner
from src.chromosome import Chromosome, Action, ActionType, UIElement, UIElementType


def test_saucedemo():
    """Test on SauceDemo website"""
    url = "https://www.saucedemo.com/"
    print(f"\n{'='*50}")
    print(f"Testing on: {url}")
    print('='*50)

    runner = TestRunner(url, headless=False)
    runner.start()

    try:
        elements = runner.get_current_elements()
        print(f"\nFound {len(elements)} elements:")
        for elem in elements:
            print(f"  {elem}")

        # SauceDemo login
        username_input = UIElement(element_type=UIElementType.INPUT, id="user-name")
        password_input = UIElement(element_type=UIElementType.INPUT, id="password")
        login_btn = UIElement(element_type=UIElementType.INPUT, id="login-button")

        test_chromosome = Chromosome(actions=[
            Action(action_type=ActionType.EDIT, target=username_input, data="standard_user"),
            Action(action_type=ActionType.EDIT, target=password_input, data="secret_sauce"),
            Action(action_type=ActionType.CLICK, target=login_btn),
        ])

        print(f"\nRunning {len(test_chromosome)} actions...")
        results = runner.run_chromosome(test_chromosome)

        print(f"\n--- Results ---")
        print(f"URLs: {results['urls']}")
        print(f"States: {len(results['states'])}")
        print(f"Errors: {len(results['errors'])}")

        for r in results['action_results']:
            status = "✓" if r['success'] else "✗"
            print(f"  {status} {r['action']}")
            if r['error']:
                print(f"      Error: {r['error']}")

    finally:
        runner.stop()


if __name__ == "__main__":
    test_saucedemo()
    print("\nTest complete!")