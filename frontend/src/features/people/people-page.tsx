"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCreatePerson, usePersons, useUpdatePerson } from "@/features/people/hooks";
import { isApiError } from "@/lib/api/client";
import { formatDateTime } from "@/lib/utils";

function PersonActiveToggle({ personId, active }: { personId: string; active: boolean }) {
  const update = useUpdatePerson(personId);
  return (
    <Button
      type="button"
      size="sm"
      variant="outline"
      disabled={update.isPending}
      onClick={() => update.mutate({ active: !active })}
    >
      {active ? "Deactivate" : "Activate"}
    </Button>
  );
}

export function PeoplePage() {
  const persons = usePersons();
  const create = useCreatePerson();
  const [name, setName] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const display_name = name.trim();
    if (!display_name) return;
    create.mutate(
      { display_name },
      {
        onSuccess: () => setName(""),
      },
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">افراد</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          مدیریت افراد ثبت‌شده. بردارهای embedding در UI نمایش داده نمی‌شوند.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>ایجاد فرد</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={onSubmit}>
            <div className="flex-1 space-y-2">
              <Label htmlFor="display-name">نام نمایشی</Label>
              <Input
                id="display-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="مثلاً Ali"
                maxLength={100}
                required
              />
            </div>
            <Button type="submit" disabled={create.isPending || !name.trim()}>
              ایجاد
            </Button>
          </form>
          {create.isError ? (
            <ErrorState
              className="mt-4"
              message={isApiError(create.error) ? create.error.message : "Create failed"}
            />
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>فهرست افراد</CardTitle>
        </CardHeader>
        <CardContent>
          {persons.isLoading ? <LoadingState /> : null}
          {persons.isError ? (
            <ErrorState
              message={isApiError(persons.error) ? persons.error.message : "Failed to load people"}
              onRetry={() => void persons.refetch()}
            />
          ) : null}
          {persons.data && persons.data.persons.length === 0 ? (
            <EmptyState title="No people enrolled yet." />
          ) : null}
          {persons.data && persons.data.persons.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>نام</TableHead>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>ثبت‌نام‌ها</TableHead>
                  <TableHead>ایجاد</TableHead>
                  <TableHead>اقدامات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {persons.data.persons.map((person) => (
                  <TableRow key={person.id}>
                    <TableCell>
                      <Link
                        href={`/people/${person.id}`}
                        className="font-medium text-primary underline-offset-4 hover:underline"
                      >
                        {person.display_name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant={person.active ? "success" : "secondary"}>
                        {person.active ? "active" : "inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>{person.enrollment_count}</TableCell>
                    <TableCell>{formatDateTime(person.created_at)}</TableCell>
                    <TableCell>
                      <PersonActiveToggle personId={person.id} active={person.active} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
