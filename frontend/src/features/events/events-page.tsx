"use client";

import { useMemo, useState } from "react";

import { EventSummary } from "@/components/recognition-display";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCameras } from "@/features/camera/hooks";
import { useEvents } from "@/features/events/hooks";
import { usePersons } from "@/features/people/hooks";
import { isApiError } from "@/lib/api/client";
import { formatDateTime } from "@/lib/utils";
import type { EventListParams, EventType } from "@/types/api";

const PAGE_SIZE = 20;

export function EventsPage() {
  const [page, setPage] = useState(1);
  const [eventType, setEventType] = useState<string>("all");
  const [personId, setPersonId] = useState<string>("all");
  const [cameraId, setCameraId] = useState<string>("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const params = useMemo<EventListParams>(() => {
    const next: EventListParams = { page, page_size: PAGE_SIZE };
    if (eventType !== "all") next.event_type = eventType as EventType;
    if (personId !== "all") next.person_id = personId;
    if (cameraId !== "all") next.camera_id = cameraId;
    if (from) next.from = new Date(from).toISOString();
    if (to) next.to = new Date(to).toISOString();
    return next;
  }, [page, eventType, personId, cameraId, from, to]);

  const events = useEvents(params);
  const persons = usePersons();
  const cameras = useCameras();

  const personNames = new Map(
    (persons.data?.persons ?? []).map((person) => [person.id, person.display_name]),
  );

  const totalPages = events.data
    ? Math.max(1, Math.ceil(events.data.total / events.data.page_size))
    : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">رویدادها</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          صفحه‌بندی و فیلتر از backend. Similarity به صورت امتیاز نمایش داده می‌شود، نه درصد.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>فیلترها</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <div className="space-y-2">
            <Label>نوع رویداد</Label>
            <Select
              value={eventType}
              onValueChange={(value) => {
                setPage(1);
                setEventType(value);
              }}
            >
              <SelectTrigger aria-label="نوع رویداد">
                <SelectValue placeholder="همه" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">همه</SelectItem>
                <SelectItem value="recognized">recognized</SelectItem>
                <SelectItem value="unknown_face">unknown_face</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>فرد</Label>
            <Select
              value={personId}
              onValueChange={(value) => {
                setPage(1);
                setPersonId(value);
              }}
            >
              <SelectTrigger aria-label="فرد">
                <SelectValue placeholder="همه" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">همه</SelectItem>
                {(persons.data?.persons ?? []).map((person) => (
                  <SelectItem key={person.id} value={person.id}>
                    {person.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>دوربین</Label>
            <Select
              value={cameraId}
              onValueChange={(value) => {
                setPage(1);
                setCameraId(value);
              }}
            >
              <SelectTrigger aria-label="دوربین">
                <SelectValue placeholder="همه" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">همه</SelectItem>
                {(cameras.data?.cameras ?? []).map((camera) => (
                  <SelectItem key={camera.id} value={camera.id}>
                    {camera.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="from">از تاریخ</Label>
            <Input
              id="from"
              type="datetime-local"
              value={from}
              onChange={(event) => {
                setPage(1);
                setFrom(event.target.value);
              }}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="to">تا تاریخ</Label>
            <Input
              id="to"
              type="datetime-local"
              value={to}
              onChange={(event) => {
                setPage(1);
                setTo(event.target.value);
              }}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>نتایج</CardTitle>
        </CardHeader>
        <CardContent>
          {events.isLoading ? <LoadingState /> : null}
          {events.isError ? (
            <ErrorState
              message={isApiError(events.error) ? events.error.message : "Failed to load events"}
              onRetry={() => void events.refetch()}
            />
          ) : null}
          {events.data && events.data.items.length === 0 ? (
            <EmptyState title="رویدادی با این فیلترها یافت نشد." />
          ) : null}
          {events.data && events.data.items.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>زمان</TableHead>
                  <TableHead>رویداد</TableHead>
                  <TableHead>دوربین</TableHead>
                  <TableHead>Track</TableHead>
                  <TableHead>جزئیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.data.items.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell>{formatDateTime(event.occurred_at)}</TableCell>
                    <TableCell>{event.event_type}</TableCell>
                    <TableCell>{event.camera_id}</TableCell>
                    <TableCell>{event.track_id}</TableCell>
                    <TableCell>
                      <EventSummary
                        event={event}
                        personName={
                          event.person_id ? personNames.get(event.person_id) : null
                        }
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}

          {events.data ? (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                صفحه {events.data.page} از {totalPages} — مجموع {events.data.total}
              </p>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((value) => Math.max(1, value - 1))}
                >
                  قبلی
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={page >= totalPages}
                  onClick={() => setPage((value) => value + 1)}
                >
                  بعدی
                </Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
