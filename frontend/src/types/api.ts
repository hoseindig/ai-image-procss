/** Frontend types mirroring backend API schemas. No raw embedding vectors. */

export type CameraState =
  | "closed"
  | "opening"
  | "open"
  | "running"
  | "stopped"
  | "error";

export interface Camera {
  id: string;
  name: string;
  state: CameraState;
  device_index: number;
  width: number;
  height: number;
  fps: number;
  last_frame_at: string | null;
  error: string | null;
}

export interface CameraListResponse {
  cameras: Camera[];
}

export interface Point {
  x: number;
  y: number;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface FaceLandmarks {
  left_eye: Point;
  right_eye: Point;
  nose: Point;
  left_mouth: Point;
  right_mouth: Point;
}

export interface FaceDetection {
  confidence: number;
  bounding_box: BoundingBox;
  landmarks: FaceLandmarks;
}

export type QualityRejectionReason =
  | "face_too_small"
  | "too_blurry"
  | "too_dark"
  | "too_bright"
  | "invalid_landmarks"
  | "invalid_crop";

export interface FaceQuality {
  accepted: boolean;
  reasons: QualityRejectionReason[];
  face_width: number;
  face_height: number;
  sharpness: number | null;
  brightness: number | null;
  landmarks_valid: boolean;
  aligned: boolean;
}

export type EmbeddingStatus = "generated" | "skipped" | "failed";
export type EmbeddingSkipReason =
  | "quality_rejected"
  | "alignment_unavailable"
  | "embedding_disabled"
  | "inference_failed";

/** Metadata only — never includes the 128-D vector. */
export interface FaceEmbeddingMetadata {
  status: EmbeddingStatus;
  dimension: number | null;
  reason: EmbeddingSkipReason | null;
  normalized: boolean;
}

export type RecognitionStatus = "matched" | "unknown" | "skipped" | "error";
export type RecognitionReason =
  | "below_threshold"
  | "gallery_empty"
  | "quality_rejected"
  | "alignment_unavailable"
  | "embedding_unavailable"
  | "embedding_failed"
  | "recognition_disabled"
  | "invalid_embedding"
  | "internal_error";

export interface RecognitionResult {
  status: RecognitionStatus;
  person_id: string | null;
  person_display_name: string | null;
  similarity: number | null;
  enrollment_id: string | null;
  reason: RecognitionReason | null;
}

export type TrackState = "tentative" | "confirmed" | "lost";

export interface FaceTrack {
  track_id: number;
  state: TrackState;
  confidence: number;
  bounding_box: BoundingBox;
  landmarks: FaceLandmarks;
  age_frames: number;
  missed_frames: number;
  quality: FaceQuality | null;
  embedding: FaceEmbeddingMetadata | null;
  recognition: RecognitionResult | null;
}

export interface DetectionResponse {
  camera_id: string;
  enabled: boolean;
  timestamp: string | null;
  faces: FaceDetection[];
  tracks: FaceTrack[];
  inference_ms: number | null;
  tracking_ms: number | null;
  quality_ms: number | null;
  alignment_ms: number | null;
  embedding_ms: number | null;
  recognition_ms: number | null;
  aligned_count: number;
  embedded_count: number;
  error: string | null;
}

export interface Person {
  id: string;
  display_name: string;
  active: boolean;
  created_at: string;
  updated_at: string;
  enrollment_count: number;
}

export interface PersonListResponse {
  persons: Person[];
}

export interface PersonCreateRequest {
  display_name: string;
}

export interface PersonUpdateRequest {
  display_name?: string;
  active?: boolean;
}

/** Enrollment metadata only — never includes raw embedding vectors. */
export interface EnrollmentSampleMetadata {
  id: string;
  person_id: string;
  dimension: number;
  normalized: boolean;
  face_width: number | null;
  face_height: number | null;
  sharpness: number | null;
  brightness: number | null;
  source_track_id: number | null;
  created_at: string;
}

export interface EnrollmentListResponse {
  enrollments: EnrollmentSampleMetadata[];
}

/**
 * Developer/testing enrollment payload.
 * The browser does not generate SFace embeddings.
 */
export interface EnrollmentCreateRequest {
  embedding: number[];
  normalized: boolean;
  quality: {
    accepted: boolean;
    face_width?: number | null;
    face_height?: number | null;
    sharpness?: number | null;
    brightness?: number | null;
  };
  source_track_id?: number | null;
}

export type EnrollmentSessionState =
  | "starting"
  | "waiting_for_face"
  | "face_detected"
  | "multiple_faces"
  | "quality_rejected"
  | "ready"
  | "capturing"
  | "completed"
  | "failed"
  | "cancelled";

export interface EnrollmentSession {
  id: string;
  person_id: string;
  camera_id: string;
  state: EnrollmentSessionState;
  track_id: number | null;
  quality_reasons: QualityRejectionReason[];
  message: string | null;
  error_code: string | null;
  enrollment_id: string | null;
  face_width: number | null;
  face_height: number | null;
  sharpness: number | null;
  brightness: number | null;
  created_at: string;
  updated_at: string;
}

export interface EnrollmentSessionCreateRequest {
  camera_id?: string | null;
}

export type EventType =
  | "recognized"
  | "unknown_face"
  | "track_started"
  | "track_lost";

export interface Event {
  id: string;
  event_type: EventType;
  camera_id: string;
  track_id: number;
  person_id: string | null;
  enrollment_id: string | null;
  similarity: number | null;
  occurred_at: string;
  created_at: string;
}

export interface EventListResponse {
  items: Event[];
  page: number;
  page_size: number;
  total: number;
}

export interface EventListParams {
  camera_id?: string;
  person_id?: string;
  event_type?: EventType;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}

export interface HealthResponse {
  status: "ok";
}

export interface ReadyCheck {
  ok: boolean;
  detail: string | null;
}

export interface ReadyResponse {
  status: "ready" | "not_ready";
  database: ReadyCheck;
  models: ReadyCheck;
  camera_required_for_ready: false;
}

export interface DatabaseStatus {
  connected: boolean;
}

export interface CameraHealthStatus {
  available: boolean;
  running: boolean;
}

export interface FaceDetectionHealthStatus {
  enabled: boolean;
  model_loaded: boolean;
  provider: string | null;
  last_inference_ms: number | null;
  tracking_enabled: boolean;
  quality_enabled: boolean;
  alignment_enabled: boolean;
  embedding_enabled: boolean;
  embedding_provider: string | null;
  recognition_enabled: boolean;
  recognition_threshold: number | null;
  event_logging_enabled: boolean;
}

export interface SystemStatus {
  status: "ok" | "degraded";
  environment: string;
  python_version: string;
  uptime_seconds: number;
  database: DatabaseStatus;
  camera: CameraHealthStatus;
  face_detection: FaceDetectionHealthStatus;
  ready: boolean;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
