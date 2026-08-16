import { expect, test, type Page, type Route } from "@playwright/test";

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function stubBackend(page: Page) {
  await page.route("**/backend/api/health", (route) => fulfillJson(route, { status: "ok" }));
  await page.route("**/backend/api/system/status", (route) =>
    fulfillJson(route, {
      status: "ok",
      environment: "development",
      python_version: "3.13.0",
      uptime_seconds: 12,
      database: { connected: true },
      camera: { available: true, running: false },
      face_detection: {
        enabled: true,
        model_loaded: true,
        provider: "CPUExecutionProvider",
        last_inference_ms: null,
        tracking_enabled: true,
        quality_enabled: true,
        alignment_enabled: true,
        embedding_enabled: true,
        embedding_provider: "CPUExecutionProvider",
        recognition_enabled: true,
        recognition_threshold: 0.363,
        event_logging_enabled: true,
      },
    }),
  );
  await page.route("**/backend/api/cameras", (route) =>
    fulfillJson(route, {
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
    }),
  );
  await page.route("**/backend/api/cameras/default", (route) =>
    fulfillJson(route, {
      id: "default",
      name: "USB Webcam",
      state: "closed",
      device_index: 0,
      width: 1280,
      height: 720,
      fps: 15,
      last_frame_at: null,
      error: null,
    }),
  );
  await page.route("**/backend/api/persons", (route) => fulfillJson(route, { persons: [] }));
  await page.route("**/backend/api/events**", (route) =>
    fulfillJson(route, { items: [], page: 1, page_size: 20, total: 0 }),
  );
}

test.describe("smoke", () => {
  test.beforeEach(async ({ page }) => {
    await stubBackend(page);
  });

  test("application and dashboard load", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "داشبورد" })).toBeVisible();
    await expect(page.getByText("سلامت backend")).toBeVisible();
  });

  test("people page loads", async ({ page }) => {
    await page.goto("/people");
    await expect(page.getByRole("heading", { name: "افراد" })).toBeVisible();
    await expect(page.getByText("No people enrolled yet.")).toBeVisible();
  });

  test("events page loads", async ({ page }) => {
    await page.goto("/events");
    await expect(page.getByRole("heading", { name: "رویدادها" })).toBeVisible();
  });

  test("camera page loads", async ({ page }) => {
    await page.goto("/camera");
    await expect(page.getByRole("heading", { name: "دوربین" })).toBeVisible();
    await expect(page.getByText("Stopped")).toBeVisible();
  });
});
