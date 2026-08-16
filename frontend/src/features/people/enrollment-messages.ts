import type { EnrollmentSessionState } from "@/types/api";

const CODE_MESSAGES: Record<string, string> = {
  multiple_faces: "Only one face should be visible.",
  face_too_small: "Move closer to the camera.",
  too_blurry: "Keep your face still.",
  too_dark: "Improve the lighting.",
  too_bright: "Reduce strong lighting.",
  invalid_landmarks: "Face position could not be detected reliably.",
  invalid_crop: "Face crop was invalid; recenter your face.",
  camera_not_running: "Start the camera first.",
  embedding_disabled: "Face embedding is disabled on the backend.",
  embedding_unavailable: "Embedding is not available yet; keep your face steady.",
  alignment_unavailable: "Face position could not be aligned yet.",
  enrollment_not_ready: "Enrollment capture is not ready.",
};

export function enrollmentUserMessage(
  state: EnrollmentSessionState,
  message: string | null,
  errorCode: string | null,
): string {
  if (errorCode && CODE_MESSAGES[errorCode]) {
    return CODE_MESSAGES[errorCode];
  }
  if (message) {
    return message;
  }
  switch (state) {
    case "starting":
      return "Starting enrollment…";
    case "waiting_for_face":
      return "Look at the camera so one face is visible.";
    case "face_detected":
      return "Face detected.";
    case "multiple_faces":
      return "Only one face should be visible.";
    case "quality_rejected":
      return "Face quality was rejected.";
    case "ready":
      return "Ready to enroll.";
    case "capturing":
      return "Capturing enrollment sample…";
    case "completed":
      return "Enrollment sample captured successfully.";
    case "failed":
      return "Enrollment failed.";
    case "cancelled":
      return "Enrollment session cancelled.";
    default:
      return "Enrollment in progress.";
  }
}

export function enrollmentQualityLabel(state: EnrollmentSessionState): string {
  switch (state) {
    case "ready":
    case "completed":
      return "Quality: OK";
    case "quality_rejected":
      return "Quality: rejected";
    case "waiting_for_face":
      return "Quality: waiting for face";
    case "multiple_faces":
      return "Quality: multiple faces";
    case "face_detected":
      return "Quality: assessing";
    default:
      return "Quality: —";
  }
}
