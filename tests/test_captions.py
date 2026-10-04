from app.captions.merge import CaptionDecision, merge_caption


def test_empty_incoming_is_skipped() -> None:
    assert merge_caption("hello", "   ") == CaptionDecision(text="hello", kind="skip")


def test_duplicate_window_is_skipped() -> None:
    previous = "Habari yenu mabru"
    incoming = "Habari yenu mabru"
    assert merge_caption(previous, incoming).kind == "skip"


def test_extension_updates_the_same_caption() -> None:
    decision = merge_caption("Ninaenda sokoni", "Ninaenda sokoni kuona babe")
    assert decision.kind == "update"
    assert decision.text == "Ninaenda sokoni kuona babe"


def test_new_sentence_starts_a_fresh_caption() -> None:
    decision = merge_caption("Ninaenda sokoni", "Wasee mmeona huyo jamaa")
    assert decision.kind == "new"
    assert decision.text == "Wasee mmeona huyo jamaa"


def test_incoming_substring_of_previous_is_skipped() -> None:
    decision = merge_caption("Habari yenu mabru nyumbani", "Habari yenu")
    assert decision.kind == "skip"


def test_near_duplicate_with_filler_is_skipped() -> None:
    decision = merge_caption(
        "Mimi nakupenda sana",
        "mimi nakupenda sana",
    )
    assert decision.kind == "skip"
