"use client";

import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useCameras, useStartCamera } from "@/features/camera/hooks";
import { MjpegPreview } from "@/features/camera/mjpeg-preview";
import {
  enrollmentQualityLabel,
  enrollmentUserMessage,
} from "@/features/people/enrollment-messages";
import {
  useCancelEnrollmentSession,
  useCaptureEnrollmentSession,
  useEnrollmentSession,
  useStartEnrollmentSession,
} from "@/features/people/hooks";
import { isApiError } from "@/lib/api/client";
import type { EnrollmentSessionState } from "@/types/api";

const TERMINAL: EnrollmentSessionState[] = ["completed", "cancelled", "failed"];

export function FaceEnrollmentPanel({
  personId,
  personActive,
  onCompleted,
}: {
  personId: string;
  personActive: boolean;
  onCompleted?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const cameras = useCameras();
  const cameraId = cameras.data?.cameras[0]?.id;
  const cameraState = cameras.data?.cameras[0]?.state ?? "closed";
  const startCamera = useStartCamera();
  const startSession = useStartEnrollmentSession(personId);
  const sessionQuery = useEnrollmentSession(personId, sessionId);
  const capture = useCaptureEnrollmentSession(personId);
  const cancel = useCancelEnrollmentSession(personId);

  const session = sessionQuery.data;
  const uiState: EnrollmentSessionState | "idle" | "starting" =
    !open ? "idle" : startSession.isPending && !sessionId ? "starting" : session?.state ?? "starting";

  useEffect(() => {
    if (session?.state === "completed") {
      onCompleted?.();
    }
  }, [session?.state, onCompleted]);

  async function begin() {
    setOpen(true);
    setSessionId(null);
    try {
      if (cameraId && cameraState !== "running") {
        await startCamera.mutateAsync(cameraId);
      }
      const created = await startSession.mutateAsync(cameraId);
      setSessionId(created.id);
    } catch {
      // Error surfaced via startSession.error / startCamera.error
    }
  }

  async function onCapture() {
    if (!sessionId) return;
    try {
      await capture.mutateAsync(sessionId);
    } catch {
      // surfaced via capture.error
    }
  }

  async function onClose() {
    if (sessionId && session && !TERMINAL.includes(session.state)) {
      try {
        await cancel.mutateAsync(sessionId);
      } catch {
        // ignore cancel errors on close
      }
    }
    setOpen(false);
    setSessionId(null);
    startSession.reset();
    capture.reset();
  }

  if (!open) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Enroll Face</CardTitle>
          <CardDescription>
            Capture a face sample from the live backend camera. SFace runs only on the server.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button type="button" onClick={() => void begin()} disabled={!personActive}>
            Enroll Face
          </Button>
          {!personActive ? (
            <p className="mt-2 text-sm text-muted-foreground">Activate the person before enrolling.</p>
          ) : null}
        </CardContent>
      </Card>
    );
  }

  const instruction = session
    ? enrollmentUserMessage(session.state, session.message, session.error_code)
    : startSession.isError
      ? isApiError(startSession.error)
        ? startSession.error.message
        : "Failed to start enrollment"
      : "Starting enrollment…";

  const canCapture =
    session?.state === "ready" && !capture.isPending && !TERMINAL.includes(session.state);

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>Enroll Face</CardTitle>
          <CardDescription>Backend MJPEG + quality gate. No browser-side AI.</CardDescription>
        </div>
        <Button type="button" variant="outline" onClick={() => void onClose()}>
          Close
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {cameraId ? (
          <MjpegPreview cameraId={cameraId} state={cameraState === "running" ? "running" : cameraState} />
        ) : (
          <LoadingState label="Loading camera…" />
        )}

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">State: {uiState}</Badge>
          {session ? <Badge variant="outline">{enrollmentQualityLabel(session.state)}</Badge> : null}
          {session?.error_code ? (
            <Badge variant="danger">code: {session.error_code}</Badge>
          ) : null}
        </div>

        <p className="text-sm" role="status" aria-live="polite">
          {instruction}
        </p>

        {(startCamera.isError || startSession.isError || capture.isError || sessionQuery.isError) && (
          <ErrorState
            message={
              isApiError(startCamera.error)
                ? startCamera.error.message
                : isApiError(startSession.error)
                  ? startSession.error.message
                  : isApiError(capture.error)
                    ? capture.error.message
                    : isApiError(sessionQuery.error)
                      ? sessionQuery.error.message
                      : "Enrollment error"
            }
          />
        )}

        {session?.state === "completed" ? (
          <ErrorState
            className="border-emerald-200 bg-emerald-50 text-emerald-950"
            title="Success"
            message={`Enrollment saved${session.enrollment_id ? ` (${session.enrollment_id.slice(0, 8)}…)` : ""}.`}
          />
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            onClick={() => void onCapture()}
            disabled={!canCapture}
            aria-busy={capture.isPending}
          >
            {capture.isPending ? "Capturing…" : "Capture"}
          </Button>
          <Button type="button" variant="outline" onClick={() => void begin()}>
            Restart session
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
