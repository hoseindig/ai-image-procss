"""Camera enrollment sessions. Reuses DetectionRuntime embeddings; no second SFace."""

from __future__ import annotations

from app.cameras.manager import CameraManager
from app.cameras.types import CameraState
from app.core.logging import get_logger
from app.persons.embedding_codec import EMBEDDING_DIM, validate_embedding_values
from app.persons.enrollment_session import (
    EnrollmentSessionRecord,
    EnrollmentSessionState,
    EnrollmentSessionStore,
)
from app.persons.exceptions import (
    EnrollmentCaptureNotReadyError,
    EnrollmentSessionConflictError,
    EnrollmentSessionNotFoundError,
    InvalidEmbeddingError,
    PersonInactiveError,
    PersonNotFoundError,
)
from app.schemas.enrollment_session import EnrollmentSessionResponse
from app.schemas.person import EnrollmentResponse
from app.services.enrollment import EnrollmentService
from app.services.person import PersonService
from app.vision.embedder import FaceEmbedding
from app.vision.runtime import DetectionRuntime
from app.vision.types import (
    DetectionSnapshot,
    EmbeddingStatus,
    FaceQuality,
    QualityRejectionReason,
    TrackState,
)

logger = get_logger("app.persons")

_ACTIVE_TRACK_STATES = {TrackState.TENTATIVE, TrackState.CONFIRMED}


