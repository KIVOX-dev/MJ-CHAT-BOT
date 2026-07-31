"""
Offline MCQ dataset generator - hits a local Ollama instance to bulk-generate
aptitude questions and writes them to topic-wise JSON files.

This is a one-off data-authoring tool, not part of the running application
(nothing under backend/ imports it), so it lives outside backend/ rather
than inside backend/mcq_data/ - the questions.json/quantitative.json/
data_interpretation.json files that ARE loaded at runtime (by
backend/train_mcq.py) stay there; this generator that produces more data
like them does not.

Usage:
    python tools/generate_mcq.py --output-dir ./generated_mcq --batches 10
    python tools/generate_mcq.py --ollama-host http://localhost:11434 --model phi3
"""
import argparse
import json
import os
import time

import requests

DEFAULT_TOPICS = ["Reasoning", "Logical", "Quantitative", "Data Interpretation"]

PROMPT_TEMPLATE = """
Generate 5 aptitude MCQs on {topic}.

Return ONLY JSON array:
[
  {{
    "question": "...",
    "options": ["A","B","C","D"],
    "answer": "A",
    "explanation": "..."
  }}
]
"""


def generate_mcq(topic: str, ollama_host: str, model: str, request_timeout: float) -> list:
    prompt = PROMPT_TEMPLATE.format(topic=topic)

    response = requests.post(
        f"{ollama_host}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=request_timeout,
    )
    response.raise_for_status()
    text = response.json().get("response", "")

    print(f"\nRAW ({topic}):", text)

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        print("No JSON array found in model output")
        return []

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return []


def save_topic(output_dir: str, topic: str, new_data: list) -> None:
    file_path = os.path.join(output_dir, f"{topic.lower().replace(' ', '_')}.json")

    existing = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = []

    existing.extend(new_data)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    print(f"Saved {len(new_data)} items to {file_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--output-dir",
        default=os.getenv("MJ_MCQ_OUTPUT_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_mcq")),
        help="Directory to write topic-wise JSON files into (default: %(default)s, or $MJ_MCQ_OUTPUT_DIR).",
    )
    parser.add_argument(
        "--ollama-host",
        default=os.getenv("MJ_OLLAMA_HOST", "http://localhost:11434"),
        help="Base URL of a running Ollama instance (default: %(default)s, or $MJ_OLLAMA_HOST).",
    )
    parser.add_argument("--model", default="phi3", help="Ollama model to generate with (default: %(default)s).")
    parser.add_argument("--topics", nargs="+", default=DEFAULT_TOPICS, help="Topics to cycle through.")
    parser.add_argument("--batches", type=int, default=20, help="Number of generation batches to run (default: %(default)s).")
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Delay between batches (default: %(default)s).")
    parser.add_argument("--request-timeout", type=float, default=120.0, help="Per-request timeout in seconds (default: %(default)s).")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    for i in range(args.batches):
        topic = args.topics[i % len(args.topics)]
        print(f"\nBatch {i + 1}/{args.batches} | Topic: {topic}")

        data = generate_mcq(topic, args.ollama_host, args.model, args.request_timeout)
        if data:
            save_topic(args.output_dir, topic, data)
        else:
            print("Nothing saved for this batch")

        if i < args.batches - 1:
            time.sleep(args.sleep_seconds)

    print(f"\nDone. Files written to {args.output_dir}")


if __name__ == "__main__":
    main()
