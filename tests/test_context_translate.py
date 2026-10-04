from app.captions.context import (
    format_context_block,
    locked_language_codes,
    normalize_language_tag,
)
from app.captions.translate_parse import parse_translate_payload


def test_normalize_language_tag() -> None:
    assert normalize_language_tag("fr-FR") == "fr"
    assert normalize_language_tag("swa") == "sw"
    assert normalize_language_tag("") == ""


def test_locked_language_codes_needs_streak() -> None:
    assert locked_language_codes(["fr"]) == []
    assert locked_language_codes(["fr", "fr"]) == []
    assert locked_language_codes(["fr", "fr", "fr"]) == []
    assert locked_language_codes(["fr", "fr", "fr", "fr"]) == ["fr-FR", "en-US"]


def test_format_context_block() -> None:
    block = format_context_block(
        [("Habari", "Hello"), ("Sasa", "Now")],
        limit=4,
    )
    assert "Habari" in block
    assert "Hello" in block
    assert "Recent captions" in block


def test_parse_translate_json() -> None:
    language, translation = parse_translate_payload(
        '{"language":"fr","translation":"Hello everyone"}'
    )
    assert language == "fr"
    assert translation == "Hello everyone"


def test_parse_translate_plain_fallback() -> None:
    language, translation = parse_translate_payload("Just a line")
    assert language == ""
    assert translation == "Just a line"


def test_parse_rejects_json_prose_leakage() -> None:
    language, translation = parse_translate_payload(
        'Here is the JSON requested: ```\n{"language":"sw","translation":"Hi"}'
    )
    assert language == "sw"
    assert translation == "Hi"

    language, translation = parse_translate_payload("Here is the JSON requested: ```")
    assert language == ""
    assert translation == ""

    language, translation = parse_translate_payload('Yasi zetu amamufaa {"')
    assert language == ""
    assert translation == ""


def test_parse_partial_json_fields() -> None:
    language, translation = parse_translate_payload(
        '{"language":"sw","translation":"We are many people."'
    )
    assert language == "sw"
    assert translation == "We are many people."
