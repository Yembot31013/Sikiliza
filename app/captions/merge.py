from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

Kind = Literal["skip", "update", "new"]


@dataclass(frozen=True)
class CaptionDecision:
    text: str
    kind: Kind


def merge_caption(previous: str, incoming: str) -> CaptionDecision:
    current = _normalize(incoming)
    if not current:
        return CaptionDecision(text=previous, kind="skip")

    prior = _normalize(previous)
    if not prior:
        return CaptionDecision(text=incoming.strip(), kind="new")

    if current == prior:
        return CaptionDecision(text=previous, kind="skip")

    if current in prior:
        return CaptionDecision(text=previous, kind="skip")

    if prior in current or current.startswith(prior):
        return CaptionDecision(text=incoming.strip(), kind="update")

    ratio = SequenceMatcher(None, prior, current).ratio()
    if ratio >= 0.88:
        return CaptionDecision(text=incoming.strip(), kind="update")

    return CaptionDecision(text=incoming.strip(), kind="new")


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())
