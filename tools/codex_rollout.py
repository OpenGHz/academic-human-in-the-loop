#!/usr/bin/env python3
"""codex_rollout.py — read one completed turn of a Codex session from its rollout file.

Codex records every session in ``$CODEX_HOME/sessions/YYYY/MM/DD/rollout-*-<thread id>.jsonl``
(``CODEX_HOME`` defaults to ``~/.codex``). For a reviewer called through Codex MCP,
that file holds the exact prompt the executor sent, the reviewer's final reply, and
the model and effort the Codex client configured for the turn (``turn_context``;
not a backend report of the model that answered). ``save_trace.sh --codex-rollout`` uses this
helper so traces store the reviewer's own text instead of an executor's copy of it.

CLI:

    python3 codex_rollout.py turn --thread-id <id> [--turn-index -1] [--codex-home DIR]

prints one JSON object:

    {"thread_id", "turn_id", "rollout_path", "model", "effort", "sandbox",
     "prompt", "response"}

Exit status 1 (with a message on stderr) when the rollout is missing, the turn
index is out of range, or the turn has not completed — an unfinished turn is
not a review.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

THREAD_ID_RE = re.compile(r"^[0-9A-Za-z-]+$")
ENVIRONMENT_CONTEXT = "<environment_context>"


class RolloutError(Exception):
    pass


def codex_home(explicit: str | None) -> Path:
    return Path(explicit or os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def find_rollout(thread_id: str, home: Path) -> Path:
    if not THREAD_ID_RE.match(thread_id):
        raise RolloutError(f"not a Codex thread id: {thread_id!r}")
    matches = sorted((home / "sessions").glob(f"**/rollout-*-{thread_id}.jsonl"))
    if not matches:
        raise RolloutError(f"no rollout for thread {thread_id} under {home / 'sessions'}")
    if len(matches) > 1:
        raise RolloutError(f"several rollouts for thread {thread_id}: {[str(m) for m in matches]}")
    return matches[0]


def _text(content: Any) -> str:
    return "".join(
        part.get("text", "") for part in content or [] if isinstance(part, dict)
    )


def read_turns(path: Path) -> list[dict[str, Any]]:
    """Turns in order, each with its prompt, final reply, model and completion state."""
    turns: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = event.get("type")
            payload = event.get("payload") or {}
            ptype = payload.get("type")
            if kind == "event_msg" and ptype == "task_started":
                current = {
                    "turn_id": payload.get("turn_id"), "model": None, "effort": None,
                    "sandbox": None, "prompt_parts": [], "response": None, "completed": False,
                }
                turns.append(current)
                by_id[current["turn_id"]] = current
            elif current is None:
                continue
            elif kind == "turn_context":
                current["model"] = current["model"] or payload.get("model")
                current["effort"] = current["effort"] or payload.get("effort")
                current["sandbox"] = current["sandbox"] or (payload.get("sandbox_policy") or {}).get("type")
            elif kind == "response_item" and ptype == "message" and payload.get("role") == "user":
                text = _text(payload.get("content"))
                if not text.lstrip().startswith(ENVIRONMENT_CONTEXT):
                    current["prompt_parts"].append(text)
            elif kind == "event_msg" and ptype == "task_complete":
                turn = by_id.get(payload.get("turn_id"), current)
                turn["response"] = payload.get("last_agent_message")
                turn["completed"] = True
    for turn in turns:
        turn["prompt"] = "\n\n".join(turn.pop("prompt_parts"))
    return turns


def read_turn(thread_id: str, turn_index: int = -1, home: Path | None = None) -> dict[str, Any]:
    path = find_rollout(thread_id, home or codex_home(None))
    turns = read_turns(path)
    if not turns:
        raise RolloutError(f"{path} has no turns")
    try:
        turn = turns[turn_index]
    except IndexError:
        raise RolloutError(f"{path} has {len(turns)} turns; index {turn_index} is out of range") from None
    if not turn["completed"] or turn["response"] is None:
        raise RolloutError(f"turn {turn['turn_id']} in {path} has not completed")
    return {"thread_id": thread_id, "rollout_path": str(path), **turn}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    turn = sub.add_parser("turn", help="print one completed turn as JSON")
    turn.add_argument("--thread-id", required=True)
    turn.add_argument("--turn-index", type=int, default=-1, help="0-based; negative counts from the end")
    turn.add_argument("--codex-home")
    args = parser.parse_args(argv)
    try:
        result = read_turn(args.thread_id, args.turn_index, codex_home(args.codex_home))
    except RolloutError as exc:
        print(f"codex_rollout: {exc}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
