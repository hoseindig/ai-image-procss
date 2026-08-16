import { expect, test, type Page, type Route } from "@playwright/test";

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

type Person = {
  id: string;
  display_name: string;
  active: boolean;
  created_at: string;
  updated_at: string;
  enrollment_count: number;
};

/**
 * Mocked/stubbed backend for Browser E2E.
 * Does NOT use a physical webcam or real recognition.
 */
async function stubBackend(page: Page) {
  const persons: Person[] = [];
  let enrollmentSession = {
    id: "sess-1",
    person_id: "",
    camera_id: "default",
    state: "waiting_for_face",
    track_id: null as number | null,
    quality_reasons: [] as string[],
    message: "Look at the camera so one face is visible",
    error_code: null as string | null,
    enrollment_id: null as string | null,
    face_width: null as number | null,
    face_height: null as number | null,
    sharpness: null as number | null,
    brightness: null as number | null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };

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
      ready: true,
    }),
  );

  await page.route("**/backend/api/cameras/default/start", (route) =>
    fulfillJson(route, {
      id: "default",
      name: "USB Webcam",
      state: "running",
      device_index: 0,
      width: 1280,
      height: 720,
      fps: 15,
      last_frame_at: "2026-01-01T00:00:00Z",
      error: null,
    }),
  );
  await page.route("**/backend/api/cameras/default/stop", (route) =>
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
  await page.route("**/backend/api/cameras/default/detections", (route) =>
    fulfillJson(route, {
      camera_id: "default",
      enabled: true,
      timestamp: null,
      faces: [],
      tracks: [],
      inference_ms: null,
      tracking_ms: null,
      quality_ms: null,
      alignment_ms: null,
      embedding_ms: null,
      recognition_ms: null,
      aligned_count: 0,
      embedded_count: 0,
      error: null,
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

  await page.route("**/backend/api/persons/**/enrollment-sessions/**/capture", (route) => {
    enrollmentSession = {
      ...enrollmentSession,
      state: "completed",
      enrollment_id: "enroll-1",
      message: "Enrollment sample captured successfully",
    };
    return fulfillJson(route, enrollmentSession);
  });

  await page.route("**/backend/api/persons/**/enrollment-sessions/**", async (route) => {
    const method = route.request().method();
    if (method === "DELETE") {
      enrollmentSession = { ...enrollmentSession, state: "cancelled", message: "cancelled" };
      return fulfillJson(route, enrollmentSession);
    }
    if (method === "GET") {
      return fulfillJson(route, enrollmentSession);
    }
    return route.fallback();
  });

  await page.route("**/backend/api/persons/**/enrollment-sessions", async (route) => {
    if (route.request().method() === "POST") {
      const url = route.request().url();
      const personId = url.match(/persons\/([^/]+)\/enrollment-sessions/)?.[1] ?? "";
      enrollmentSession = {
        ...enrollmentSession,
        id: "sess-1",
        person_id: personId,
        state: "waiting_for_face",
        message: "Look at the camera so one face is visible",
        error_code: null,
        enrollment_id: null,
      };
      return fulfillJson(route, enrollmentSession, 201);
    }
    return route.fallback();
  });

  await page.route("**/backend/api/persons/**/enrollments", (route) =>
    fulfillJson(route, { enrollments: [] }),
  );

  await page.route("**/backend/api/persons/**", async (route) => {
    const method = route.request().method();
    const url = new URL(route.request().url());
    const parts = url.pathname.split("/").filter(Boolean);
    // .../backend/api/persons/{id}
    const id = parts[parts.length - 1];
    if (method === "GET" && id && id !== "persons") {
      const person = persons.find((item) => item.id === id);
      if (!person) {
        return fulfillJson(
          route,
          { error: { code: "person_not_found", message: "Person was not found" } },
          404,
        );
      }
      return fulfillJson(route, person);
    }
    if (method === "PATCH") {
      const person = persons.find((item) => item.id === id);
      if (!person) {
        return fulfillJson(
          route,
          { error: { code: "person_not_found", message: "Person was not found" } },
          404,
        );
      }
      const body = route.request().postDataJSON() as { active?: boolean };
      if (typeof body.active === "boolean") person.active = body.active;
      return fulfillJson(route, person);
    }
    return route.fallback();
  });

  await page.route("**/backend/api/persons", async (route) => {
    if (route.request().method() === "GET") {
      return fulfillJson(route, { persons });
    }
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON() as { display_name: string };
      const now = "2026-01-01T00:00:00Z";
      const person: Person = {
        id: `p-${persons.length + 1}`,
        display_name: body.display_name,
        active: true,
        created_at: now,
        updated_at: now,
        enrollment_count: 0,
      };
      persons.push(person);
      return fulfillJson(route, person, 201);
    }
    return route.fallback();
  });

  await page.route("**/backend/api/events**", (route) =>
    fulfillJson(route, {
      items: [
        {
          id: "ev-1",
          event_type: "recognized",
          camera_id: "default",
          track_id: 2,
          person_id: persons[0]?.id ?? null,
          enrollment_id: null,
          similarity: 0.742,
          occurred_at: "2026-01-01T12:00:00Z",
          created_at: "2026-01-01T12:00:00Z",
        },
        {
          id: "ev-2",
          event_type: "unknown_face",
          camera_id: "default",
          track_id: 3,
          person_id: null,
          enrollment_id: null,
          similarity: 0.311,
          occurred_at: "2026-01-01T12:01:00Z",
          created_at: "2026-01-01T12:01:00Z",
        },
      ],
      page: 1,
      page_size: 20,
      total: 2,
    }),
  );
}

test.describe("browser e2e (mocked backend)", () => {
  test.beforeEach(async ({ page }) => {
    await stubBackend(page);
  });

  test("dashboard loads", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "داشبورد" })).toBeVisible();
    await expect(page.getByText("سلامت backend")).toBeVisible();
  });

  test("camera page loads", async ({ page }) => {
    await page.goto("/camera");
    await expect(page.getByRole("heading", { name: "دوربین" })).toBeVisible();
    await expect(page.getByText("Stopped")).toBeVisible();
  });

  test("people page loads", async ({ page }) => {
    await page.goto("/people");
    await expect(page.getByRole("heading", { name: "افراد" })).toBeVisible();
    await expect(page.getByText("No people enrolled yet.")).toBeVisible();
  });

  test("events page loads and renders similarity scores", async ({ page }) => {
    await page.goto("/events");
    await expect(page.getByRole("heading", { name: "رویدادها" })).toBeVisible();
    await expect(page.getByText("Recognized")).toBeVisible();
    await expect(page.getByText("Similarity: 0.742")).toBeVisible();
    await expect(page.getByText("Unknown face")).toBeVisible();
    await expect(page.getByText("Similarity: 0.311")).toBeVisible();
  });

  test("create person and open detail", async ({ page }) => {
    await page.goto("/people");
    await page.getByLabel("نام نمایشی").fill("E2E Person");
    await page.getByRole("button", { name: "ایجاد" }).click();
    await expect(page.getByRole("link", { name: "E2E Person" })).toBeVisible();
    await page.getByRole("link", { name: "E2E Person" }).click();
    await expect(page.getByRole("heading", { name: "E2E Person" })).toBeVisible();
    await expect(page.getByText("enrollments: 0")).toBeVisible();
  });

  test("enrollment UI opens and shows waiting state", async ({ page }) => {
    await page.goto("/people");
    await page.getByLabel("نام نمایشی").fill("Enroll UI Person");
    await page.getByRole("button", { name: "ایجاد" }).click();
    await page.getByRole("link", { name: "Enroll UI Person" }).click();
    await page.getByRole("button", { name: "Enroll Face" }).click();
    await expect(page.getByText(/Look at the camera/i)).toBeVisible();
    await expect(page.getByRole("button", { name: "Capture" })).toBeDisabled();
    await expect(page.getByText("State: waiting_for_face")).toBeVisible();
  });

  test("API error state renders on dashboard", async ({ page }) => {
    await page.unroute("**/backend/api/health");
    await page.route("**/backend/api/health", (route) =>
      fulfillJson(
        route,
        { error: { code: "internal_error", message: "Backend unavailable for E2E" } },
        503,
      ),
    );
    await page.goto("/");
    await expect(page.getByText("Backend unavailable for E2E")).toBeVisible();
  });
});
