import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PeoplePage } from "@/features/people/people-page";

const listMock = vi.fn();
const createMock = vi.fn();

vi.mock("@/lib/api", () => ({
  personsApi: {
    list: (...args: unknown[]) => listMock(...args),
    create: (...args: unknown[]) => createMock(...args),
    update: vi.fn(),
    deactivate: vi.fn(),
    get: vi.fn(),
  },
  enrollmentsApi: {
    list: vi.fn(),
    create: vi.fn(),
    remove: vi.fn(),
  },
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("PeoplePage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    cleanup();
    listMock.mockReset();
    createMock.mockReset();
  });

  it("shows empty state when no people exist", async () => {
    listMock.mockResolvedValue({ persons: [] });
    wrap(<PeoplePage />);
    expect(await screen.findByText("No people enrolled yet.")).toBeInTheDocument();
  });

  it("creates a person", async () => {
    listMock.mockResolvedValue({ persons: [] });
    createMock.mockResolvedValue({
      id: "p1",
      display_name: "Ali",
      active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      enrollment_count: 0,
    });

    const user = userEvent.setup();
    wrap(<PeoplePage />);

    const input = await screen.findByLabelText("نام نمایشی");
    await user.clear(input);
    await user.type(input, "Ali");
    await user.click(screen.getByRole("button", { name: "ایجاد" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith({ display_name: "Ali" });
    });
  });

  it("renders loading then list", async () => {
    listMock.mockResolvedValue({
      persons: [
        {
          id: "p1",
          display_name: "Ali",
          active: true,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          enrollment_count: 2,
        },
      ],
    });
    wrap(<PeoplePage />);
    expect(await screen.findByText("Ali")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});
