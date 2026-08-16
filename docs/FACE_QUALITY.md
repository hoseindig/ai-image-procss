# Face quality & alignment (Phase 5)

Phase 5 decides whether a tracked face is suitable for a future embedding model and produces a standardized aligned crop. It does **not** run SFace, store embeddings, or assign person identity.

**Track ID ≠ Person ID.** Quality and alignment operate on `FaceTrack` only.

## Pipeline

```text
Camera → YuNet → FaceTracker → FaceQualityAssessor → FaceAligner → AlignedFace
```

Each stage is independent. Application code depends on `FaceQualityAssessor` / `FaceAligner` protocols and typed models, not on YuNet.

## Quality metrics (heuristics)

These are engineering gates, **not** scientifically validated biometric quality scores and **not** probabilities.

| Check | Definition | Rejection |
| --- | --- | --- |
| Face size | Bounding-box width/height vs minima | `face_too_small` |
| Crop | Face box intersects the frame with a non-empty region | `invalid_crop` |
| Landmarks | Five points finite, near frame, sensible eye/mouth/nose geometry | `invalid_landmarks` |
| Sharpness | Variance of Laplacian on the grayscale face crop | `too_blurry` |
| Brightness | Mean grayscale intensity of the face crop | `too_dark` / `too_bright` |

Result type: `FaceQuality` with `accepted: bool`, structured `reasons[]`, and metric fields. There is no combined “quality probability”.

## Alignment

- Method: similarity transform from five landmarks (`cv2.estimateAffinePartial2D`, LMEDS) + `cv2.warpAffine`
- Interpolation: bilinear (`INTER_LINEAR`)
- Border: constant black
- Source order: `left_eye`, `right_eye`, `nose`, `left_mouth`, `right_mouth` (`FaceLandmarks` fields)
- Target: ArcFace 112×112 reference points, scaled if output size ≠ 112
- Default output: **112×112** BGR (matches planned SFace input; dimensions remain configurable)
- Geometry tests require transformed landmarks within **2.0 px** of targets (`ALIGNMENT_LANDMARK_TOLERANCE_PX`)

`AlignedFace` holds a NumPy HxWx3 uint8 image, size, `source_track_id`, and the 2×3 transform. Images stay in the vision layer (size-1 aligned slot); the REST API exposes quality metadata and `aligned` / `aligned_count` only.

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `FACE_QUALITY_ENABLED` | `true` | |
| `FACE_QUALITY_MIN_FACE_WIDTH` | `80` | pixels |
| `FACE_QUALITY_MIN_FACE_HEIGHT` | `80` | pixels |
| `FACE_QUALITY_MIN_SHARPNESS` | `60` | Laplacian variance; tunable |
| `FACE_QUALITY_MIN_BRIGHTNESS` | `40` | mean gray 0–255 |
| `FACE_QUALITY_MAX_BRIGHTNESS` | `220` | mean gray 0–255 |
| `FACE_ALIGNMENT_ENABLED` | `true` | |
| `FACE_ALIGNMENT_WIDTH` | `112` | |
| `FACE_ALIGNMENT_HEIGHT` | `112` | |

When quality is enabled, only **accepted** tracks are aligned. When quality is disabled and alignment is enabled, current matched tracks are aligned without a gate.

## Known limitations

- Thresholds are scene-dependent; retune for your camera lighting.
- Sharpness is a crop-level Laplacian heuristic; motion blur and compression can both lower it.
- Landmark geometry checks are simple; extreme pose can reject usable faces or accept odd ones.
- Alignment assumes roughly frontal five-point geometry; large yaw/pitch will warp poorly.
- No appearance embedding or identity in this phase.
