import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CameraPage } from "@/features/camera/camera-page";

const camerasList = vi.fn();
const cameraGet = vi.fn();
const detections = vi.fn();

vi.mock("@/lib/api", () => ({
  camerasApi: {
    list: (...args: unknown[]) => camerasList(...args),
    get: (...args: unknown[]) => cameraGet(...args),
    start: vi.fn(),
    stop: vi.fn(),
    detections: (...args: unknown[]) => detections(...args),
    previewUrl: (id: string) => `/backend/api/cameras/${id}/preview`,
  },
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("CameraPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    camerasList.mockReset();
    cameraGet.mockReset();
    detections.mockReset();
  });

  it("renders stopped camera status", async () => {
    camerasList.mockResolvedValue({
      cameras: [
        {
          id: "default",
          name: "USB Webcam",
          state: "closed",
          device_index: 0,
          width: 1280,
          height: 720,
          fps: 15,
          last_frame_at: null,
          error: null,
        },
      ],
    });
    cameraGet.mockResolvedValue({
      id: "default",
      name: "USB Webcam",
      state: "closed",
      device_index: 0,
      width: 1280,
      height: 720,
      fps: 15,
      last_frame_at: null,
      error: null,
    });

    wrap(<CameraPage />);

    expect(await screen.findByText("Stopped")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Stop" })).toBeDisabled();
  });
});
