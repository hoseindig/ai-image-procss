"use client";

import { useMemo } from "react";

import { RecognitionSummary } from "@/components/recognition-display";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useCamera,
  useCameras,
  useDetections,
  useStartCamera,
  useStopCamera,
} from "@/features/camera/hooks";
import { MjpegPreview } from "@/features/camera/mjpeg-preview";
import { isApiError } from "@/lib/api/client";
import type { CameraState, FaceTrack } from "@/types/api";

function cameraUiState(state: CameraState | undefined, pending: boolean, stopPending: boolean): string {
  if (pending) return "Starting";
  if (stopPending) return "Stopping";
  switch (state) {
    case "running":
      return "Running";
    case "opening":
    case "open":
      return "Starting";
    case "error":
      return "Camera failure";
    case "stopped":
    case "closed":
      return "Stopped";
    default:
      return "Loading";
  }
}

function pickPrimaryTrack(tracks: FaceTrack[]): FaceTrack | null {
  const matched = tracks.find((track) => track.recognition?.status === "matched");
  if (matched) return matched;
  const confirmed = tracks.find((track) => track.state === "confirmed");
  return confirmed ?? tracks[0] ?? null;
}

export function CameraPage() {
  const cameras = useCameras();
  const cameraId = cameras.data?.cameras[0]?.id;
  const camera = useCamera(cameraId);
  const start = useStartCamera();
  const stop = useStopCamera();
  const running = camera.data?.state === "running";
  const detections = useDetections(cameraId, running);

  const primary = useMemo(
    () => pickPrimaryTrack(detections.data?.tracks ?? []),
    [detections.data?.tracks],
  );

  if (cameras.isLoading) {
    return <LoadingState label="در حال دریافت فهرست دوربین…" />;
  }

  if (cameras.isError) {
    return (
      <ErrorState
        title="Backend unavailable"
        message={
          isApiError(cameras.error)
            ? cameras.error.message
            : "Cannot reach the backend. Check that npm run dev is running."
        }
        onRetry={() => void cameras.refetch()}
      />
    );
  }

  if (!cameraId) {
    return <EmptyState title="دوربینی پیکربندی نشده است." />;
  }

  const statusLabel = cameraUiState(camera.data?.state, start.isPending, stop.isPending);
  const mutationError = start.error ?? stop.error;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">دوربین</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            پیش‌نمایش MJPEG از backend — بدون getUserMedia در مرورگر.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant={
              statusLabel === "Running"
                ? "success"
                : statusLabel === "Camera failure"
                  ? "danger"
                  : "secondary"
            }
          >
            {statusLabel}
          </Badge>
          <Button
            type="button"
            onClick={() => start.mutate(cameraId)}
            disabled={running || start.isPending || stop.isPending}
          >
            Start
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => stop.mutate(cameraId)}
            disabled={!running || start.isPending || stop.isPending}
          >
            Stop
          </Button>
        </div>
      </div>

      {camera.isError ? (
        <ErrorState
          title="وضعیت دوربین"
          message={isApiError(camera.error) ? camera.error.message : "Camera status failed"}
          onRetry={() => void camera.refetch()}
        />
      ) : null}

      {mutationError ? (
        <ErrorState
          title="کنترل دوربین"
          message={isApiError(mutationError) ? mutationError.message : "Camera control failed"}
        />
      ) : null}

      {camera.data?.error ? (
        <ErrorState title="خطای سخت‌افزار دوربین" message={camera.data.error} />
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>
              {camera.data?.name ?? cameraId} — live preview
            </CardTitle>
          </CardHeader>
          <CardContent>
            <MjpegPreview cameraId={cameraId} state={camera.data?.state ?? "closed"} />
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>وضعیت pipeline</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>Detection: {detections.data?.enabled ? "enabled" : "disabled / idle"}</p>
              <p>Tracks: {detections.data?.tracks.length ?? 0}</p>
              <p>Faces: {detections.data?.faces.length ?? 0}</p>
              <p>Embedded: {detections.data?.embedded_count ?? 0}</p>
              {detections.data?.error ? (
                <p className="text-red-700">Detection error: {detections.data.error}</p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>شناسایی</CardTitle>
            </CardHeader>
            <CardContent>
              {running && detections.isError ? (
                <ErrorState
                  title="Recognition unavailable"
                  message={
                    isApiError(detections.error)
                      ? detections.error.message
                      : "Failed to load detection results"
                  }
                  onRetry={() => void detections.refetch()}
                />
              ) : null}
              {running && detections.isLoading ? <LoadingState /> : null}
              {!running ? (
                <p className="text-sm text-muted-foreground">دوربین در حال اجرا نیست.</p>
              ) : null}
              {running && !detections.isLoading && !detections.isError && !primary ? (
                <EmptyState title="چهره‌ای در فریم فعلی نیست." />
              ) : null}
              {primary ? (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Track #{primary.track_id} ({primary.state})
                  </p>
                  <RecognitionSummary recognition={primary.recognition} />
                  <p className="text-sm">
                    Quality:{" "}
                    {primary.quality
                      ? primary.quality.accepted
                        ? "accepted"
                        : `rejected (${primary.quality.reasons.join(", ") || "n/a"})`
                      : "—"}
                  </p>
                  <p className="text-sm">
                    Embedding: {primary.embedding?.status ?? "—"}
                    {primary.embedding?.dimension
                      ? ` (${primary.embedding.dimension}D metadata)`
                      : ""}
                  </p>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>آخرین tracks</CardTitle>
        </CardHeader>
        <CardContent>
          {(detections.data?.tracks.length ?? 0) === 0 ? (
            <EmptyState title="Track فعالی نیست." />
          ) : (
            <ul className="divide-y">
              {detections.data?.tracks.map((track) => (
                <li key={track.track_id} className="flex flex-col gap-2 py-3 sm:flex-row sm:justify-between">
                  <div>
                    <p className="font-medium">Track #{track.track_id}</p>
                    <p className="text-sm text-muted-foreground">
                      state={track.state} confidence={track.confidence.toFixed(3)}
                    </p>
                  </div>
                  <RecognitionSummary recognition={track.recognition} />
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
