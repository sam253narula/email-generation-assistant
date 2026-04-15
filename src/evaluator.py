from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from statistics import mean
from typing import Dict, List


GREETING_PATTERNS = [r"^Dear .+,", r"^Hi .+,", r"^Hello,", r"^Hello .+,", r"^Hi Team,", r"^Dear Team,"]
CLOSING_PATTERNS = [r"Best regards,", r"Kind regards,", r"Regards,", r"Best,", r"Sincerely,", r"With appreciation,", r"Thanks for your prompt attention."]

TONE_KEYWORDS = {
    "formal": ["thank you", "appreciate", "please", "best regards"],
    "professional": ["confirm", "review", "agenda", "best regards"],
    "polite": ["could", "thank you", "understanding", "kind regards"],
    "empathetic": ["sorry", "patience", "understanding", "glad"],
    "urgent": ["urgent", "immediate", "as soon as possible", "today"],
    "warm": ["appreciate", "valuable", "stay in touch", "with appreciation"],
    "respectful": ["thank you", "consideration", "sincerely", "happy to reconnect"],
    "clear": ["follow up", "required", "deadline", "questions"],
    "celebratory": ["happy", "glad", "thank you all", "celebration"],
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def fact_coverage_score(email: str, facts: List[str]) -> float:
    email_n = normalize(email)
    covered = 0
    for fact in facts:
        tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", fact.lower()) if len(t) > 3]
        if not tokens:
            continue
        overlap = sum(1 for t in tokens if t in email_n)
        if overlap / len(tokens) >= 0.6:
            covered += 1
    return round(covered / len(facts), 3)


def tone_alignment_score(email: str, tone: str) -> float:
    email_n = normalize(email)
    keywords = TONE_KEYWORDS[tone]
    hits = sum(1 for kw in keywords if kw in email_n)
    base = hits / len(keywords)
    penalty = 0.0
    if tone == "urgent" and len(email.split()) > 170:
        penalty += 0.1
    if tone == "formal" and "hello," in email_n:
        penalty += 0.15
    if tone == "celebratory" and "sorry" in email_n:
        penalty += 0.15
    return round(max(0.0, min(1.0, base - penalty)), 3)


def structure_fluency_score(email: str) -> float:
    score = 0.0
    lines = [line.strip() for line in email.splitlines() if line.strip()]
    if lines and lines[0].lower().startswith("subject:"):
        score += 0.2
    if any(re.match(pat, lines[1]) for pat in GREETING_PATTERNS) if len(lines) > 1 else False:
        score += 0.25
    if any(re.search(pat, email) for pat in CLOSING_PATTERNS):
        score += 0.25
    word_count = len(re.findall(r"\b\w+\b", email))
    if 80 <= word_count <= 190:
        score += 0.15
    paragraphs = email.strip().split("\n\n")
    if len(paragraphs) >= 4:
        score += 0.15
    return round(score, 3)


def evaluate(generated_path: str | Path, report_json: str | Path, report_csv: str | Path) -> Dict:
    records = json.loads(Path(generated_path).read_text())
    rows: List[Dict] = []

    for item in records:
        for model_name, email_key in [("advanced_prompt", "advanced_email"), ("baseline_prompt", "baseline_email")]:
            email = item[email_key]
            m1 = fact_coverage_score(email, item["key_facts"])
            m2 = tone_alignment_score(email, item["tone"])
            m3 = structure_fluency_score(email)
            overall = round(mean([m1, m2, m3]), 3)
            rows.append(
                {
                    "scenario_id": item["id"],
                    "model": model_name,
                    "intent": item["intent"],
                    "tone": item["tone"],
                    "fact_coverage_score": m1,
                    "tone_alignment_score": m2,
                    "structure_fluency_score": m3,
                    "overall_score": overall,
                }
            )

    metric_definitions = {
        "fact_coverage_score": "Measures how many required facts are present in the generated email using token overlap against each fact. Score = covered facts / total facts.",
        "tone_alignment_score": "Measures how well the email matches the requested tone using tone-specific lexical cues and small penalties for mismatched style.",
        "structure_fluency_score": "Measures whether the email contains a subject line, greeting, closing, acceptable length, and paragraph structure."
    }

    summary = {}
    for model in sorted(set(r["model"] for r in rows)):
        model_rows = [r for r in rows if r["model"] == model]
        summary[model] = {
            "avg_fact_coverage_score": round(mean(r["fact_coverage_score"] for r in model_rows), 3),
            "avg_tone_alignment_score": round(mean(r["tone_alignment_score"] for r in model_rows), 3),
            "avg_structure_fluency_score": round(mean(r["structure_fluency_score"] for r in model_rows), 3),
            "avg_overall_score": round(mean(r["overall_score"] for r in model_rows), 3),
        }

    report = {
        "metric_definitions": metric_definitions,
        "scenario_scores": rows,
        "summary": summary,
    }

    Path(report_json).write_text(json.dumps(report, indent=2))
    with open(report_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    report = evaluate(
        root / "outputs" / "generated_outputs.json",
        root / "outputs" / "evaluation_report.json",
        root / "outputs" / "evaluation_report.csv",
    )
    print(json.dumps(report["summary"], indent=2))
