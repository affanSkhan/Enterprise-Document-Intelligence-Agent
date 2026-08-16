"""Run the repository's baseline prompt-injection benchmark."""
from __future__ import annotations
import json
from pathlib import Path
from app.evaluation.security import SecurityCase, evaluate_security
from app.core.security import detect_prompt_injection


def main() -> None:
    path = Path(__file__).with_name("security_cases.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [SecurityCase(**case) for case in payload["cases"]]
    result = evaluate_security(cases, detect_prompt_injection)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
