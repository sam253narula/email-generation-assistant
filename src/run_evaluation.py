from pathlib import Path
from generator import load_scenarios, save_generated_outputs
from evaluator import evaluate


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    scenarios = load_scenarios(root / "data" / "scenarios.json")
    save_generated_outputs(scenarios, root / "outputs" / "generated_outputs.json")
    evaluate(
        root / "outputs" / "generated_outputs.json",
        root / "outputs" / "evaluation_report.json",
        root / "outputs" / "evaluation_report.csv",
    )
    print("Done. See outputs/generated_outputs.json and outputs/evaluation_report.*")
