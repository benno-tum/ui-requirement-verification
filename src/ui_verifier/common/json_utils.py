from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_json_response(text: str) -> Any:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for match in re.finditer(r"[\{\[]", text):
        try:
            parsed, _ = decoder.raw_decode(text[match.start() :])
            return parsed
        except json.JSONDecodeError:
            continue

    m = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))

    m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))

    raise ValueError("Model response could not be parsed as JSON.")
