# api/shared/utils/normalize_document_id.py

import re


def normalize_document_id(document_id: str) -> str:
    if not document_id:
        return ""

    cleaned_document_id = re.sub(
        r"[^0-9kK-]",
        "",
        str(document_id).strip(),
    ).upper()

    if not cleaned_document_id:
        return ""

    if "-" in cleaned_document_id:
        parts = cleaned_document_id.split("-")

        if len(parts) == 2:
            number, verifier_digit = parts

            if number and verifier_digit:
                return f"{number}-{verifier_digit}"

        cleaned_document_id = cleaned_document_id.replace("-", "")

    if len(cleaned_document_id) < 2:
        return cleaned_document_id

    number = cleaned_document_id[:-1]
    verifier_digit = cleaned_document_id[-1]

    return f"{number}-{verifier_digit}"


def calculate_chilean_rut_verifier_digit(number: str) -> str:
    multiplier = 2
    total = 0

    for digit in reversed(number):
        total += int(digit) * multiplier
        multiplier += 1

        if multiplier > 7:
            multiplier = 2

    remainder = total % 11
    result = 11 - remainder

    if result == 11:
        return "0"

    if result == 10:
        return "K"

    return str(result)


def is_valid_chilean_rut(document_id: str) -> bool:
    normalized_document_id = normalize_document_id(document_id)

    if "-" not in normalized_document_id:
        return False

    number, verifier_digit = normalized_document_id.split("-", 1)

    if not number.isdigit():
        return False

    if not re.fullmatch(r"[0-9K]", verifier_digit):
        return False

    expected_verifier_digit = calculate_chilean_rut_verifier_digit(number)

    return verifier_digit == expected_verifier_digit