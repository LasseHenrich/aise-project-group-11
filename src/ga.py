# src/ga.py
import copy
import random
from src.chromosome import Chromosome, Action, ActionType, UIElementType, PageState
from src.runner import TestRunner
from src.crawler import Crawler

class MessyGeneticAlgorithm:
    """
    Central GA class implementing a messy genetic algorithm.
    Potential todo: Add support for a "static" start action sequence, like a login, which is executed for every chromosome.
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
        self.runner = TestRunner(url, headless=True)
        self.crawler = Crawler()

    def _initialize_population(self):
        """
        Creates the initial population of chromosomes in two ways:
        1. By sampling single actions from the initial page.
        2. By performing random walks on the initial page to create short valid sequences,
        in case the initial page has fewer interactive elements than the desired population size.
        """
        print("Initializing population")
        initial_elements = self.runner.get_current_elements()

        for element in initial_elements:
            if element.element_type in [UIElementType.BUTTON, UIElementType.LINK]:
                self.population.append(Chromosome(actions=[Action(ActionType.CLICK, element)]))
            elif element.element_type == UIElementType.INPUT:
                self.population.append(Chromosome(actions=[Action(ActionType.EDIT, element, "test")]))

        attempts = 0
        max_attempts = self.population_size * 2
        while len(self.population) < self.population_size and attempts < max_attempts:
            chromosome = self._generate_chromosome_random_walk()
            if chromosome.actions:
                self.population.append(chromosome)
            attempts += 1
            # print(f"Generated new chromosome via random walk: {chromosome}")

        print(f"Initialized population with {len(self.population)} chromosomes.")

    def _generate_chromosome_random_walk(self) -> Chromosome:
        """
        Generates a chromosome through a random walk on a page,
        while ensuring that the sequence of actions is valid and executable.
        """

        self.runner.reset()
        actions = []

        walk_length = random.randint(2, min(5, max(2, self.max_chromosome_length // 2)))
        for _ in range(walk_length):
            elements = self.runner.get_current_elements()
            if not elements:
                break

            target = random.choice(elements)
            if target.element_type == UIElementType.INPUT:
                action = Action(ActionType.EDIT, target, "test")
            else:
                action = Action(ActionType.CLICK, target)

            try:
                self.runner.execute_action(action)
                self.runner.page.wait_for_load_state('domcontentloaded', timeout=3000)
                actions.append(action)
            except Exception: # action fails ~> stop walk and return what we have so far
                print('Action failed during random walk, stopping generation of this chromosome.')
                break

        return Chromosome(actions=actions)

    def _evaluate_chromosome(self):
        """
        Runs each chromosome and assigns a fitness score.
        - Highest reward for finding application bugs (JS/HTTP errors, crashes).
        - Zero reward for invalid test sequences (execution errors).
        - Standard reward for successful exploration (new states).
        Also stores discovered states for building block discovery.
        """
        print("Evaluating Chromosomes")
        for chromosome in self.population:
            self.runner.reset()
            results = self.runner.run_chromosome(chromosome)

            chromosome.all_states = self._gather_states_from_run(results)
            chromosome.fitness = self._calculate_fitness_from_run(chromosome, results)

    @staticmethod
    def _gather_states_from_run(run_results: dict) -> list[PageState]:
        initial_state = run_results['unique_states'][0]  # first state is the initial state
        action_results = run_results.get('action_results', [])
        resulting_states = []
        for action_result in action_results:
            state = action_result.get('resulting_state')
            resulting_states.append(state)
        return [initial_state] + resulting_states

    def _calculate_fitness_from_run(self, chromosome: Chromosome, run_results: dict) -> float:
        if run_results['crashed']: # there are many safeguards against crashes; these should only occur because of non-determinism
            return -1  # should not be selected for reproduction

        # Calculate base fitness from exploration (new states)
        base_fitness = len(run_results['unique_states']) * 50

        # Calculate bug bounty
        bug_bounty = 0

        for error in run_results.get("http_errors", []):
            status = error["status"]
            url = error["url"]

            if self._error_is_noise(url):
                continue

            if 500 <= status < 600:
                bug_bounty += 1000  # jackpot
            elif 400 <= status < 500:
                bug_bounty += 20  # broken links / bad requests...

        for error in run_results.get("js_errors", []):
            url = error["url"]

            if not self._error_is_noise(url):
                bug_bounty += 150  # actual JS (or CSS) crashes
            # otherwise probably blocked trackers again...

        len_penalty = -len(chromosome.actions) # low valuation, kind of functions as a tiebreaker

        fitness = base_fitness + bug_bounty + len_penalty
        return max(0, fitness)

    @staticmethod
    def _error_is_noise(url: str) -> bool:
        noise_patterns = [
            "google-analytics", "doubleclick", "facebook", "gtm",
            "fbevents", "pixel", "ads", "telemetry", "cors", "optimizely"
        ]
        return any(p in url.lower() for p in noise_patterns)

    def _selection(self) -> list[Chromosome]:
        """
        Selects the best chromosomes for reproduction using tournament selection.
        """
        print("Selecting parents")
        parents = []
        for _ in range(self.population_size):
            tournament = random.sample(self.population, self.tournament_size)
            winner = max(tournament, key=lambda x: x.fitness if x.fitness is not None else -1)
            parents.append(winner)
        return parents

    def _crossover(self, parent1: Chromosome, parent2: Chromosome) -> Chromosome:
        """
        Context-aware crossover ("cut and splice") between two parent chromosomes.
        Combines two parent chromosomes by finding a common state they both visited,
        ensuring that the second sequence of actions starts in a state where those actions are valid.
        """
        p1_states = {state.hash: idx for idx, state in enumerate(parent1.all_states)}
        p2_states = {state.hash: idx for idx, state in enumerate(parent2.all_states)}
        common_state_hashes = list(set(p1_states.keys()) & set(p2_states.keys()))

        if not common_state_hashes:
            # no common states ~> return a copy of one parent
            return copy.deepcopy(random.choice([parent1, parent2]))

        crossover_state_hash = random.choice(common_state_hashes)
        cut_point_p1 = p1_states[crossover_state_hash]
        cut_point_p2 = p2_states[crossover_state_hash]

        child_actions_head = parent1.actions[:cut_point_p1]
        child_actions_tail = parent2.actions[cut_point_p2:]

        child_actions = child_actions_head + child_actions_tail

        if len(child_actions) > self.max_chromosome_length:
            child_actions = child_actions[:self.max_chromosome_length]

        child = Chromosome(actions=child_actions)
        child.fitness = None # to be filled later during evaluation

        head_states = parent1.all_states[:cut_point_p1+1]
        tail_states = parent2.all_states[cut_point_p2+1:]
        child.all_states = head_states + tail_states

        return child

    # potential todo: experiment with different strategies / rates
    def _mutate(self, chromosome: Chromosome) -> Chromosome:
        """
        Applies random changes to a chromosome based on the mutation rate.
        """
        if random.random() > self.mutation_rate:
            return chromosome

        mutated_chromosome = copy.deepcopy(chromosome)
        actions = mutated_chromosome.actions
        states = mutated_chromosome.all_states

        # can only add if we have state info to know what is clickable
        can_add = len(states) > 0 # should always be true, but just in case...

        mutation_type = random.choice(['add', 'add', 'add', 'insert', 'delete']) if len(actions) > 1 else 'add'
        if (mutation_type == 'add' or mutation_type == 'insert') and not can_add:
            mutation_type = 'delete'

        if (mutation_type == 'add' or mutation_type == 'insert') and len(actions) < self.max_chromosome_length:
            insertion_point = random.randint(0, len(actions)-1) if mutation_type == 'insert' else len(actions)
            all_elements = states[insertion_point].available_elements
            if not all_elements:
                return mutated_chromosome # No elements to interact with

            new_element = random.choice(all_elements)
            if new_element.element_type in [UIElementType.BUTTON, UIElementType.LINK]:
                new_action = Action(ActionType.CLICK, new_element)
            elif new_element.element_type == UIElementType.INPUT:
                new_action = Action(ActionType.EDIT, new_element, "test")
            else:
                return mutated_chromosome # Should not happen

            actions.insert(insertion_point, new_action)
            mutated_chromosome.actions = actions[:insertion_point+1]

        elif mutation_type == 'delete' and actions:
            delete_point = random.randint(0, len(actions) - 1)
            # delete everything from delete_point to the end to maintain validity
            mutated_chromosome.actions = actions[:delete_point]

        # the expected states after this point are now invalid,
        # but that's fine as the runner will regenerate them during evaluation
        mutated_chromosome.all_states = []

        return mutated_chromosome

    def run(self):
        """
        Main evolutionary loop, entry point for this class
        """
        print("Starting Genetic Algorithm")
        self.runner.start()
        best_overall_chromosome = None

        self._initialize_population()

        for generation in range(self.generations):
            print(f"\n----- Generation {generation + 1}/{self.generations} -----")

            self._evaluate_chromosome()
            self.population.sort(key=lambda x: x.fitness if x.fitness is not None else -1, reverse=True)
            
            if self.population and self.population[0].fitness is not None:
                best_in_gen = self.population[0]
                if best_overall_chromosome is None or best_in_gen.fitness > (best_overall_chromosome.fitness or -1):
                    best_overall_chromosome = copy.deepcopy(best_in_gen)

                print(f"Best chromosome in generation: {best_in_gen}")
            else:
                print("Could not determine best chromosome in this generation.")

            if generation == self.generations - 1:
                break  # no need to create a new generation on the last iteration

            parents = self._selection()
            
            next_generation = []

            # carry over the best N chromosomes
            for i in range(min(self.elitism_count, len(self.population))):
                next_generation.append(copy.deepcopy(self.population[i]))

            # create the rest of the new generation
            while len(next_generation) < self.population_size:
                parent1 = random.choice(parents)
                parent2 = random.choice(parents)

                child = self._crossover(parent1, parent2)
                child = self._mutate(child)

                next_generation.append(child)
            
            self.population = next_generation

        print("\nGenetic Algorithm finished.")
        self.runner.stop()

        return best_overall_chromosome


# Example usage
# todo: Add a main.py file calling the genetic algorithm with a given URL and
# using code_gen to create an executable Playwright script from the best chromosome
if __name__ == "__main__":
    
    # potential todo: experiment with different hyperparameters
    ga = MessyGeneticAlgorithm(
        url="https://the-internet.herokuapp.com/",
        population_size=50,
        generations=50,
        mutation_rate=1.0
    )
    best_chromosome = ga.run()

    if best_chromosome and best_chromosome.fitness is not None:
        print(f"\nBest chromosome found: {best_chromosome}:")
    else:
        print("\nNo effective chromosome was found.")
