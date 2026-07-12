"""Credential masking helpers for exchange connections."""

from trader_app.services.runtime import decrypt_text, encrypt_text


def encrypt_credential(value):
    return encrypt_text(value)


def decrypt_credential(value):
    return decrypt_text(value)


def mask_credential(value, visible=4):
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= visible:
        return "*" * len(text)
    return f"{text[:visible]}...{'*' * 6}"

