"""Benchmark event persistence and cooldown suppression.

From the backend directory:

    .\\.venv\\Scripts\\python.exe scripts/benchmark_events.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _venv_python() -> Path | None:
    if sys.platform == "win32":
        candidate = _BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = _BACKEND_ROOT / ".venv" / "bin" / "python"
    return candidate if candidate.is_file() else None


def _reexec_with_venv_if_needed() -> None:
    venv_python = _venv_python()
    if venv_python is None:
        return
    current = Path(sys.executable).resolve()
    target = venv_python.resolve()
    if current == target:
        return
    os.execv(str(target), [str(target), *sys.argv])


_reexec_with_venv_if_needed()

try:
    from app.db.session import Database
    from app.models import Base
    from app.services.event import EventService, EventServiceConfig
    from app.vision.recognizer import RecognitionResult
    from app.vision.types import RecognitionStatus
except ModuleNotFoundError as exc:
    print(f"Missing dependency: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


def _matched(person_id: str, track_id: int) -> RecognitionResult:
    return RecognitionResult(
        status=RecognitionStatus.MATCHED,
        track_id=track_id,
        person_id=person_id,
        person_display_name=person_id,
        similarity=0.9,
        enrollment_id=f"enroll-{person_id}",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark event persistence")
    parser.add_argument("--writes", type=int, default=100)
    args = parser.parse_args()

    database = Database("sqlite:///:memory:")
    Base.metadata.create_all(database.engine)
    service = EventService(
        database,
        EventServiceConfig(
            enabled=True,
            recognized_cooldown_seconds=3600.0,
            unknown_cooldown_seconds=3600.0,
        ),
    )

    # Distinct people → always write (no cooldown collision).
    started = time.perf_counter()
    for index in range(args.writes):
        service.record_from_recognition(
            "cam-1",
            _matched(person_id=f"p-{index}", track_id=index + 1),
        )
    write_elapsed = time.perf_counter() - started
    avg_write_ms = (write_elapsed / args.writes) * 1000.0
    print(
        f"event_writes={args.writes} avg_ms={avg_write_ms:.4f} "
        f"throughput={args.writes / write_elapsed:.1f} writes/sec"
    )

    # Same person during cooldown → no DB writes.
    service.clear_cooldowns()
    service.record_from_recognition("cam-1", _matched("cooldown-person", 1))
    started = time.perf_counter()
    suppressed = 0
    for _ in range(args.writes):
        if service.record_from_recognition("cam-1", _matched("cooldown-person", 1)) is None:
            suppressed += 1
    cooldown_elapsed = time.perf_counter() - started
    print(
        f"cooldown_calls={args.writes} suppressed={suppressed} "
        f"avg_ms={(cooldown_elapsed / args.writes) * 1000.0:.4f} "
        f"(no additional DB rows expected)"
    )
    total = service.list_events().total
    print(f"total_events_in_db={total} (expected {args.writes + 1})")
    database.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
