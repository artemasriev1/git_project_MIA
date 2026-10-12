from src.client import _sampling


def test_temperature_goes_through_extra_body_on_models_that_accept_it():
    # anthropic 1.x removed `temperature` from messages.create(); passing it directly is a TypeError
    assert _sampling("claude-sonnet-4-5", 0.0) == {"extra_body": {"temperature": 0.0}}


def test_temperature_is_dropped_for_models_that_reject_it():
    for model in ("claude-sonnet-5", "claude-opus-5", "claude-opus-5-5", "claude-opus-4-7", "claude-fable-5-1"):
        assert _sampling(model, 0.0) == {}


def test_no_temperature_sends_nothing():
    assert _sampling("claude-sonnet-4-5", None) == {}
