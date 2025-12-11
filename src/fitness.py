# src/fitness.py
# delete

from typing import Dict, Any

from src.chromosome import Chromosome


class FitnessCalculator:
    """
    Fitness for a Chromosome based on:
      - Exploration / coverage: unique URLs and UI states
      - Bug discovery: sequences that trigger errors/bugs
      - Redundancy / efficiency: penalize overly long sequences

    Expected execution_result (from TestRunner.run_chromosome):
        {
            "urls": List[str],
            "states": List[str],
            "errors": List[Any],
            "action_results": List[dict],
        }
    """
    
    def __init__(
        self,
        w_exploration: float = 1.0,
        w_bug: float = 2.0,
        w_redundancy: float = 0.2,
        length_threshold: int = 5,
        bug_cap: int = 3,
    ) -> None:
        # how important each component is
        self.w_exploration = w_exploration
        self.w_bug = w_bug
        self.w_redundancy = w_redundancy

        # configuration
        self.length_threshold = length_threshold
        self.bug_cap = bug_cap  # limit how much we reward many errors

    def evaluate(self, chrom: Chromosome, execution_result: Dict[str, Any]) -> float:
        urls = execution_result.get("urls", [])
        states = execution_result.get("states", [])
        errors = execution_result.get("errors", [])

        unique_url_count = len(set(urls))
        unique_state_count = len(set(states))
        error_count = len(errors)
        seq_len = len(chrom.actions)

        # 1) Exploration: more unique URLs/states = better
        exploration_score = unique_url_count + 1.5 * unique_state_count

        # 2) Bug discovery: reward sequences that trigger errors (up to a cap)
        bug_score = min(error_count, self.bug_cap)

        # 3) Redundancy / efficiency: penalize long sequences beyond a threshold
        extra_length = max(0, seq_len - self.length_threshold)
        redundancy_penalty = extra_length

        fitness = (
            self.w_exploration * exploration_score
            + self.w_bug * bug_score
            - self.w_redundancy * redundancy_penalty
        )

        chrom.fitness = fitness
        return fitness
