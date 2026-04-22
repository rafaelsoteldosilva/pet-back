
# api/shared/utils/normalize_dni.py

import re

def normalize_dni(dni: str) -> str:
    """
    Normalize a Chilean RUN/RUT:
    - Remove dots and spaces
    - Uppercase the verifier digit
    - Ensure it contains one hyphen: XXXXXXXX-Y
    """
    if not dni:
        return dni

    # Remove dots, spaces, weird characters
    dni = re.sub(r"[^0-9kK-]", "", dni)

    # Uppercase everything
    dni = dni.upper()

    # If it already contains a hyphen, assume format is correct
    if "-" in dni:
        parts = dni.split("-")
        if len(parts) == 2:
            number, dv = parts
            return f"{number}{'-'}{dv}"

    # If no hyphen, last character is the verifier
    number = dni[:-1]
    dv = dni[-1]

    return f"{number}-{dv}"
