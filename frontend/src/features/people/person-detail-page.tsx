"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useCreateEnrollment,
  useDeleteEnrollment,
  useEnrollments,
  usePerson,
  useUpdatePerson,
} from "@/features/people/hooks";
import { isApiError } from "@/lib/api/client";
import { formatDateTime } from "@/lib/utils";

const EMBEDDING_DIM = 128;

function parseEmbeddingJson(raw: string): number[] {
  const parsed: unknown = JSON.parse(raw);
  if (!Array.isArray(parsed)) {
    throw new Error("Embedding must be a JSON array of 128 numbers");
  }
  if (parsed.length !== EMBEDDING_DIM) {
    throw new Error(`Embedding must have exactly ${EMBEDDING_DIM} numbers`);
  }
  const values = parsed.map((item) => {
    if (typeof item !== "number" || Number.isNaN(item)) {
      throw new Error("Embedding values must be numbers");
    }
    return item;
  });
  return values;
}

export function PersonDetailPage({ personId }: { personId: string }) {
  const person = usePerson(personId);
  const enrollments = useEnrollments(personId);
  const update = useUpdatePerson(personId);
  const createEnrollment = useCreateEnrollment(personId);
  const deleteEnrollment = useDeleteEnrollment(personId);
  const [embeddingJson, setEmbeddingJson] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);

  function onEnroll(event: FormEvent) {
    event.preventDefault();
    setParseError(null);
    try {
      const embedding = parseEmbeddingJson(embeddingJson);
      createEnrollment.mutate(
        {
          embedding,
          normalized: true,
          quality: { accepted: true },
        },
        {
          onSuccess: () => setEmbeddingJson(""),
        },
      );
    } catch (error) {
      setParseError(error instanceof Error ? error.message : "Invalid embedding JSON");
    }
  }

  if (person.isLoading) {
    return <LoadingState />;
  }

  if (person.isError) {
    return (
      <ErrorState
        title="فرد یافت نشد"
        message={isApiError(person.error) ? person.error.message : "Failed to load person"}
        onRetry={() => void person.refetch()}
      />
    );
  }

  if (!person.data) {
    return <EmptyState title="فرد یافت نشد." />;
  }

  const data = person.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">
            <Link href="/people" className="underline-offset-4 hover:underline">
              افراد
            </Link>{" "}
            / {data.display_name}
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{data.display_name}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge variant={data.active ? "success" : "secondary"}>
              {data.active ? "active" : "inactive"}
            </Badge>
            <Badge variant="outline">enrollments: {data.enrollment_count}</Badge>
          </div>
        </div>
        <Button
          type="button"
          variant="outline"
          disabled={update.isPending}
          onClick={() => update.mutate({ active: !data.active })}
        >
          {data.active ? "Deactivate" : "Activate"}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>جزئیات</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
          <p>
            <span className="text-muted-foreground">Created:</span> {formatDateTime(data.created_at)}
          </p>
          <p>
            <span className="text-muted-foreground">Updated:</span> {formatDateTime(data.updated_at)}
          </p>
          <p>
            <span className="text-muted-foreground">ID:</span> {data.id}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>ثبت‌نام‌ها (metadata)</CardTitle>
          <CardDescription>
            فقط فراداده نمایش داده می‌شود. بردار خام 128 بعدی هرگز در پاسخ GET یا UI نیست.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {enrollments.isLoading ? <LoadingState /> : null}
          {enrollments.isError ? (
            <ErrorState
              message={
                isApiError(enrollments.error)
                  ? enrollments.error.message
                  : "Failed to load enrollments"
              }
              onRetry={() => void enrollments.refetch()}
            />
          ) : null}
          {enrollments.data && enrollments.data.enrollments.length === 0 ? (
            <EmptyState title="هنوز نمونه‌ای ثبت نشده است." />
          ) : null}
          {enrollments.data && enrollments.data.enrollments.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Dim</TableHead>
                  <TableHead>Quality</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>اقدام</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {enrollments.data.enrollments.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-xs">{item.id.slice(0, 8)}…</TableCell>
                    <TableCell>{item.dimension}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {item.face_width ?? "—"}×{item.face_height ?? "—"} / sharp{" "}
                      {item.sharpness ?? "—"}
                    </TableCell>
                    <TableCell>{formatDateTime(item.created_at)}</TableCell>
                    <TableCell>
                      <Button
                        type="button"
                        size="sm"
                        variant="destructive"
                        disabled={deleteEnrollment.isPending}
                        onClick={() => deleteEnrollment.mutate(item.id)}
                      >
                        Remove
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-amber-300 bg-amber-50">
        <CardHeader>
          <CardTitle>Developer / testing enrollment</CardTitle>
          <CardDescription>
            Phase 7A accepts a precomputed 128-D embedding. This UI does{" "}
            <strong>not</strong> run SFace in the browser. Paste a JSON array of 128 floats from a
            trusted local tool/test harness only.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={onEnroll}>
            <div className="space-y-2">
              <Label htmlFor="embedding-json">Embedding JSON (128 floats)</Label>
              <textarea
                id="embedding-json"
                className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={embeddingJson}
                onChange={(event) => setEmbeddingJson(event.target.value)}
                placeholder="[0.01, -0.02, ...]"
                spellCheck={false}
              />
            </div>
            {(parseError || createEnrollment.isError) && (
              <ErrorState
                message={
                  parseError ??
                  (isApiError(createEnrollment.error)
                    ? createEnrollment.error.message
                    : "Enrollment failed")
                }
              />
            )}
            <Button type="submit" disabled={createEnrollment.isPending || !embeddingJson.trim()}>
              Add enrollment (dev)
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
