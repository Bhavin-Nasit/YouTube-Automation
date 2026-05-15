from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Dict, Optional


class ProcessedVideoStore:
    """Tiny JSON-backed store to avoid duplicate updates on repeated webhooks."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._lock = Lock()

    def has(self, video_id: str) -> bool:
        return video_id in self._read()

    def mark(self, video_id: str, payload: Dict[str, object]) -> None:
        with self._lock:
            data = self._read_unlocked()
            data[video_id] = payload
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    def get(self, video_id: str) -> Optional[Dict[str, object]]:
        return self._read().get(video_id)

    def _read(self) -> Dict[str, Dict[str, object]]:
        with self._lock:
            return self._read_unlocked()

    def _read_unlocked(self) -> Dict[str, Dict[str, object]]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(raw, dict):
            return {}
        return {str(key): value for key, value in raw.items() if isinstance(value, dict)}
