# AISE Project - Group 11
Automated Web UI Testing using Messy Genetic Algorithm

## Project Structure
```
.
└── src/
    ├── chromosome.py     # UI elements, actions, chromosomes
    ├── crawler.py        # Extract clickable elements from a webpage
    ├── runner.py         # Executes chromosomes in Playwright
    ├── ga.py             # Messy genetic algorithm
    └── code_gen.py       # Convert a chromosome into standalone test code
├── main.py           # Entry point for running the GA
├── playwright_setup_test.py
├── test_runner.py

```

## How to Run

### Setup
#### Install dependencies
```commandline
pip install -r requirements.txt
playwright install chromium
```

### Test setup
```commandline
python playwright_setup_test.py
```

### Run
```commandline
python main.py --url <test website url> --generations <size of generation> --population <size of population>
```
* Default generation size: 50
* Default population size: 50
* Example Websites for Testing:
https://the-internet.herokuapp.com/  
https://www.saucedemo.com/  
https://demoqa.com/  
https://automationexercise.com/
