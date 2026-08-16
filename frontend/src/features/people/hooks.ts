"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { enrollmentsApi, personsApi } from "@/lib/api";
import { queryKeys } from "@/lib/query/client";
import type { EnrollmentCreateRequest, PersonCreateRequest, PersonUpdateRequest } from "@/types/api";

export function usePersons() {
  return useQuery({
    queryKey: queryKeys.persons,
    queryFn: ({ signal }) => personsApi.list(signal),
    staleTime: 10_000,
  });
}

export function usePerson(personId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.person(personId ?? ""),
    queryFn: ({ signal }) => personsApi.get(personId!, signal),
    enabled: Boolean(personId),
    staleTime: 10_000,
  });
}

export function useCreatePerson() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: PersonCreateRequest) => personsApi.create(body),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.persons });
    },
  });
}

export function useUpdatePerson(personId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: PersonUpdateRequest) => personsApi.update(personId, body),
    onSuccess: (data) => {
      void client.invalidateQueries({ queryKey: queryKeys.persons });
      void client.invalidateQueries({ queryKey: queryKeys.person(data.id) });
    },
  });
}

export function useDeactivatePerson() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (personId: string) => personsApi.deactivate(personId),
    onSuccess: (data) => {
      void client.invalidateQueries({ queryKey: queryKeys.persons });
      void client.invalidateQueries({ queryKey: queryKeys.person(data.id) });
    },
  });
}

export function useEnrollments(personId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.enrollments(personId ?? ""),
    queryFn: ({ signal }) => enrollmentsApi.list(personId!, signal),
    enabled: Boolean(personId),
    staleTime: 10_000,
  });
}

export function useCreateEnrollment(personId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: EnrollmentCreateRequest) => enrollmentsApi.create(personId, body),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.enrollments(personId) });
      void client.invalidateQueries({ queryKey: queryKeys.person(personId) });
      void client.invalidateQueries({ queryKey: queryKeys.persons });
    },
  });
}

export function useDeleteEnrollment(personId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (enrollmentId: string) => enrollmentsApi.remove(personId, enrollmentId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.enrollments(personId) });
      void client.invalidateQueries({ queryKey: queryKeys.person(personId) });
      void client.invalidateQueries({ queryKey: queryKeys.persons });
    },
  });
}

export function useEnrollmentSession(personId: string, sessionId: string | null) {
  return useQuery({
    queryKey: queryKeys.enrollmentSession(personId, sessionId ?? ""),
    queryFn: ({ signal }) => enrollmentsApi.getSession(personId, sessionId!, signal),
    enabled: Boolean(sessionId),
    staleTime: 0,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      if (
        state === "completed" ||
        state === "cancelled" ||
        state === "failed"
      ) {
        return false;
      }
      return 750;
    },
  });
}

export function useStartEnrollmentSession(personId: string) {
  return useMutation({
    mutationFn: (cameraId?: string) =>
      enrollmentsApi.startSession(personId, cameraId ? { camera_id: cameraId } : {}),
  });
}

export function useCaptureEnrollmentSession(personId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => enrollmentsApi.captureSession(personId, sessionId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.enrollments(personId) });
      void client.invalidateQueries({ queryKey: queryKeys.person(personId) });
      void client.invalidateQueries({ queryKey: queryKeys.persons });
    },
  });
}

export function useCancelEnrollmentSession(personId: string) {
  return useMutation({
    mutationFn: (sessionId: string) => enrollmentsApi.cancelSession(personId, sessionId),
  });
}
