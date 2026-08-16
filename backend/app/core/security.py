import re

INJECTION_PATTERNS = [
    r"ignore (all|any|the) previous instructions",
    r"system message",
    r"developer message",
    r"reveal (the )?(secret|system prompt|credentials)",
    r"disregard (all|the) instructions",
]


def detect_prompt_injection(text: str) -> list[str]:
    lowered = text.lower()
    return [pattern for pattern in INJECTION_PATTERNS if re.search(pattern, lowered)]


def sanitize_retrieved_content(text: str) -> str:
    """Mark retrieved text as untrusted data; it must never become an instruction."""
    findings = detect_prompt_injection(text)
    if findings:
        return "[UNTRUSTED DOCUMENT CONTENT: instruction-like text detected]\n" + text
    return "[UNTRUSTED DOCUMENT CONTENT]\n" + text
