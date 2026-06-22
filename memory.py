import json
from pathlib import Path

SAVE_PATH = Path(__file__).parent / "chat_save.json"


def save_session(
    character: dict,
    chat_history: list,
    chat_context: list,
    reached_milestones: set,
) -> None:
    data = {
        "character": character,
        "chat_history": chat_history,
        "chat_context": chat_context,
        "reached_milestones": list(reached_milestones),
    }
    SAVE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_session() -> dict | None:
    if not SAVE_PATH.exists():
        return None
    try:
        data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        data["reached_milestones"] = set(int(m) for m in data.get("reached_milestones", []))
        return data
    except Exception:
        return None
