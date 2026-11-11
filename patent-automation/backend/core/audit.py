import json
import threading
from datetime import datetime, timezone
from pathlib import Path

_lock = threading.Lock()


def append_audit(job_dir: Path, event: str, actor: str = "system", **details) -> None:
    """Append one JSON line to the job's audit.log (append-only audit trail)."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "actor": actor,
        **details,
    }
    with _lock, open(job_dir / "audit.log", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
