"use client";

import { useQuery } from "@tanstack/react-query";

import { healthApi, systemApi } from "@/lib/api";
import { queryKeys } from "@/lib/query/client";

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: ({ signal }) => healthApi.get(signal),
    staleTime: 10_000,
    refetchInterval: 15_000,
  });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: ({ signal }) => systemApi.getStatus(signal),
    staleTime: 5_000,
    refetchInterval: 10_000,
  });
}
