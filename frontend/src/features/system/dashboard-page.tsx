"use client";

import Link from "next/link";

import { EventSummary } from "@/components/recognition-display";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCameras } from "@/features/camera/hooks";
import { useEvents } from "@/features/events/hooks";
import { usePersons } from "@/features/people/hooks";
import { useHealth, useSystemStatus } from "@/features/system/hooks";
import { isApiError } from "@/lib/api/client";
import { formatDateTime } from "@/lib/utils";

function statusBadge(ok: boolean, labelOk: string, labelBad: string) {
  return <Badge variant={ok ? "success" : "danger"}>{ok ? labelOk : labelBad}</Badge>;
}

export function DashboardPage() {
  const health = useHealth();
  const system = useSystemStatus();
  const cameras = useCameras();
  const persons = usePersons();
  const events = useEvents({ page: 1, page_size: 5 });

  const personNames = new Map(
    (persons.data?.persons ?? []).map((person) => [person.id, person.display_name]),
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">داشبورد</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          وضعیت سامانه از APIهای واقعی backend — بدون آمار ساختگی.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>سلامت backend</CardTitle>
          </CardHeader>
          <CardContent>
            {health.isLoading ? <LoadingState /> : null}
            {health.isError ? (
              <ErrorState
                message={
                  isApiError(health.error)
                    ? health.error.message
                    : "Backend unavailable"
                }
                onRetry={() => void health.refetch()}
              />
            ) : null}
            {health.data ? statusBadge(health.data.status === "ok", "ok", "failed") : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>وضعیت سیستم</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {system.isLoading ? <LoadingState /> : null}
            {system.isError ? (
              <ErrorState
                message={
                  isApiError(system.error) ? system.error.message : "Failed to load system status"
                }
                onRetry={() => void system.refetch()}
              />
            ) : null}
            {system.data ? (
              <>
                <div className="flex items-center justify-between gap-2">
                  <span>Ready</span>
                  {statusBadge(system.data.ready, "ready", "not ready")}
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span>Status</span>
                  {statusBadge(system.data.status === "ok", "ok", "degraded")}
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span>Database</span>
                  {statusBadge(system.data.database.connected, "connected", "disconnected")}
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span>Camera available</span>
                  {statusBadge(system.data.camera.available, "yes", "no")}
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span>Camera running</span>
                  {statusBadge(system.data.camera.running, "running", "stopped")}
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span>Recognition</span>
                  {statusBadge(
                    system.data.face_detection.recognition_enabled,
                    "enabled",
                    "disabled",
                  )}
                </div>
                {system.data.face_detection.recognition_threshold != null ? (
                  <p className="text-muted-foreground">
                    Threshold: {system.data.face_detection.recognition_threshold}
                  </p>
                ) : null}
              </>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>دوربین</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {cameras.isLoading ? <LoadingState /> : null}
            {cameras.isError ? (
              <ErrorState
                message={isApiError(cameras.error) ? cameras.error.message : "Camera list failed"}
                onRetry={() => void cameras.refetch()}
              />
            ) : null}
            {cameras.data?.cameras.length === 0 ? (
              <EmptyState title="دوربینی ثبت نشده است." />
            ) : null}
            {cameras.data?.cameras.map((camera) => (
              <div key={camera.id} className="flex items-center justify-between gap-2">
                <div>
                  <p className="font-medium">{camera.name}</p>
                  <p className="text-muted-foreground">{camera.id}</p>
                </div>
                <Badge variant={camera.state === "running" ? "success" : "secondary"}>
                  {camera.state}
                </Badge>
              </div>
            ))}
            <Link href="/camera" className="inline-block text-sm text-primary underline-offset-4 hover:underline">
              صفحه دوربین
            </Link>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle>رویدادهای اخیر</CardTitle>
          <Link href="/events" className="text-sm text-primary underline-offset-4 hover:underline">
            همه رویدادها
          </Link>
        </CardHeader>
        <CardContent>
          {events.isLoading ? <LoadingState /> : null}
          {events.isError ? (
            <ErrorState
              message={isApiError(events.error) ? events.error.message : "Events failed"}
              onRetry={() => void events.refetch()}
            />
          ) : null}
          {events.data && events.data.items.length === 0 ? (
            <EmptyState title="هنوز رویدادی ثبت نشده است." />
          ) : null}
          {events.data && events.data.items.length > 0 ? (
            <ul className="divide-y">
              {events.data.items.map((event) => (
                <li key={event.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:justify-between">
                  <EventSummary
                    event={event}
                    personName={event.person_id ? personNames.get(event.person_id) : null}
                  />
                  <div className="text-sm text-muted-foreground">
                    <p>{formatDateTime(event.occurred_at)}</p>
                    <p>
                      {event.camera_id} / track {event.track_id}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          {events.data ? (
            <p className="mt-3 text-sm text-muted-foreground">Total events: {events.data.total}</p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
