import base64

def base64_parser(string: str) -> str:
    """Encode a plain text sequence into base64."""
    return base64.b64encode(string.encode()).decode()


def is_base64(string: str) -> bool:
    """Return True when ``string`` is a valid base64 payload."""
    try:
        base64.b64decode(string, validate=True)
        return True
    except Exception:
        return False
