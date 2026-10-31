"""Measures how well search finds the right pages: recall@5 for vector, keyword and hybrid search.

Standard library only, against the running stack: `python3 backend/scripts/eval_search.py [FILE]`.
FILE (default `data/eval-search.json`) lists questions and the pages that answer them:

    [{"question": "Wann war ich beim Zahnarzt?", "pages": ["pg_01k7…"]}]

Keep it under `data/` (git-ignored): the questions come from your own pages. Reads `API_PORT`
(default 8000) and `API_TOKEN` (if the server needs one) from the environment.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE = f"http://localhost:{os.environ.get('API_PORT') or 8000}/api/v1"
MODES = ("vector", "keyword", "hybrid")
K = 5


def _search(question: str, mode: str) -> list[str]:
    """The IDs of the top `K` pages for the question."""
    query = urllib.parse.urlencode({"q": question, "mode": mode, "limit": K})
    request = urllib.request.Request(f"{BASE}/search?{query}")
    if token := os.environ.get("API_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return [hit["page"]["id"] for hit in json.load(response)["items"]]


def _recall(expected: list[str], found: list[str]) -> float:
    """The share of expected pages among the found ones."""
    return len(set(expected) & set(found)) / len(set(expected))


def main() -> int:
    parser = argparse.ArgumentParser(description="Recall@5 of each search mode.")
    parser.add_argument("file", nargs="?", type=Path, default=Path("data/eval-search.json"))
    parser.add_argument("-v", "--verbose", action="store_true", help="list each mode's misses")
    args = parser.parse_args()

    questions: list[dict[str, Any]] = json.loads(args.file.read_text())
    if not questions or any(not question["pages"] for question in questions):
        print(f"{args.file} needs questions, each with at least one page.")
        return 1

    print(f"{len(questions)} question(s) from {args.file}\n")
    print(f"{'mode':<8}  recall@{K}")
    for mode in MODES:
        recalls = []
        misses = []
        for question in questions:
            found = _search(question["question"], mode)
            recalls.append(_recall(question["pages"], found))
            if recalls[-1] < 1:
                missing = sorted(set(question["pages"]) - set(found))
                misses.append(f"  {question['question']}  (missing {', '.join(missing)})")
        print(f"{mode:<8}  {sum(recalls) / len(recalls):.2f}")
        if args.verbose and misses:
            print("\n".join(misses))
    return 0


if __name__ == "__main__":
    sys.exit(main())
