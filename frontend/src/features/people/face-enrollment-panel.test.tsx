import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FaceEnrollmentPanel } from "@/features/people/face-enrollment-panel";

const camerasList = vi.fn();
const startCamera = vi.fn();
const startSession = vi.fn();
const getSession = vi.fn();
const captureSession = vi.fn();
const cancelSession = vi.fn();

vi.mock("@/lib/api", () => ({
  camerasApi: {
    list: (...args: unknown[]) => camerasList(...args),
    start: (...args: unknown[]) => startCamera(...args),
    previewUrl: (id: string) => `/backend/api/cameras/${id}/preview`,
  },
  enrollmentsApi: {
    startSession: (...args: unknown[]) => startSession(...args),
    getSession: (...args: unknown[]) => getSession(...args),
    captureSession: (...args: unknown[]) => captureSession(...args),
    cancelSession: (...args: unknown[]) => cancelSession(...args),
  },
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("FaceEnrollmentPanel", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    camerasList.mockReset();
    startCamera.mockReset();
    startSession.mockReset();
    getSession.mockReset();
    captureSession.mockReset();
    cancelSession.mockReset();
    camerasList.mockResolvedValue({
      cameras: [
        {
          id: "default",
          name: "USB Webcam",
          state: "running",
          device_index: 0,
          width: 1280,
          height: 720,
          fps: 15,
          last_frame_at: null,
          error: null,
        },
      ],
    });
  });

  it("opens enrollment and shows waiting_for_face", async () => {
    startSession.mockResolvedValue({
      id: "s1",
      person_id: "p1",
      camera_id: "default",
      state: "waiting_for_face",
      track_id: null,
      quality_reasons: [],
      message: "Look at the camera so one face is visible",
      error_code: null,
      enrollment_id: null,
      face_width: null,
      face_height: null,
      sharpness: null,
      brightness: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    getSession.mockResolvedValue({
      id: "s1",
      person_id: "p1",
      camera_id: "default",
      state: "waiting_for_face",
      track_id: null,
      quality_reasons: [],
      message: "Look at the camera so one face is visible",
      error_code: null,
      enrollment_id: null,
      face_width: null,
      face_height: null,
      sharpness: null,
      brightness: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

    const user = userEvent.setup();
    wrap(<FaceEnrollmentPanel personId="p1" personActive />);
    await user.click(screen.getByRole("button", { name: "Enroll Face" }));

    await waitFor(() => {
      expect(startSession).toHaveBeenCalled();
    });
    expect(await screen.findByText(/Look at the camera/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Capture" })).toBeDisabled();
  });

  it("shows multiple faces message and keeps capture disabled", async () => {
    startSession.mockResolvedValue({
      id: "s2",
      person_id: "p1",
      camera_id: "default",
      state: "multiple_faces",
      track_id: null,
      quality_reasons: [],
      message: "Only one face should be visible",
      error_code: "multiple_faces",
      enrollment_id: null,
      face_width: null,
      face_height: null,
      sharpness: null,
      brightness: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    getSession.mockResolvedValue({
      id: "s2",
      person_id: "p1",
      camera_id: "default",
      state: "multiple_faces",
      track_id: null,
      quality_reasons: [],
      message: "Only one face should be visible",
      error_code: "multiple_faces",
      enrollment_id: null,
      face_width: null,
      face_height: null,
      sharpness: null,
      brightness: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

    const user = userEvent.setup();
    wrap(<FaceEnrollmentPanel personId="p1" personActive />);
    await user.click(screen.getByRole("button", { name: "Enroll Face" }));
    expect(await screen.findByText("Only one face should be visible.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Capture" })).toBeDisabled();
  });

  it("captures when ready", async () => {
    const ready = {
      id: "s3",
      person_id: "p1",
      camera_id: "default",
      state: "ready" as const,
      track_id: 1,
      quality_reasons: [],
      message: "Ready to enroll",
      error_code: null,
      enrollment_id: null,
      face_width: 80,
      face_height: 80,
      sharpness: 100,
      brightness: 120,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    startSession.mockResolvedValue(ready);
    getSession.mockResolvedValue(ready);
    captureSession.mockResolvedValue({
      ...ready,
      state: "completed",
      enrollment_id: "e1",
      message: "Enrollment sample captured successfully",
    });

    const user = userEvent.setup();
    wrap(<FaceEnrollmentPanel personId="p1" personActive />);
    await user.click(screen.getByRole("button", { name: "Enroll Face" }));
    const captureBtn = await screen.findByRole("button", { name: "Capture" });
    await waitFor(() => expect(captureBtn).toBeEnabled());
    await user.click(captureBtn);
    await waitFor(() => {
      expect(captureSession).toHaveBeenCalledWith("p1", "s3");
    });
  });

  it("shows quality rejection", async () => {
    startSession.mockResolvedValue({
      id: "s4",
      person_id: "p1",
      camera_id: "default",
      state: "quality_rejected",
      track_id: 1,
      quality_reasons: ["too_blurry"],
      message: "Keep your face still",
      error_code: "too_blurry",
      enrollment_id: null,
      face_width: 80,
      face_height: 80,
      sharpness: 10,
      brightness: 120,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    getSession.mockResolvedValue({
      id: "s4",
      person_id: "p1",
      camera_id: "default",
      state: "quality_rejected",
      track_id: 1,
      quality_reasons: ["too_blurry"],
      message: "Keep your face still",
      error_code: "too_blurry",
      enrollment_id: null,
      face_width: 80,
      face_height: 80,
      sharpness: 10,
      brightness: 120,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

    const user = userEvent.setup();
    wrap(<FaceEnrollmentPanel personId="p1" personActive />);
    await user.click(screen.getByRole("button", { name: "Enroll Face" }));
    expect(await screen.findByText("Keep your face still.")).toBeInTheDocument();
    expect(screen.getByText("Quality: rejected")).toBeInTheDocument();
  });
});
