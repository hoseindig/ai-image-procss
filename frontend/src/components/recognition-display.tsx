import { formatSimilarity } from "@/lib/utils";
import type { Event, RecognitionResult } from "@/types/api";

export function SimilarityLabel({ value }: { value: number | null | undefined }) {
  const formatted = formatSimilarity(value);
  if (!formatted) {
    return <span className="text-muted-foreground">—</span>;
  }
  return <span>Similarity: {formatted}</span>;
}

export function RecognitionSummary({ recognition }: { recognition: RecognitionResult | null }) {
  if (!recognition) {
    return <p className="text-sm text-muted-foreground">Recognition: no data</p>;
  }
  if (recognition.status === "matched") {
    return (
      <div className="space-y-1">
        <p className="font-medium">{recognition.person_display_name ?? "Matched"}</p>
        <p className="text-sm text-muted-foreground">
          <SimilarityLabel value={recognition.similarity} />
        </p>
      </div>
    );
  }
  if (recognition.status === "unknown") {
    return (
      <div className="space-y-1">
        <p className="font-medium">Unknown face</p>
        <p className="text-sm text-muted-foreground">
          <SimilarityLabel value={recognition.similarity} />
        </p>
      </div>
    );
  }
  return (
    <div className="space-y-1">
      <p className="font-medium">Recognition: {recognition.status}</p>
      {recognition.reason ? (
        <p className="text-sm text-muted-foreground">Reason: {recognition.reason}</p>
      ) : null}
    </div>
  );
}

export function EventSummary({
  event,
  personName,
}: {
  event: Event;
  personName?: string | null;
}) {
  if (event.event_type === "recognized") {
    return (
      <div className="space-y-1">
        <p className="font-medium">Recognized</p>
        <p>{personName ?? event.person_id ?? "—"}</p>
        <p className="text-sm text-muted-foreground">
          <SimilarityLabel value={event.similarity} />
        </p>
      </div>
    );
  }
  if (event.event_type === "unknown_face") {
    return (
      <div className="space-y-1">
        <p className="font-medium">Unknown face</p>
        <p className="text-sm text-muted-foreground">
          <SimilarityLabel value={event.similarity} />
        </p>
      </div>
    );
  }
  return <p className="font-medium">{event.event_type}</p>;
}
