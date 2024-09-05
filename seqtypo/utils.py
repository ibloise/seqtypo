import base64

def base64_parser(string: str):
    encoded = base64.b64encode(string.encode()).decode()
    return encoded


def is_base64(string: str) -> bool:
    try:
        # Intentar decodificar la cadena
        base64.b64decode(string, validate=True)
        return True
    except Exception:
        return False

