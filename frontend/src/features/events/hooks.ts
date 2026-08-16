"use client";

import { useQuery } from "@tanstack/react-query";

import { eventsApi } from "@/lib/api";
import { queryKeys } from "@/lib/query/client";
import type { EventListParams } from "@/types/api";

export function useEvents(params: EventListParams) {
  return useQuery({
    queryKey: queryKeys.events(params as Record<string, unknown>),
    queryFn: ({ signal }) => eventsApi.list(params, signal),
    staleTime: 5_000,
    placeholderData: (previous) => previous,
  });
}
