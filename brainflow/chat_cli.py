"""CLI helper: run brainflow deep chat workflow for a single message.

Usage:
  python chat_cli.py "hello"

It runs workflows/chat_deep.yaml and prints the draft.
"""

from __future__ import annotations

import os
import sys

from core.engine import WorkflowEngine

# Make Windows console output robust
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python chat_cli.py <message>")
        raise SystemExit(2)

    base_dir = os.path.abspath(os.path.dirname(__file__))
    os.environ["BRAINFLOW_IN"] = sys.argv[1]

    # load goal into env
    goal_path = os.path.join(base_dir, "GOAL.md")
    if os.path.exists(goal_path):
        os.environ["BRAINFLOW_GOAL"] = open(goal_path, "r", encoding="utf-8").read()

    eng = WorkflowEngine(base_dir=base_dir)
    res = eng.run_from_file("workflows/chat_deep.yaml")
    # Print only the draft string for hook consumption
    draft = ""
    try:
        draft = res.get("vars", {}).get("draft", "")
    except Exception:
        draft = str(res)
    print(draft)


if __name__ == "__main__":
    main()
