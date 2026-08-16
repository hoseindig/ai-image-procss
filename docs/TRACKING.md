# Face tracking (Phase 4)

Tracking exists so the same visible face keeps a stable **Track ID** across frames. Detection alone would treat every YuNet result as a new object.

Track IDs are **not** person identity. Recognition / SFace / enrollment are later phases.

## Algorithm

Lightweight greedy association on original-frame boxes:

1. Compute IoU and centroid distance between each active track and each new detection.
2. A pair is valid if `IoU >= FACE_TRACKING_IOU_THRESHOLD` **or** centroid distance `<= FACE_TRACKING_MAX_CENTROID_DISTANCE`.
3. Prefer IoU matches over distance-only matches, then higher IoU, then smaller distance, then lower `track_id`.
4. Assign greedily (one detection per track).
5. Unmatched detections create a new monotonic integer ID (`1, 2, 3, …`) until `FACE_TRACKING_MAX_TRACKS`.
6. Unmatched tracks increment `missed_frames`. Confirmed tracks become `lost`. After more than `FACE_TRACKING_MAX_MISSED_FRAMES` misses, the track is removed.

IDs are never reused in the same tracker instance.

This is **not** DeepSORT / ByteTrack. There is no appearance embedding.

## Lifecycle

```text
detection → tentative → confirmed → lost → removed
```

Default: two hits (`FACE_TRACKING_MIN_CONFIRMED_FRAMES=2`) promote tentative to confirmed. A short gap (within `max_missed_frames`) keeps the same ID.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `FACE_TRACKING_ENABLED` | `true` | Attach a tracker to the detection worker |
| `FACE_TRACKING_IOU_THRESHOLD` | `0.3` | Minimum IoU for an IoU match |
| `FACE_TRACKING_MAX_CENTROID_DISTANCE` | `100` | Pixel fallback when IoU is low (fast motion) |
| `FACE_TRACKING_MAX_MISSED_FRAMES` | `5` | Track survives this many consecutive misses |
| `FACE_TRACKING_MIN_CONFIRMED_FRAMES` | `2` | Hits required before `confirmed` |
| `FACE_TRACKING_MAX_TRACKS` | `20` | Cap on simultaneous tracks |

These are engineering defaults, not universal optima.

## Known limitations

- No appearance model: two people who cross with overlapping boxes can swap IDs.
- A jump larger than the centroid limit with no IoU overlap starts a new track.
- Lost tracks still occupy a `max_tracks` slot until removed.
- Tracker state is per camera start (a new worker gets a fresh ID sequence).
