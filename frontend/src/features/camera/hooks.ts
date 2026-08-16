"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { camerasApi } from "@/lib/api";
import { queryKeys } from "@/lib/query/client";

export function useCameras() {
  return useQuery({
    queryKey: queryKeys.cameras,
    queryFn: ({ signal }) => camerasApi.list(signal),
    staleTime: 5_000,
    refetchInterval: 5_000,
  });
}

export function useCamera(cameraId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.camera(cameraId ?? ""),
    queryFn: ({ signal }) => camerasApi.get(cameraId!, signal),
    enabled: Boolean(cameraId),
    staleTime: 2_000,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      if (state === "running" || state === "opening") {
        return 2_000;
      }
      return 5_000;
    },
  });
}

export function useDetections(cameraId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.detections(cameraId ?? ""),
    queryFn: ({ signal }) => camerasApi.detections(cameraId!, signal),
    enabled: Boolean(cameraId) && enabled,
    staleTime: 500,
    refetchInterval: enabled ? 1_000 : false,
  });
}

export function useStartCamera() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (cameraId: string) => camerasApi.start(cameraId),
    onSuccess: (data) => {
      void client.invalidateQueries({ queryKey: queryKeys.cameras });
      void client.invalidateQueries({ queryKey: queryKeys.camera(data.id) });
      void client.invalidateQueries({ queryKey: queryKeys.systemStatus });
    },
  });
}

export function useStopCamera() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (cameraId: string) => camerasApi.stop(cameraId),
    onSuccess: (data) => {
      void client.invalidateQueries({ queryKey: queryKeys.cameras });
      void client.invalidateQueries({ queryKey: queryKeys.camera(data.id) });
      void client.invalidateQueries({ queryKey: queryKeys.detections(data.id) });
      void client.invalidateQueries({ queryKey: queryKeys.systemStatus });
    },
  });
}