def _to_response(session: EnrollmentSessionRecord) -> EnrollmentSessionResponse:
    return EnrollmentSessionResponse(
        id=session.id,
        person_id=session.person_id,
        camera_id=session.camera_id,
        state=session.state,
        track_id=session.track_id,
        quality_reasons=list(session.quality_reasons),
        message=session.message,
        error_code=session.error_code,
        enrollment_id=session.enrollment_id,
        face_width=session.face_width,
        face_height=session.face_height,
        sharpness=session.sharpness,
        brightness=session.brightness,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


class EnrollmentSessionService:
    """Evaluates live detection slots and captures embeddings into EnrollmentService."""

    def __init__(
        self,
        store: EnrollmentSessionStore,
        person_service: PersonService,
        enrollment_service: EnrollmentService,
        camera_manager: CameraManager,
        detection_runtime: DetectionRuntime,
        *,
        default_camera_id: str,
    ) -> None:
        self._store = store
        self._persons = person_service
        self._enrollments = enrollment_service
        self._cameras = camera_manager
        self._runtime = detection_runtime
        self._default_camera_id = default_camera_id

    def start_session(
        self,
        person_id: str,
        *,
        camera_id: str | None = None,
    ) -> EnrollmentSessionResponse:
        person = self._persons.get_person(person_id)
        if not person.active:
            raise PersonInactiveError(person_id)
        resolved_camera = camera_id or self._default_camera_id
        # Ensure camera is registered (raises if unknown).
        self._cameras.get_status(resolved_camera)
        session = self._store.create(person_id=person_id, camera_id=resolved_camera)
        return _to_response(self._refresh(session))

    def get_session(self, person_id: str, session_id: str) -> EnrollmentSessionResponse:
        session = self._require_session(person_id, session_id)
        if session.state in {
            EnrollmentSessionState.COMPLETED,
            EnrollmentSessionState.CANCELLED,
            EnrollmentSessionState.FAILED,
        }:
            return _to_response(session)
        return _to_response(self._refresh(session))

    def capture(self, person_id: str, session_id: str) -> EnrollmentSessionResponse:
        session = self._require_session(person_id, session_id)
        if session.state is EnrollmentSessionState.COMPLETED:
            raise EnrollmentSessionConflictError(
                "Enrollment session is already completed",
                code="enrollment_session_completed",
            )
        if session.state is EnrollmentSessionState.CANCELLED:
            raise EnrollmentSessionConflictError(
                "Enrollment session was cancelled",
                code="enrollment_session_cancelled",
            )

        session = self._refresh(session)
        if session.state is not EnrollmentSessionState.READY:
            raise EnrollmentCaptureNotReadyError(
                session.message or "Enrollment capture is not ready",
                code=session.error_code or "enrollment_not_ready",
            )

        session.state = EnrollmentSessionState.CAPTURING
        self._store.update(session)

        track_id = session.track_id
        if track_id is None:
            session.state = EnrollmentSessionState.FAILED
            session.error_code = "enrollment_missing_track"
            session.message = "No track is available for capture"
            self._store.update(session)
            raise EnrollmentCaptureNotReadyError(session.message, code=session.error_code)

        embedding = self._find_embedding(session.camera_id, track_id)
        if embedding is None:
            session.state = EnrollmentSessionState.FACE_DETECTED
            session.error_code = "embedding_unavailable"
            session.message = "Embedding is not available yet; wait for a stable face"
            self._store.update(session)
            raise EnrollmentCaptureNotReadyError(session.message, code=session.error_code)

        vector = [float(value) for value in embedding.vector.tolist()]
        try:
            validate_embedding_values(vector)
        except InvalidEmbeddingError as exc:
            session.state = EnrollmentSessionState.FAILED
            session.error_code = exc.code
            session.message = exc.message
            self._store.update(session)
            raise

        created: EnrollmentResponse = self._enrollments.add_embedding(
            person_id,
            vector,
            quality_accepted=True,
            normalized=embedding.normalized,
            face_width=session.face_width,
            face_height=session.face_height,
            sharpness=session.sharpness,
            brightness=session.brightness,
            source_track_id=track_id,
        )

        session.state = EnrollmentSessionState.COMPLETED
        session.enrollment_id = created.id
        session.error_code = None
        session.message = "Enrollment sample captured successfully"
        self._store.update(session)
        logger.info(
            "Camera enrollment captured person_id=%s session_id=%s enrollment_id=%s track_id=%s",
            person_id,
            session_id,
            created.id,
            track_id,
        )
        return _to_response(session)

    def cancel(self, person_id: str, session_id: str) -> EnrollmentSessionResponse:
        session = self._require_session(person_id, session_id)
        if session.state is EnrollmentSessionState.COMPLETED:
            raise EnrollmentSessionConflictError(
                "Completed enrollment sessions cannot be cancelled",
                code="enrollment_session_completed",
            )
        session.state = EnrollmentSessionState.CANCELLED
        session.message = "Enrollment session cancelled"
        session.error_code = None
        self._store.update(session)
        return _to_response(session)

    def _require_session(self, person_id: str, session_id: str) -> EnrollmentSessionRecord:
        # Validates person exists.
        try:
            self._persons.get_person(person_id)
        except PersonNotFoundError:
            raise
        session = self._store.get(session_id)
        if session is None or session.person_id != person_id:
            raise EnrollmentSessionNotFoundError(session_id)
        return session

    def _refresh(self, session: EnrollmentSessionRecord) -> EnrollmentSessionRecord:
        try:
            camera = self._cameras.get_status(session.camera_id)
        except Exception:
            session.state = EnrollmentSessionState.FAILED
            session.error_code = "camera_not_found"
            session.message = f"Camera '{session.camera_id}' was not found"
            return self._store.update(session)

        if camera.state is not CameraState.RUNNING:
            session.state = EnrollmentSessionState.FAILED
            session.error_code = "camera_not_running"
            session.message = "Start the camera first"
            session.track_id = None
            session.quality_reasons = []
            return self._store.update(session)

        if not self._runtime.embedding_enabled:
            session.state = EnrollmentSessionState.FAILED
            session.error_code = "embedding_disabled"
            session.message = "Face embedding is disabled on the backend"
            return self._store.update(session)

        snapshot = self._runtime.latest(session.camera_id)
        if snapshot is None:
            session.state = EnrollmentSessionState.STARTING
            session.message = "Waiting for the detection pipeline to start"
            session.error_code = None
            session.track_id = None
            session.quality_reasons = []
            return self._store.update(session)

        return self._store.update(self._evaluate_snapshot(session, snapshot))

    def _evaluate_snapshot(
        self,
        session: EnrollmentSessionRecord,
        snapshot: DetectionSnapshot,
    ) -> EnrollmentSessionRecord:
        session.error_code = None
        active_tracks = [track for track in snapshot.tracks if track.state in _ACTIVE_TRACK_STATES]

        if len(active_tracks) == 0:
            session.state = EnrollmentSessionState.WAITING_FOR_FACE
            session.track_id = None
            session.quality_reasons = []
            session.face_width = None
            session.face_height = None
            session.sharpness = None
            session.brightness = None
            session.message = "Look at the camera so one face is visible"
            return session

        if len(active_tracks) > 1:
            session.state = EnrollmentSessionState.MULTIPLE_FACES
            session.track_id = None
            session.quality_reasons = []
            session.message = "Only one face should be visible"
            session.error_code = "multiple_faces"
            return session

        track = active_tracks[0]
        session.track_id = track.track_id
        quality = self._quality_for(snapshot, track.track_id)
        if quality is not None:
            session.face_width = quality.face_width
            session.face_height = quality.face_height
            session.sharpness = quality.sharpness
            session.brightness = quality.brightness
            session.quality_reasons = list(quality.reasons)

        if quality is None:
            session.state = EnrollmentSessionState.FACE_DETECTED
            session.message = "Face detected; assessing quality"
            return session

        if not quality.accepted:
            session.state = EnrollmentSessionState.QUALITY_REJECTED
            session.error_code = quality.reasons[0].value if quality.reasons else "quality_rejected"
            session.message = _quality_message(quality.reasons)
            return session

        if track.track_id not in set(snapshot.aligned_track_ids):
            session.state = EnrollmentSessionState.FACE_DETECTED
            session.error_code = "alignment_unavailable"
            session.message = "Face position could not be aligned yet"
            return session

        embedding_info = next(
            (item for item in snapshot.embeddings if item.track_id == track.track_id),
            None,
        )
        if embedding_info is None or embedding_info.status is not EmbeddingStatus.GENERATED:
            session.state = EnrollmentSessionState.FACE_DETECTED
            session.error_code = (
                embedding_info.reason.value
                if embedding_info is not None and embedding_info.reason is not None
                else "embedding_pending"
            )
            session.message = "Face detected; generating embedding"
            return session

        raw = self._find_embedding(session.camera_id, track.track_id)
        if raw is None or raw.dimension != EMBEDDING_DIM:
            session.state = EnrollmentSessionState.FACE_DETECTED
            session.error_code = "embedding_unavailable"
            session.message = "Embedding is not available yet; keep your face steady"
            return session

        session.state = EnrollmentSessionState.READY
        session.error_code = None
        session.message = "Ready to enroll"
        session.quality_reasons = []
        return session

    def _find_embedding(self, camera_id: str, track_id: int) -> FaceEmbedding | None:
        for item in self._runtime.latest_embeddings(camera_id):
            if item.source_track_id == track_id and item.dimension == EMBEDDING_DIM:
                return item
        return None

    @staticmethod
    def _quality_for(snapshot: DetectionSnapshot, track_id: int) -> FaceQuality | None:
        for item in snapshot.qualities:
            if item.track_id == track_id:
                return item
        return None


def _quality_message(reasons: list[QualityRejectionReason]) -> str:
    if not reasons:
        return "Face quality was rejected"
    mapping = {
        QualityRejectionReason.FACE_TOO_SMALL: "Move closer to the camera",
        QualityRejectionReason.TOO_BLURRY: "Keep your face still",
        QualityRejectionReason.TOO_DARK: "Improve the lighting",
        QualityRejectionReason.TOO_BRIGHT: "Reduce strong lighting",
        QualityRejectionReason.INVALID_LANDMARKS: ("Face position could not be detected reliably"),
        QualityRejectionReason.INVALID_CROP: "Face crop was invalid; recenter your face",
    }
    return mapping.get(reasons[0], reasons[0].value)
