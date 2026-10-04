from app.captions.merge import merge_caption


def test_first_caption_is_new() -> None:
    decision = merge_caption("", "Habari")
    assert decision.kind == "new"
    assert decision.text == "Habari"
