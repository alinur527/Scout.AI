# ScoutAI API v1

Base URL: `VITE_API_BASE_URL`; default local API is `http://localhost:8000`. Interactive OpenAPI: `/docs`. JSON uses snake_case. Dates are UTC. Auth uses `Authorization: Bearer <access_token>`. No legacy duplicate endpoints remain except GET job and its explicit status view, both with the same representation.

| Method | Path | Access | Request / response |
|---|---|---|---|
| GET | `/health` | public | status, demo_mode, worker_online, upload/duration limits |
| POST | `/auth/register` | public | username (3–40 ASCII letters/digits/underscore), password (8–128), role player/scout; 201 public user |
| POST | `/auth/login` | public | username/password; access_token, token_type, user |
| GET | `/profile/me` | any authenticated | `{user, profile}`; scouts have null profile |
| PUT | `/profile/me` | player | full_name, position, optional age, team, bio; full profile replacement |
| GET | `/analyses` | player | newest 100 owned job summaries |
| POST | `/analyses` | player | multipart `video`; 202 persisted queued job |
| GET | `/analyses/{id}` | owner | job summary |
| GET | `/analyses/{id}/status` | owner | same job summary, polling every 1.2 s in UI |
| GET | `/analyses/{id}/players` | owner | `{players:[{id,thumbnail,label,observations}],preview,video}` |
| PATCH | `/analyses/{id}/player` | owner | `{player_id: integer}` while awaiting_selection |
| POST | `/analyses/{id}/run` | owner | `{calibration:null}` or calibration below; 202 queued reporting |
| GET | `/analyses/{id}/result` | owner | selected-player report after completion |
| GET | `/players?q=&offset=0` | scout/admin | up to 50 real player records, profiles, latest completed report |
| GET | `/players/{user_id}` | scout/admin | profile and last 10 completed reports |

Public registration of admin returns 403. Username normalization is lowercase. Player positions: Goalkeeper, Defender, Midfielder, Forward. Raw uploads, storage paths, passwords and JWT secrets are never returned. Scouts receive completed reports through player endpoints, not access to another user's raw job/gallery endpoints. All registered player profiles are discoverable by registered scouts; no private-profile toggle exists yet.

## Job contract and stages

Job fields: id, status, stage, progress (0–100), original_filename, selected_player_id, demo, created_at, started_at, completed_at, error, video metadata.

```
queued / detection / 0
  → processing / detection / 5..75
  → processing / awaiting_selection / 80
  → PATCH player, POST run
  → queued / reporting / 80
  → processing / reporting / 90
  → completed / done / 100
```

Any processing failure becomes `failed / done` with a persisted error. `awaiting_selection` intentionally remains processing until the user selects and runs; it is not a stalled inference. Refresh and browser navigation do not lose progress. The mode is captured on job creation; changing server mode never silently changes an existing job. An API and worker must share the same database and upload directory.

## Calibration

```
{"calibration":{"points":[[10,10],[310,10],[310,190],[10,190]],"field_length":40,"field_width":20,"stationary_camera":true}}
```

Example points are only an illustration. Use actual video pixel coordinates. Four points must trace the boundary of a known rectangular field region in this order: origin, along length, opposite corner, along width. They map to (0,0), (length,0), (length,width), (0,width) metres. Camera must remain static. `stationary_camera` defaults to false; physical estimates additionally require no detected camera motion and reliable decoder timestamps. Moving/unknown cameras produce a completed image-space report with null physical metrics even when valid corners were supplied. The UI supports clicking the first frame and a JSON keyboard alternative. Never reuse arbitrary example coordinates for measurements.

## Result contract

Real reports also provide `detector_profile` (`panoramic_person`, `explicit_person`, `configured_base`, or `unknown`) and `ground_position_method` (`bbox_bottom_center`, `ankle_mean_with_bbox_fallback`, or `unknown`). Person-only detection uses approximate bbox positions and adds a warning that precise feet are not measured. These fields do not authorize physical metrics or express accuracy.

Server configuration `CV_DETECTOR_POLICY=auto` chooses `PERSON_MODEL_WEIGHTS` for videos at least1920px wide with aspect ratio at least3; all other shapes retain `MODEL_WEIGHTS`. Explicit `pose` and `person` policies are available. Missing local weights produce an actionable error; the server never downloads them. See [SMALL_PLAYER_EXPERIMENTS.md](SMALL_PLAYER_EXPERIMENTS.md) for the scope and regressions behind this choice.

`analysis_id`, `player_id`, `demo`, `calibrated`, `calibration_provided`, `coordinate_space` (field/image), `metrics` (`total_distance_m`, `top_speed_kmh`, `sprint_count`), normalized `movement` points (max1000, retained for older clients), `movement_segments` (render these separate polylines; endpoints preserved), 12×20 `heatmap`, observations, duration_seconds, frames_processed, device, rejected_segments, warnings, optional annotated_preview/radar. Added `camera_motion`, `timestamp_basis`, `physical_metrics_status` (demo/estimated/unavailable), `physical_accuracy=not_validated`, and `tracking_quality`.

`calibrated` now means physical projection was actually permitted, while `calibration_provided` records input corners. `tracking_quality.observed_frame_coverage` is selected-ID detected frames / decoded frames (null for demo/older missing records), and `trajectory_segments` counts continuous retained segments. The formula is also included in `definition`; neither is an accuracy score. `timestamp_basis` is decoder_pts, nominal_fps_fallback or synthetic. Existing clients omitting stationary confirmation retain image-space reports, rather than being silently authorized for physical measurement.

Real uncalibrated results have **null** distance/speed/sprints; movement is normalized image space. Calibrated results are estimates from one track, not verified real-world accuracy. Demo reports contain deterministic synthetic data and explicit warnings. Goals, assists, ball possession and ranking are not implemented.

Errors: 401 unauthenticated/expired/invalid JWT; 403 role violation; 404 missing or other owner's job; 409 duplicate username or invalid job stage; 413 body/file too large; 415 unsupported extension/MIME; 422 invalid form, undecodable video or bad calibration. Internal CV exceptions are logged by analysis ID and become a generic public failure; configuration/input errors are actionable.
