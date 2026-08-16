import { QueryClient } from "@tanstack/react-query";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5_000,
        retry: (failureCount, error) => {
          if (
            error &&
            typeof error === "object" &&
            "status" in error &&
            typeof (error as { status: unknown }).status === "number"
          ) {
            const status = (error as { status: number }).status;
            if (status === 404 || status === 409 || status === 422) {
              return false;
            }
          }
          return failureCount < 2;
        },
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export const queryKeys = {
  health: ["health"] as const,
  systemStatus: ["system", "status"] as const,
  cameras: ["cameras"] as const,
  camera: (id: string) => ["cameras", id] as const,
  detections: (id: string) => ["cameras", id, "detections"] as const,
  persons: ["persons"] as const,
  person: (id: string) => ["persons", id] as const,
  enrollments: (personId: string) => ["persons", personId, "enrollments"] as const,
  events: (params: Record<string, unknown>) => ["events", params] as const,
  event: (id: string) => ["events", "detail", id] as const,
};
