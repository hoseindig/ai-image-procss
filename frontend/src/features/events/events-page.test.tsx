import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EventsPage } from "@/features/events/events-page";

const eventsList = vi.fn();
const personsList = vi.fn();
const camerasList = vi.fn();

vi.mock("@/lib/api", () => ({
  eventsApi: {
    list: (...args: unknown[]) => eventsList(...args),
    get: vi.fn(),
  },
  personsApi: {
    list: (...args: unknown[]) => personsList(...args),
  },
  camerasApi: {
    list: (...args: unknown[]) => camerasList(...args),
  },
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("EventsPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    eventsList.mockReset();
    personsList.mockResolvedValue({ persons: [] });
    camerasList.mockResolvedValue({ cameras: [] });
  });

  it("renders recognized events with score similarity", async () => {
    eventsList.mockResolvedValue({
      items: [
        {
          id: "e1",
          event_type: "recognized",
          camera_id: "default",
          track_id: 3,
          person_id: null,
          enrollment_id: null,
          similarity: 0.742,
          occurred_at: "2026-01-01T12:00:00Z",
          created_at: "2026-01-01T12:00:00Z",
        },
      ],
      page: 1,
      page_size: 20,
      total: 1,
    });

    wrap(<EventsPage />);

    expect(await screen.findByText("Recognized")).toBeInTheDocument();
    expect(screen.getByText("Similarity: 0.742")).toBeInTheDocument();
    expect(screen.queryByText("%")).not.toBeInTheDocument();
  });

  it("shows error state", async () => {
    const { ApiError } = await import("@/lib/api/client");
    eventsList.mockRejectedValue(new ApiError(500, "internal", "boom"));
    wrap(<EventsPage />);
    expect(await screen.findByText("boom")).toBeInTheDocument();
  });
});
