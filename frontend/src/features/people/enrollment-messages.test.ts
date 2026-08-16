import { describe, expect, it } from "vitest";

import {
  enrollmentQualityLabel,
  enrollmentUserMessage,
} from "@/features/people/enrollment-messages";

describe("enrollment messages", () => {
  it("maps machine codes to user-friendly text", () => {
    expect(enrollmentUserMessage("multiple_faces", null, "multiple_faces")).toBe(
      "Only one face should be visible.",
    );
    expect(enrollmentUserMessage("quality_rejected", null, "face_too_small")).toBe(
      "Move closer to the camera.",
    );
    expect(enrollmentUserMessage("failed", null, "camera_not_running")).toBe(
      "Start the camera first.",
    );
  });

  it("prefers backend message when no code mapping exists", () => {
    expect(enrollmentUserMessage("face_detected", "Face detected", null)).toBe("Face detected");
  });

  it("labels quality states", () => {
    expect(enrollmentQualityLabel("ready")).toBe("Quality: OK");
    expect(enrollmentQualityLabel("quality_rejected")).toBe("Quality: rejected");
  });
});
