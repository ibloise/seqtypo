from seqtypo.utils import base64_parser, is_base64


def test_base64_parser_and_detector_roundtrip():
    payload = "ACTGACTG"
    encoded = base64_parser(payload)

    assert encoded != payload
    assert is_base64(encoded) is True


def test_is_base64_rejects_plain_text():
    assert is_base64("not-base64") is False
