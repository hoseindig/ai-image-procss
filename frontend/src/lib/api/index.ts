import { apiRequest, cameraPreviewUrl } from "@/lib/api/client";
import type {
  Camera,
  CameraListResponse,
  DetectionResponse,
  EnrollmentCreateRequest,
  EnrollmentListResponse,
  EnrollmentSampleMetadata,
  EnrollmentSession,
  EnrollmentSessionCreateRequest,
  Event,
  EventListParams,
  EventListResponse,
  HealthResponse,
  Person,
  PersonCreateRequest,
  PersonListResponse,
  PersonUpdateRequest,
  SystemStatus,
} from "@/types/api";

export const healthApi = {
  get: (signal?: AbortSignal) => apiRequest<HealthResponse>("/api/health", { signal }),
};

export const systemApi = {
  getStatus: (signal?: AbortSignal) =>
    apiRequest<SystemStatus>("/api/system/status", { signal }),
};

export const camerasApi = {
  list: (signal?: AbortSignal) => apiRequest<CameraListResponse>("/api/cameras", { signal }),
  get: (cameraId: string, signal?: AbortSignal) =>
    apiRequest<Camera>(`/api/cameras/${encodeURIComponent(cameraId)}`, { signal }),
  start: (cameraId: string, signal?: AbortSignal) =>
    apiRequest<Camera>(`/api/cameras/${encodeURIComponent(cameraId)}/start`, {
      method: "POST",
      signal,
    }),
  stop: (cameraId: string, signal?: AbortSignal) =>
    apiRequest<Camera>(`/api/cameras/${encodeURIComponent(cameraId)}/stop`, {
      method: "POST",
      signal,
    }),
  detections: (cameraId: string, signal?: AbortSignal) =>
    apiRequest<DetectionResponse>(
      `/api/cameras/${encodeURIComponent(cameraId)}/detections`,
      { signal },
    ),
  previewUrl: cameraPreviewUrl,
};

export const personsApi = {
  list: (signal?: AbortSignal) => apiRequest<PersonListResponse>("/api/persons", { signal }),
  get: (personId: string, signal?: AbortSignal) =>
    apiRequest<Person>(`/api/persons/${encodeURIComponent(personId)}`, { signal }),
  create: (body: PersonCreateRequest, signal?: AbortSignal) =>
    apiRequest<Person>("/api/persons", { method: "POST", body, signal }),
  update: (personId: string, body: PersonUpdateRequest, signal?: AbortSignal) =>
    apiRequest<Person>(`/api/persons/${encodeURIComponent(personId)}`, {
      method: "PATCH",
      body,
      signal,
    }),
  deactivate: (personId: string, signal?: AbortSignal) =>
    apiRequest<Person>(`/api/persons/${encodeURIComponent(personId)}`, {
      method: "DELETE",
      signal,
    }),
};

export const enrollmentsApi = {
  list: (personId: string, signal?: AbortSignal) =>
    apiRequest<EnrollmentListResponse>(
      `/api/persons/${encodeURIComponent(personId)}/enrollments`,
      { signal },
    ),
  create: (personId: string, body: EnrollmentCreateRequest, signal?: AbortSignal) =>
    apiRequest<EnrollmentSampleMetadata>(
      `/api/persons/${encodeURIComponent(personId)}/enrollments`,
      { method: "POST", body, signal },
    ),
  remove: (personId: string, enrollmentId: string, signal?: AbortSignal) =>
    apiRequest<void>(
      `/api/persons/${encodeURIComponent(personId)}/enrollments/${encodeURIComponent(enrollmentId)}`,
      { method: "DELETE", signal },
    ),
  startSession: (
    personId: string,
    body: EnrollmentSessionCreateRequest = {},
    signal?: AbortSignal,
  ) =>
    apiRequest<EnrollmentSession>(
      `/api/persons/${encodeURIComponent(personId)}/enrollment-sessions`,
      { method: "POST", body, signal },
    ),
  getSession: (personId: string, sessionId: string, signal?: AbortSignal) =>
    apiRequest<EnrollmentSession>(
      `/api/persons/${encodeURIComponent(personId)}/enrollment-sessions/${encodeURIComponent(sessionId)}`,
      { signal },
    ),
  captureSession: (personId: string, sessionId: string, signal?: AbortSignal) =>
    apiRequest<EnrollmentSession>(
      `/api/persons/${encodeURIComponent(personId)}/enrollment-sessions/${encodeURIComponent(sessionId)}/capture`,
      { method: "POST", signal },
    ),
  cancelSession: (personId: string, sessionId: string, signal?: AbortSignal) =>
    apiRequest<EnrollmentSession>(
      `/api/persons/${encodeURIComponent(personId)}/enrollment-sessions/${encodeURIComponent(sessionId)}`,
      { method: "DELETE", signal },
    ),
};

function buildEventQuery(params: EventListParams = {}): string {
  const search = new URLSearchParams();
  if (params.camera_id) search.set("camera_id", params.camera_id);
  if (params.person_id) search.set("person_id", params.person_id);
  if (params.event_type) search.set("event_type", params.event_type);
  if (params.from) search.set("from", params.from);
  if (params.to) search.set("to", params.to);
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const eventsApi = {
  list: (params: EventListParams = {}, signal?: AbortSignal) =>
    apiRequest<EventListResponse>(`/api/events${buildEventQuery(params)}`, { signal }),
  get: (eventId: string, signal?: AbortSignal) =>
    apiRequest<Event>(`/api/events/${encodeURIComponent(eventId)}`, { signal }),
};
