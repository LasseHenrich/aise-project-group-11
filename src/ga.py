# src/ga.py
import copy
import random
from src.chromosome import Chromosome, Action, ActionType, UIElementType
from src.runner import TestRunner
from src.crawler import Crawler

class GeneticAlgorithm:
    """
    Manages the evolutionary process of generating GUI tests.
    """

    def __init__(self, url: str, population_size: int = 50, generations: int = 100, tournament_size: int = 5, max_chromosome_length: int = 30, mutation_rate: float = 0.1, elitism_count: int = 1):
        self.url = url
        self.population_size = population_size
        self.generations = generations
        self.tournament_size = tournament_size
        self.max_chromosome_length = max_chromosome_length
        self.mutation_rate = mutation_rate
        self.elitism_count = elitism_count
        self.population: list[Chromosome] = []
        self.runner = TestRunner(url)
        self.crawler = Crawler()
        self.discovered_states = set()

    def _initialize_population(self):
        """
        Creates the initial population of chromosomes by creating a chromosome for each possible action on the page.
        ~> We start with single-action chromosomes.
        """
        print("Initializing population...")
        initial_elements = self.runner.get_current_elements()
        
        base_actions = []
        for element in initial_elements:
            if element.element_type == UIElementType.BUTTON or element.element_type == UIElementType.LINK:
                base_actions.append(Action(ActionType.CLICK, element))
            elif element.element_type == UIElementType.INPUT:
                # For input fields, we can add a default text
                base_actions.append(Action(ActionType.EDIT, element, "test"))

        if not base_actions:
            print("Warning: No initial actions discovered.")
            return

        while len(self.population) < self.population_size:
            action = random.choice(base_actions)
            self.population.append(Chromosome(actions=[action]))
        
        print(f"Initialized population with {len(self.population)} chromosomes.")

    def _evaluate_fitness(self):
        """
        Runs each chromosome and assigns a fitness score.
        - Highest reward for finding application bugs (JS/HTTP errors, crashes).
        - Zero reward for invalid test sequences (execution errors).
        - Standard reward for successful exploration (new states).
        """
        print("Evaluating fitness...")
        for chromosome in self.population:
            self.runner.reset()
            results = self.runner.run_chromosome(chromosome)
            
            # Calculate base fitness from novelty/exploration
            new_states_found = 0
            for state_hash in results['states']:
                if state_hash not in self.discovered_states:
                    new_states_found += 1
                    self.discovered_states.add(state_hash)
            base_fitness = new_states_found * 100

            # Calculate bug bounty
            application_errors = len(results.get('js_errors', [])) + len(results.get('http_errors', []))
            if results.get('crashed'):
                application_errors += 1
            bug_bounty = application_errors * 500

            if bug_bounty > 0:
                # Reward for finding a bug, and also for the exploration that led to it
                fitness = bug_bounty + base_fitness
            elif results.get('execution_errors'):
                # Zero fitness for tests that were invalid and found no bugs
                fitness = 0
            else:
                # Standard reward for successful runs, with a penalty for length
                fitness = base_fitness - len(chromosome.actions)

            chromosome.fitness = max(0, fitness)


    def _selection(self) -> list[Chromosome]:
        """
        Selects the best chromosomes for reproduction using tournament selection.
        """
        print("Selecting parents...")
        parents = []
        for _ in range(self.population_size):
            tournament = random.sample(self.population, self.tournament_size)
            winner = max(tournament, key=lambda x: x.fitness if x.fitness is not None else -1)
            parents.append(winner)
        return parents

    def _crossover(self, parent1: Chromosome, parent2: Chromosome) -> Chromosome:
        """
        Creates a child by splicing two parent chromosomes.
        """
        # It's important to deepcopy to avoid modifying the original parents' actions
        p1_actions = copy.deepcopy(parent1.actions)
        p2_actions = copy.deepcopy(parent2.actions)

        if not p1_actions:
            return Chromosome(actions=p2_actions)

        cut_point = random.randint(0, len(p1_actions))
        
        child_actions = p1_actions[:cut_point] + p2_actions

        # Truncate if the chromosome is too long
        if len(child_actions) > self.max_chromosome_length:
            child_actions = child_actions[:self.max_chromosome_length]

        return Chromosome(actions=child_actions)

    def _mutate(self, chromosome: Chromosome) -> Chromosome:
        """
        Applies random changes to a chromosome based on the mutation rate.
        """
        if random.random() > self.mutation_rate:
            return chromosome

        mutated_chromosome = copy.deepcopy(chromosome)
        actions = mutated_chromosome.actions

        if not actions and random.random() < 0.5: # 50% chance to add action if empty
             # try to add a new action
            all_elements = self.runner.get_current_elements()
            if not all_elements: return mutated_chromosome # No elements to interact with

            new_element = random.choice(all_elements)
            # Determine action type based on element type
            if new_element.element_type in [UIElementType.BUTTON, UIElementType.LINK]:
                new_action = Action(ActionType.CLICK, new_element)
            elif new_element.element_type == UIElementType.INPUT:
                new_action = Action(ActionType.EDIT, new_element, "mutated_text")
            else:
                return mutated_chromosome # Should not happen
            
            actions.append(new_action)
            return mutated_chromosome


        mutation_type = random.choice(['add', 'delete', 'modify'])

        if mutation_type == 'add' and len(actions) < self.max_chromosome_length:
            # Get available elements in the current state of the page (might need page context)
            # For simplicity, we'll just use the initial set of elements for now
            all_elements = self.runner.get_current_elements()
            if not all_elements: return mutated_chromosome # No elements to interact with

            new_element = random.choice(all_elements)
            # Determine action type based on element type
            if new_element.element_type in [UIElementType.BUTTON, UIElementType.LINK]:
                new_action = Action(ActionType.CLICK, new_element)
            elif new_element.element_type == UIElementType.INPUT:
                new_action = Action(ActionType.EDIT, new_element, "mutated_text")
            else:
                return mutated_chromosome # Should not happen

            insert_point = random.randint(0, len(actions))
            actions.insert(insert_point, new_action)

        elif mutation_type == 'delete' and actions:
            delete_point = random.randint(0, len(actions) - 1)
            del actions[delete_point]

        elif mutation_type == 'modify':
            # Find all 'edit' actions and modify one
            editable_actions = [a for a in actions if a.action_type == ActionType.EDIT]
            if editable_actions:
                action_to_modify = random.choice(editable_actions)
                action_to_modify.data = f"random_{random.randint(1, 1000)}"

        return mutated_chromosome

    def run(self):
        """
        Main evolutionary loop.
        """
        print("Starting Genetic Algorithm...")
        self.runner.start()
        best_overall_chromosome = None

        self._initialize_population()

        for generation in range(self.generations):
            print(f"\n----- Generation {generation + 1}/{self.generations} -----")

            self._evaluate_fitness()

            # Sort population by fitness, descending
            self.population.sort(key=lambda x: x.fitness if x.fitness is not None else -1, reverse=True)
            
            if self.population and self.population[0].fitness is not None:
                best_in_gen = self.population[0]
                if best_overall_chromosome is None or best_in_gen.fitness > (best_overall_chromosome.fitness or -1):
                    best_overall_chromosome = copy.deepcopy(best_in_gen)

                print(f"Best fitness in generation: {best_in_gen.fitness:.2f} | Length: {len(best_in_gen.actions)}")
            else:
                print("Could not determine best chromosome in this generation.")


            parents = self._selection()
            
            next_generation = []

            # Elitism: carry over the best N chromosomes
            if self.population:
                for i in range(min(self.elitism_count, len(self.population))):
                    next_generation.append(copy.deepcopy(self.population[i]))

            # Create the rest of the new generation
            while len(next_generation) < self.population_size:
                parent1 = random.choice(parents)
                parent2 = random.choice(parents)

                child = self._crossover(parent1, parent2)
                
                child = self._mutate(child)

                next_generation.append(child)
            
            self.population = next_generation

        print("\nGenetic Algorithm finished.")
        if best_overall_chromosome and best_overall_chromosome.fitness is not None:
            print(f"\nBest chromosome found with fitness {best_overall_chromosome.fitness:.2f}:")
            for i, action in enumerate(best_overall_chromosome.actions):
                print(f"  Step {i+1}: {action}")
        else:
            print("\nNo effective chromosome was found.")
            
        self.runner.stop()

if __name__ == "__main__":
    # Example of how to run the GA
    ga = GeneticAlgorithm(
        url="https://the-internet.herokuapp.com/login",
        population_size=50,
        generations=10
    )
    ga.run()
