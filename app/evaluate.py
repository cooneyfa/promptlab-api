"""Deterministic, dependency-free prompt evaluation heuristics.

This is intentionally a *mock* evaluator: it scores a prompt's structure
(length, specificity signals, formatting hygiene) without calling any paid
LLM API, so the test suite is hermetic and free to run. The module is
factored so a real model-based scorer can replace `evaluate()` later
without changing the API contract.
"""

from __future__ import annotations

import re

_IMPERATIVES = {
    "summarize", "explain", "list", "describe", "compare", "generate",
    "write", "draft", "analyze", "analyse", "translate", "classify",
    "extract", "rewrite", "outline", "brainstorm", "evaluate", "rank",
    "convert", "create",
}

_FORMAT_SIGNALS = ("```", "- ", "* ", "1.", "##", "|")


def _length_score(text: str) -> tuple[float, str]:
    n = len(text)
    if 60 <= n <= 600:
        return 1.0, f"length {n} chars is in the 60-600 sweet spot"
    if n < 60:
        return round(n / 60, 2), f"length {n} chars is very short; add context"
    return round(max(0.2, 600 / n), 2), f"length {n} chars is long; consider trimming"


def _specificity_score(text: str) -> tuple[float, str]:
    lowered = text.lower()
    words = re.findall(r"[a-z]+", lowered)
    hits = sum(1 for w in _IMPERATIVES if w in words)
    quoted = len(re.findall(r'"[^"]+"', text))
    numbered = len(re.findall(r"\b\d+[\).\:]?", text))
    raw = hits * 0.25 + quoted * 0.15 + numbered * 0.1
    score = round(min(1.0, raw), 2)
    note = (
        f"found {hits} action verb(s), {quoted} quoted constraint(s)"
        if score > 0
        else "no action verbs or concrete constraints detected"
    )
    return score, note


def _format_score(text: str) -> tuple[float, str]:
    hits = sum(1 for sig in _FORMAT_SIGNALS if sig in text)
    score = round(min(1.0, hits * 0.5), 2)
    note = (
        f"uses {hits} formatting signal(s) for structured output"
        if hits
        else "no formatting signals; specify the output shape you want"
    )
    return score, note


def evaluate(text: str) -> dict:
    """Score prompt text; returns scores dict, overall 0-100, and notes."""
    length, length_note = _length_score(text)
    specificity, spec_note = _specificity_score(text)
    formatting, format_note = _format_score(text)
    scores = {
        "length": length,
        "specificity": specificity,
        "formatting": formatting,
    }
    overall = round(sum(scores.values()) / len(scores) * 100, 1)
    notes = [length_note, spec_note, format_note]
    return {"scores": scores, "overall": overall, "notes": notes}
