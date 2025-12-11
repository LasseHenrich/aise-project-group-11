# main.py

import argparse
from src.ga import MessyGeneticAlgorithm
from src.code_gen import CodeGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Messy GA-based GUI test generation on a target website."
    )

    parser.add_argument(
        "--url",
        type=str,
        default="https://the-internet.herokuapp.com/",
        help="Target website URL to test.",
    )
    parser.add_argument(
        "--pop-size",
        type=int,
        default=50,
        help="Population size for the GA.",
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=50,
        help="Number of generations to run.",
    )
    parser.add_argument(
        "--tournament-size",
        type=int,
        default=5,
        help="Tournament size used in selection.",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=30,
        help="Maximum chromosome length.",
    )
    parser.add_argument(
        "--mutation-rate",
        type=float,
        default=1.0,
        help="Mutation rate (0.0-1.0).",
    )
    parser.add_argument(
        "--elitism",
        type=int,
        default=1,
        help="Number of top chromosomes carried over unchanged each generation.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=== Messy GA UI Test Runner ===")
    print(f"Target URL          : {args.url}")
    print(f"Population size     : {args.pop_size}")
    print(f"Generations         : {args.generations}")
    print(f"Tournament size     : {args.tournament_size}")
    print(f"Max chromosome len  : {args.max_length}")
    print(f"Mutation rate       : {args.mutation_rate}")
    print(f"Elitism count       : {args.elitism}")
    print()

    ga = MessyGeneticAlgorithm(
        url=args.url,
        population_size=args.pop_size,
        generations=args.generations,
        tournament_size=args.tournament_size,
        max_chromosome_length=args.max_length,
        mutation_rate=args.mutation_rate,
        elitism_count=args.elitism,
    )

    best_chromosome = ga.run()

    print("\n=== GA run complete ===")
    if best_chromosome and best_chromosome.fitness is not None:
        print(f"\nBest chromosome found: {best_chromosome}")
        print("Actions:")
        for i, action in enumerate(best_chromosome.actions):
            print(f"  Step {i+1}: {action}")

        print("\n=== Generating standalone Playwright test for best chromosome ===")
        generator = CodeGenerator(
            url=args.url,
            headless=False,  # if True: Doesn't show browser
            print_generated_code=True # if False: Doesn't print code
        )
        generated_code = generator.generate_code(best_chromosome)

        print("\n=== Replaying generated test script once ===\n")
        exec(generated_code)

    else:
        print("No effective chromosome was found.")


if __name__ == "__main__":
    main()
