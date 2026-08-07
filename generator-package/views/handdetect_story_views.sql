-- HandDetect Generator Package C-view projections.
-- The durable source of truth remains run artifacts and DVC-backed lineage.

CREATE OR REPLACE VIEW handdetect_story_runs_v1 AS
SELECT
  run_suite_id,
  run_id,
  max(created_at) AS last_event_at,
  max(status) AS status,
  count(*) AS event_count
FROM raw_handdetect_run_events
GROUP BY run_suite_id, run_id;

CREATE OR REPLACE VIEW handdetect_story_clips_v1 AS
SELECT
  run_suite_id,
  run_id,
  clip_id,
  max(created_at) AS last_clip_event_at,
  count(*) AS clip_event_count
FROM raw_handdetect_run_events
WHERE clip_id IS NOT NULL
GROUP BY run_suite_id, run_id, clip_id;

CREATE OR REPLACE VIEW handdetect_story_platforms_v1 AS
SELECT
  run_suite_id,
  run_id,
  artifact_path,
  message,
  created_at
FROM raw_handdetect_run_events
WHERE event_type = 'artifact_ready';
