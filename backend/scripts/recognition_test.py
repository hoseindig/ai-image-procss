"""TEST ONLY CLI: run recognition on a synthetic/aligned 112×112 crop.

Does not start the webcam. Requires RECOGNITION_TEST_MODE=true in the environment
or pass --force-test-mode (sets the flag for this process only).

Example (Windows PowerShell, from repo root):

  $env:RECOGNITION_TEST_MODE="true"
  backend\\.venv\\Scripts\\python.exe backend\\scripts\\recognition_test.py `
    --image backend\\tests\\fixtures\\faces\\synthetic_aligned_a.png

Never prints embeddings.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TEST ONLY recognition on an aligned 112×112 face crop"
    )
    parser.add_argument(
        "--image",
        required=True,
        type=Path,
        help="Path to aligned 112×112 PNG/JPEG",
    )
    parser.add_argument("--camera-id", default="test")
    parser.add_argument("--track-id", type=int, default=1)
    parser.add_argument(
        "--no-event",
        action="store_true",
        help="Skip EventService persistence",
    )
    parser.add_argument(
        "--force-test-mode",
        action="store_true",
        help="Set RECOGNITION_TEST_MODE=true for this process only",
    )
    args = parser.parse_args()

    if args.force_test_mode:
        os.environ["RECOGNITION_TEST_MODE"] = "true"

    from app.core.config import load_settings
    from app.db.session import Database
    from app.models import Base
    from app.services.event import EventService, EventServiceConfig
    from app.services.recognition_test import (
        RecognitionTestDisabledError,
        RecognitionTestInputError,
        RecognitionTestService,
    )
    from app.vision.factory import (
        create_event_service,
        create_face_embedder,
        create_face_recognizer,
    )

    settings = load_settings()
    if not settings.recognition_test_mode:
        print(
            "ERROR: RECOGNITION_TEST_MODE is false. "
            "Export RECOGNITION_TEST_MODE=true or pass --force-test-mode.",
            file=sys.stderr,
        )
        return 2

    embedder = create_face_embedder(settings)
    if embedder is None:
        print("ERROR: face embedder unavailable (check SFace model path).", file=sys.stderr)
        return 2

    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    recognizer = create_face_recognizer(settings, database)
    if recognizer is None:
        print("ERROR: face recognizer unavailable.", file=sys.stderr)
        database.dispose()
        return 2

    event_service = create_event_service(settings, database) or EventService(
        database,
        EventServiceConfig(enabled=False),
    )

    service = RecognitionTestService(
        enabled=True,
        embedder=embedder,
        recognizer=recognizer,
        event_service=event_service,
        recognition_threshold=settings.face_recognition_threshold,
    )

    data = args.image.read_bytes()
    try:
        outcome = service.recognize_image_bytes(
            data,
            camera_id=args.camera_id,
            track_id=args.track_id,
            record_event=not args.no_event,
        )
    except (RecognitionTestDisabledError, RecognitionTestInputError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        database.dispose()
        return 1

    payload = {
        "test_only": True,
        "status": outcome.status,
        "track_id": outcome.track_id,
        "person_id": outcome.person_id,
        "person_display_name": outcome.person_display_name,
        "similarity": outcome.similarity,
        "enrollment_id": outcome.enrollment_id,
        "reason": outcome.reason,
        "event_id": outcome.event_id,
        "event_created": outcome.event_created,
        "camera_id": outcome.camera_id,
        "threshold": outcome.threshold,
    }
    print(json.dumps(payload, indent=2))
    database.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
