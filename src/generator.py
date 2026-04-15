from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from prompts import ADVANCED_SYSTEM_PROMPT, ADVANCED_USER_TEMPLATE, BASELINE_PROMPT, FEW_SHOT_EXAMPLE

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


@dataclass
class Scenario:
    id: int
    intent: str
    tone: str
    key_facts: List[str]
    reference_email: str


TONE_OPENERS = {
    "formal": "I hope you are doing well.",
    "professional": "I hope you are doing well.",
    "polite": "I hope you are well.",
    "empathetic": "Thank you for your patience.",
    "urgent": "I’m reaching out because this needs immediate attention.",
    "warm": "I hope you’ve been well.",
    "respectful": "Thank you for your time and consideration.",
    "clear": "I wanted to follow up with a quick update.",
    "celebratory": "I’m glad to share a positive update.",
}

TONE_CLOSERS = {
    "formal": "Best regards,",
    "professional": "Best regards,",
    "polite": "Kind regards,",
    "empathetic": "Best,",
    "urgent": "Thanks for your prompt attention.",
    "warm": "With appreciation,",
    "respectful": "Sincerely,",
    "clear": "Regards,",
    "celebratory": "Best,",
}


def load_scenarios(path: str | Path) -> List[Scenario]:
    data = json.loads(Path(path).read_text())
    return [Scenario(**item) for item in data]


def subject_from_intent(intent: str) -> str:
    normalized = intent[0].upper() + intent[1:] if intent else "Email Update"
    return normalized.replace("a ", "").replace("an ", "")


def advanced_prompt_preview(s: Scenario) -> str:
    facts = "\n".join(f"- {fact}" for fact in s.key_facts)
    return (
        f"SYSTEM:\n{ADVANCED_SYSTEM_PROMPT}\n\n"
        f"FEW-SHOT INPUT:\nIntent: {FEW_SHOT_EXAMPLE['input']['intent']}\n"
        f"Tone: {FEW_SHOT_EXAMPLE['input']['tone']}\n"
        f"Facts: {FEW_SHOT_EXAMPLE['input']['facts']}\n\n"
        f"FEW-SHOT OUTPUT:\n{FEW_SHOT_EXAMPLE['output']}\n\n"
        f"USER:\n{ADVANCED_USER_TEMPLATE.format(intent=s.intent, tone=s.tone, facts=facts)}"
    )


def baseline_prompt_preview(s: Scenario) -> str:
    return BASELINE_PROMPT.format(
        intent=s.intent,
        tone=s.tone,
        facts="; ".join(s.key_facts),
    )


def deterministic_advanced_email(s: Scenario) -> str:
    greeting = "Dear Team," if s.tone in {"formal", "professional"} else "Hi Team,"
    if any(word in s.intent.lower() for word in ["client", "vendor", "customer", "hiring manager", "mentor"]):
        greeting = {
            "formal": "Dear Sir or Madam,",
            "professional": "Dear Client Team,",
            "polite": "Dear Hiring Manager,",
            "warm": "Hi Priya,",
            "clear": "Hello,",
            "respectful": "Dear Alex,",
        }.get(s.tone, greeting)
    if "internal stakeholder" in s.intent.lower():
        greeting = "Hi Jordan,"

    opener = TONE_OPENERS.get(s.tone, "I hope you are doing well.")
    facts = [fact.rstrip(".") + "." for fact in s.key_facts]
    while len(facts) < 3:
        facts.append("")

    body_parts = [
        opener,
        f"I’m writing regarding {s.intent.lower()}. {facts[0]}",
        facts[1],
        facts[2],
    ]

    if s.tone == "urgent":
        body_parts[1] = f"I’m writing with an urgent request regarding {s.intent.lower()}. {facts[0]}"
    elif s.tone == "celebratory":
        body_parts[1] = f"I’m happy to share an update related to {s.intent.lower()}. {facts[0]}"
    elif s.tone == "empathetic":
        body_parts[1] = f"I wanted to follow up regarding {s.intent.lower()}. {facts[0]}"

    closing_line = {
        "urgent": "Please let me know as soon as possible if anything needs clarification.",
        "warm": "I truly appreciate your support.",
        "celebratory": "Thank you all for the strong collaboration.",
    }.get(s.tone, "Please let me know if you have any questions.")

    return (
        f"Subject: {subject_from_intent(s.intent)}\n\n"
        f"{greeting}\n\n"
        f"{' '.join(part for part in body_parts if part).strip()}\n\n"
        f"{closing_line}\n\n"
        f"{TONE_CLOSERS.get(s.tone, 'Best regards,')}\n"
        f"Samarth"
    )


def deterministic_baseline_email(s: Scenario) -> str:
    first_two = " ".join(fact.rstrip(".") + "." for fact in s.key_facts[:2])
    return (
        f"Subject: {subject_from_intent(s.intent)}\n\n"
        f"Hello,\n\n"
        f"This email is about {s.intent.lower()}. {first_two}"
        f"\n\nThanks,\nSamarth"
    )


