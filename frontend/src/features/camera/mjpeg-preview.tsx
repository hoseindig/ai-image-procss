"use client";

import { camerasApi } from "@/lib/api";
import type { CameraState } from "@/types/api";

export function MjpegPreview({
  cameraId,
  state,
}: {
  cameraId: string;
  state: CameraState;
}) {
  if (state !== "running") {
    return (
      <div className="flex aspect-video items-center justify-center rounded-lg border bg-muted text-sm text-muted-foreground">
        {state === "opening" || state === "open"
          ? "در حال راه‌اندازی پیش‌نمایش…"
          : state === "error"
            ? "خطای دوربین — پیش‌نمایش در دسترس نیست"
            : "دوربین متوقف است. برای پیش‌نمایش MJPEG ابتدا Start کنید."}
      </div>
    );
  }

  return (
    // Backend owns the webcam; browser only displays the MJPEG stream.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={camerasApi.previewUrl(cameraId)}
      alt={`پیش‌نمایش زنده دوربین ${cameraId}`}
      className="aspect-video w-full rounded-lg border bg-black object-contain"
    />
  );
}
