from app.captions.quality import is_usable_transcript


def test_rejects_empty_and_tiny_fragments() -> None:
    assert is_usable_transcript("") is False
    assert is_usable_transcript("hi") is False
    assert is_usable_transcript("ok") is False


def test_rejects_digit_noise_and_gibberish() -> None:
    assert is_usable_transcript("410") is False
    assert is_usable_transcript("49yyu.") is False
    assert is_usable_transcript("14/08/1990") is False


def test_rejects_json_leakage() -> None:
    assert is_usable_transcript('Here is the JSON requested: ```') is False
    assert is_usable_transcript('Mambo ya zisconi {"') is False


def test_keeps_real_speech() -> None:
    assert is_usable_transcript("Habari yenu") is True
    assert is_usable_transcript("Puis nous retournons à TST Kitchen") is True
    assert is_usable_transcript("La noche.") is True
