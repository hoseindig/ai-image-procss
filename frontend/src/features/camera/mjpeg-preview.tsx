"use client";

import { useEffect, useState } from "react";

import { camerasApi } from "@/lib/api";
import type { CameraState } from "@/types/api";

export function MjpegPreview({
  cameraId,
  state,
}: {
  cameraId: string;
  state: CameraState;
}) {
  const [streamFailed, setStreamFailed] = useState(false);

  useEffect(() => {
    setStreamFailed(false);
  }, [cameraId, state]);

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

  if (streamFailed) {
    return (
      <div className="flex aspect-video flex-col items-center justify-center gap-2 rounded-lg border bg-muted px-4 text-center text-sm text-muted-foreground">
        <p>پیش‌نمایش قطع شد یا backend در دسترس نیست.</p>
        <button
          type="button"
          className="text-foreground underline"
          onClick={() => setStreamFailed(false)}
        >
          Retry preview
        </button>
      </div>
    );
  }

  return (
    // Backend owns the webcam; browser only displays the MJPEG stream.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      key={`${cameraId}-preview`}
      src={camerasApi.previewUrl(cameraId)}
      alt={`پیش‌نمایش زنده دوربین ${cameraId}`}
      className="aspect-video w-full rounded-lg border bg-black object-contain"
      onError={() => setStreamFailed(true)}
    />
  );
}
