from app.providers.http import extract_choice, extract_gemini_text, extract_text


def test_extract_text_strips_payload() -> None:
    assert extract_text({"text": "  Habari  "}) == "Habari"
    assert extract_text({"text": 12}) == ""
    assert extract_text({}) == ""


def test_extract_choice_reads_chat_message() -> None:
    payload = {"choices": [{"message": {"content": " Hello there "}}]}
    assert extract_choice(payload) == "Hello there"
    assert extract_choice({"choices": []}) == ""
    assert extract_choice({}) == ""


def test_extract_gemini_text_joins_parts() -> None:
    payload = {
        "candidates": [
            {"content": {"parts": [{"text": " Habari "}, {"text": " yenu "}]}}
        ]
    }
    assert extract_gemini_text(payload) == "Habari yenu"
    assert extract_gemini_text({}) == ""


def test_extract_gemini_text_reads_audio_transcription() -> None:
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "audioTranscription": {
                                "text": " Can I please have a latte? "
                            }
                        }
                    ]
                }
            }
        ]
    }
    assert extract_gemini_text(payload) == "Can I please have a latte?"


def test_extract_gemini_text_falls_back_to_words() -> None:
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "audioTranscription": {
                                "words": [
                                    {"word": "Habari"},
                                    {"word": "yenu"},
                                ]
                            }
                        }
                    ]
                }
            }
        ]
    }
    assert extract_gemini_text(payload) == "Habari yenu"