def build_single_scenario(intent: str, tone: str, facts: List[str]) -> Scenario:
    return Scenario(
        id=0,
        intent=intent,
        tone=tone,
        key_facts=facts,
        reference_email="",
    )


def get_openai_client(api_key: Optional[str] = None, base_url: Optional[str] = None):
    if OpenAI is None:
        raise RuntimeError("The openai package is not installed. Run: pip install openai")

    resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Export it before using --use-llm.")

    client_kwargs = {"api_key": resolved_api_key}
    resolved_base_url = base_url or os.getenv("OPENAI_BASE_URL")
    if resolved_base_url:
        client_kwargs["base_url"] = resolved_base_url

    return OpenAI(**client_kwargs)


def call_llm(prompt_text: str, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> str:
    client = get_openai_client(api_key=api_key, base_url=base_url)
    response = client.responses.create(
        model=model,
        input=prompt_text,
    )
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text.strip()

    try:
        return str(response.output[0].content[0].text).strip()
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Could not extract text from model response: {exc}") from exc


def generate_email_advanced(
    s: Scenario,
    use_llm: bool = False,
    model: str = "gpt-5.4",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    if use_llm:
        return call_llm(
            prompt_text=advanced_prompt_preview(s),
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
    return deterministic_advanced_email(s)


def generate_email_baseline(
    s: Scenario,
    use_llm: bool = False,
    model: str = "gpt-5.4",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    if use_llm:
        return call_llm(
            prompt_text=baseline_prompt_preview(s),
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
    return deterministic_baseline_email(s)


def save_generated_outputs(
    scenarios: List[Scenario],
    out_path: str | Path,
    use_llm: bool = False,
    model: str = "gpt-5.4",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> None:
    records: List[Dict] = []
    for s in scenarios:
        records.append(
            {
                "id": s.id,
                "intent": s.intent,
                "tone": s.tone,
                "key_facts": s.key_facts,
                "reference_email": s.reference_email,
                "advanced_email": generate_email_advanced(
                    s, use_llm=use_llm, model=model, api_key=api_key, base_url=base_url
                ),
                "baseline_email": generate_email_baseline(
                    s, use_llm=use_llm, model=model, api_key=api_key, base_url=base_url
                ),
                "advanced_prompt_preview": advanced_prompt_preview(s),
                "baseline_prompt_preview": baseline_prompt_preview(s),
                "generation_mode": "llm" if use_llm else "deterministic",
                "model": model if use_llm else "deterministic-template",
            }
        )
    Path(out_path).write_text(json.dumps(records, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Email generation assistant")
    parser.add_argument("--use-llm", action="store_true", help="Use a real OpenAI model instead of deterministic templates")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-5.4"), help="Model name to use with the OpenAI Responses API")
    parser.add_argument("--api-key", default=None, help="Optional API key override; otherwise uses OPENAI_API_KEY")
    parser.add_argument("--base-url", default=None, help="Optional API base URL override; otherwise uses OPENAI_BASE_URL")

    parser.add_argument("--strategy", choices=["advanced", "baseline"], default="advanced", help="Strategy for single-email generation mode")
    parser.add_argument("--intent", default=None, help="Single-email mode: email intent")
    parser.add_argument("--tone", default=None, help="Single-email mode: tone")
    parser.add_argument("--facts", nargs="*", default=None, help="Single-email mode: one or more facts")
    parser.add_argument("--output", default=None, help="Optional output file path for single-email mode")

    return parser.parse_args()


def run_single_email(args: argparse.Namespace) -> str:
    if not args.intent or not args.tone or not args.facts:
        raise RuntimeError(
            "For single-email mode, provide --intent, --tone, and at least one value in --facts."
        )

    scenario = build_single_scenario(args.intent, args.tone, args.facts)
    if args.strategy == "advanced":
        email = generate_email_advanced(
            scenario,
            use_llm=args.use_llm,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
        )
    else:
        email = generate_email_baseline(
            scenario,
            use_llm=args.use_llm,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
        )

    if args.output:
        Path(args.output).write_text(email)
    return email


if __name__ == "__main__":
    args = parse_args()
    root = Path(__file__).resolve().parents[1]

    if args.intent or args.tone or args.facts:
        email = run_single_email(args)
        print(email)
    else:
        scenarios = load_scenarios(root / "data" / "scenarios.json")
        save_generated_outputs(
            scenarios=scenarios,
            out_path=root / "outputs" / "generated_outputs.json",
            use_llm=args.use_llm,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
        )
        mode = "LLM" if args.use_llm else "deterministic"
        print(f"Generated outputs written to outputs/generated_outputs.json using {mode} mode.")
