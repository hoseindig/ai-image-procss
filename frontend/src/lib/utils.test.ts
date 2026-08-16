import { describe, expect, it } from "vitest";

import { formatSimilarity } from "@/lib/utils";

describe("formatSimilarity", () => {
  it("formats scores without converting to percentage", () => {
    expect(formatSimilarity(0.742)).toBe("0.742");
    expect(formatSimilarity(0.311)).toBe("0.311");
  });

  it("handles missing values", () => {
    expect(formatSimilarity(null)).toBeNull();
    expect(formatSimilarity(undefined)).toBeNull();
  });
});
