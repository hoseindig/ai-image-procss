import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest, cameraPreviewUrl, getApiBaseUrl } from "@/lib/api/client";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("uses /backend as the default base URL", () => {
    expect(getApiBaseUrl()).toBe("/backend");
  });

  it("builds MJPEG preview URLs without embedding vectors", () => {
    expect(cameraPreviewUrl("default")).toBe("/backend/api/cameras/default/preview");
  });

  it("parses backend error envelopes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "camera_not_found", message: "Camera missing", details: null },
          }),
          { status: 404, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(apiRequest("/api/cameras/missing")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      code: "camera_not_found",
      message: "Camera missing",
    } satisfies Partial<ApiError>);
  });

  it("maps network failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    await expect(apiRequest("/api/health")).rejects.toMatchObject({
      code: "network_error",
      status: 0,
    });
  });

  it("supports AbortSignal", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await apiRequest("/api/health", { signal: controller.signal });

    expect(fetchMock).toHaveBeenCalledWith(
      "/backend/api/health",
      expect.objectContaining({ signal: controller.signal }),
    );
  });
});
