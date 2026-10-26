"""save_trace.sh --codex-rollout copies the reviewer's turn from Codex's session file.

A novelty-check trace once held the executor's summary of a Codex review
instead of the review itself; the raw reply was in ~/.codex/sessions all along.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TRACE_SCRIPT = ROOT / "tools" / "save_trace.sh"
HELPER = ROOT / "tools" / "codex_rollout.py"
THREAD = "01a17779-7dab-7c10-9e2a-1652d45b63a3"


def _event(kind: str, payload: dict | None = None) -> str:
    return json.dumps({"timestamp": "2026-10-26T09:10:13Z", "type": kind, "payload": payload or {}})


def _turn(turn_id: str, prompt: str, reply: str | None, model: str = "gpt-6-astra") -> list[str]:
    lines = [
        _event("event_msg", {"type": "task_started", "turn_id": turn_id}),
        _event("response_item", {"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": "<environment_context>\n  <cwd>/p</cwd>\n</environment_context>"}]}),
        _event("turn_context", {"turn_id": turn_id, "model": model, "effort": "xhigh",
                                "sandbox_policy": {"type": "read-only"}}),
        _event("response_item", {"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": prompt}]}),
        _event("response_item", {"type": "message", "role": "assistant", "content": [
            {"type": "output_text", "text": "I'll read the files first."}]}),
    ]
    if reply is not None:
        lines.append(_event("event_msg", {"type": "task_complete", "turn_id": turn_id,
                                          "last_agent_message": reply}))
    return lines


def _codex_home(tmp_path: Path, *turns: list[str]) -> Path:
    home = tmp_path / "codex"
    day = home / "sessions" / "2026" / "10" / "26"
    day.mkdir(parents=True)
    lines = [_event("session_meta", {"id": THREAD})] + [line for turn in turns for line in turn]
    (day / f"rollout-2026-10-26T17-10-13-{THREAD}.jsonl").write_text("\n".join(lines) + "\n")
    return home


def _save(tmp_path: Path, home: Path, *args: str) -> subprocess.CompletedProcess:
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    return subprocess.run(
        ["bash", str(TRACE_SCRIPT), "--skill", "novelty-check", "--purpose", "review",
         "--model", "gpt-6-astra", "--thread-id", THREAD, *args],
        cwd=project, text=True, capture_output=True, env={**os.environ, "CODEX_HOME": str(home)},
    )


def _saved(tmp_path: Path) -> tuple[dict, str]:
    run_dir = next((tmp_path / "project" / ".aris" / "traces" / "novelty-check").iterdir())
    request = sorted(run_dir.glob("*.request.json"))[-1]
    response = request.with_name(request.name.replace(".request.json", ".response.md"))
    meta = request.with_name(request.name.replace(".request.json", ".meta.json"))
    return {**json.loads(meta.read_text()), "prompt": json.loads(request.read_text())["prompt"]}, response.read_text()


def test_trace_holds_the_reviewers_own_text_and_reported_model(tmp_path: Path) -> None:
    reply = "**7/10, PROCEED.**\n\n| Claim | Closest |\n|---|---|\n| C1 | [Bruder](https://arxiv.org/abs/2010.09961) |"
    home = _codex_home(tmp_path, _turn("t1", "Read the dossier at /p/D.md.", reply))

    result = _save(tmp_path, home, "--codex-rollout")

    assert result.returncode == 0, result.stderr
    meta, response = _saved(tmp_path)
    assert response == reply
    # save_trace.sh stores every prompt with a trailing newline (its here-string).
    assert meta["prompt"] == "Read the dossier at /p/D.md.\n"  # environment block left out
    assert meta["model"] == "gpt-6-astra"
    assert meta["effort"] == "xhigh"


def test_latest_turn_by_default_and_index_selects_another(tmp_path: Path) -> None:
    home = _codex_home(tmp_path, _turn("t1", "Round 1.", "first"), _turn("t2", "Round 2.", "second"))

    assert _save(tmp_path, home, "--codex-rollout").returncode == 0
    assert _saved(tmp_path)[1] == "second"
    assert _save(tmp_path, home, "--codex-rollout", "--codex-turn-index", "0").returncode == 0
    assert _saved(tmp_path)[1] == "first"


def test_unfinished_turn_is_refused(tmp_path: Path) -> None:
    home = _codex_home(tmp_path, _turn("t1", "Round 1.", None))

    result = _save(tmp_path, home, "--codex-rollout")

    assert result.returncode != 0
    assert "has not completed" in result.stderr


def test_rollout_and_a_caller_response_cannot_both_be_given(tmp_path: Path) -> None:
    home = _codex_home(tmp_path, _turn("t1", "Round 1.", "reply"))

    result = _save(tmp_path, home, "--codex-rollout", "--response", "my summary")

    assert result.returncode != 0
    assert "replaces" in result.stderr


def test_configured_model_stays_requested_and_cannot_grant_acceptance(tmp_path: Path) -> None:
    """turn_context is the client's configuration, not a backend report."""
    home = _codex_home(tmp_path, _turn("t1", "Round 1.", "reply", model="gpt-6.1-sol"))

    result = _save(tmp_path, home, "--codex-rollout", "--executor", "claude-code",
                   "--executor-model", "claude-opus-5-5", "--review-completed",
                   "--review-scope-complete", "--review-positive")

    assert result.returncode == 0, result.stderr
    meta, _ = _saved(tmp_path)
    assert meta["model"] == "gpt-6.1-sol"  # the rollout's value replaces --model
    assert "differs from the rollout's configured" in result.stderr
    assert meta["reported_reviewer_model"] is None
    assert meta["reviewer_model_source"] == "requested"
    assert meta["acceptance_status"] == "provisional"


def test_missing_rollout_is_an_error(tmp_path: Path) -> None:
    home = tmp_path / "empty"
    (home / "sessions").mkdir(parents=True)

    result = _save(tmp_path, home, "--codex-rollout")

    assert result.returncode != 0
    assert "no rollout" in result.stderr


def test_helper_rejects_a_path_as_thread_id(tmp_path: Path) -> None:
    result = subprocess.run(["python3", str(HELPER), "turn", "--thread-id", "../x",
                             "--codex-home", str(tmp_path)], text=True, capture_output=True)

    assert result.returncode == 1
    assert "not a Codex thread id" in result.stderr
