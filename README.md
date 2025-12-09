# AISE Project - Group 11
**Automated Web UI Testing using a Messy Genetic Algorithm**

This project attempts to automatically generate web UI test sequences using a Messy Genetic Algorithm.  
The system crawls a webpage, identifies interactable elements, evolves test chromosomes through selection–crossover–mutation, and evaluates them using fitness based on exploration, state diversity, and bug discovery.  
The output is an automatically generated high-value test scenario for real websites.

## Features
- Automatic crawling of interactable UI elements  
- Messy Genetic Algorithm with:
  - Context-aware crossover (cut & splice using page states)
  - Mutation (add / delete / insert actions)
  - Elitism & tournament selection
- Fitness based on:
  - Unique URLs and page states
  - JS/HTTP error detection
  - Sequence length penalty
- TestRunner using Playwright to safely execute chromosomes
- Code generator for exporting the best chromosome as a standalone test script

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
## System Workflow
Crawler → Initial Chromosomes → Messy GA → Runner Executes Chromosomes → Fitness Calculation → New Generation → Best Test

## How to Run

### Setup
Install dependencies
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
* Example websites for testing:  
https://the-internet.herokuapp.com/  
https://www.saucedemo.com/  
https://demoqa.com/  
https://automationexercise.com/

### Run Examples
```commandline
python main.py --url https://the-internet.herokuapp.com/ --generations 30 --population 40
```

### Output
After running, the GA prints:

- Best chromosome per generation  
- Final best chromosome  
- Fitness score  
- Action sequence  

* Example output:
CLICK link[text='Login']  
EDIT input[id='username']  
CLICK button[class='submit']

## Authors 
- Lasse Henrich  
- Johan Rönnquist  
- Hyokyung Kim  
- Seohyun Ahn  
_Created at KAIST, 2025._
