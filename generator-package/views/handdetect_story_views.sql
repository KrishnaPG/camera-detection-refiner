-- HandDetect Generator Package C-view projections.
-- Berg10 queries mounted external table files through a package-owned semantic
-- pass-through view; HandDetect owns run-scoped visual artifact creation and
-- never pushes rows through ingestion.

-- berg10:view id=handdetect_story_rows_v1
-- layer=semantic kind=table materialization=pass_through
-- output=C.handdetect.story.L2.as_is schema=schemas/handdetect-story-row.schema.json
-- query.cursor=sort_key
-- query.partition=run_id
-- query.filter=run_suite_id,run_id,event_type,status,reason,track_id
-- query.order=sort_key
create view handdetect_story_rows_v1 as
select * from handdetect_story_rows;

-- berg10:view id=handdetect_story_runs_v1
-- layer=presentation kind=detail materialization=pass_through
-- output=C.handdetect.story.L2.as_is schema=schemas/handdetect-story-row.schema.json
-- query.cursor=sort_key
-- query.partition=run_id
-- query.filter=run_suite_id,run_id,status
-- query.order=sort_key
create view handdetect_story_runs_v1 as
select
  row_id,
  run_suite_id,
  run_id,
  clip_id,
  event_type,
  status,
  label,
  artifact_path,
  created_at,
  sort_key,
  payload_json,
  package_id,
  decision,
  stage,
  reason,
  frame,
  track_id,
  confidence,
  url
from handdetect_story_rows_v1
where package_id = 'handdetect_quality_adapter'
  and event_type = 'story_ready';

-- berg10:view id=handdetect_story_clips_v1
-- layer=presentation kind=table materialization=pass_through
-- output=C.handdetect.story.L2.as_is schema=schemas/handdetect-story-row.schema.json
-- query.cursor=sort_key
-- query.partition=run_id
-- query.filter=run_suite_id,run_id,clip_id
-- query.order=sort_key
create view handdetect_story_clips_v1 as
select * from handdetect_story_rows_v1
where package_id = 'handdetect_quality_adapter'
  and event_type = 'clip_summary';

-- berg10:view id=handdetect_story_rejections_v1
-- layer=presentation kind=table materialization=pass_through
-- output=C.handdetect.story.L2.as_is schema=schemas/handdetect-story-row.schema.json
-- query.cursor=sort_key
-- query.partition=run_id
-- query.filter=run_suite_id,run_id,event_type,status,reason
-- query.order=sort_key
create view handdetect_story_rejections_v1 as
select * from handdetect_story_rows_v1
where package_id = 'handdetect_quality_adapter'
  and event_type = 'adapter_decision'
  and status != 'kept';

-- berg10:view id=handdetect_story_viewer_v1
-- layer=presentation kind=detail materialization=pass_through
-- output=C.handdetect.story.L2.as_is schema=schemas/handdetect-story-row.schema.json
-- query.cursor=sort_key
-- query.partition=run_id
-- query.filter=run_suite_id,run_id,clip_id
-- query.order=sort_key
create view handdetect_story_viewer_v1 as
select * from handdetect_story_rows_v1
where package_id = 'handdetect_quality_adapter'
  and event_type in ('story_ready', 'clip_summary');

-- berg10:view id=handdetect_story_events_v1
-- layer=presentation kind=table materialization=pass_through
-- output=C.handdetect.story.L2.as_is schema=schemas/handdetect-story-row.schema.json
-- query.cursor=sort_key
-- query.partition=run_id
-- query.filter=run_suite_id,run_id,event_type,status,reason,track_id
-- query.order=sort_key
create view handdetect_story_events_v1 as
select * from handdetect_story_rows_v1
where package_id = 'handdetect_quality_adapter';

-- berg10:view id=handdetect_story_tracks_v1
-- layer=presentation kind=table materialization=pass_through
-- output=C.handdetect.story.L2.as_is schema=schemas/handdetect-story-row.schema.json
-- query.cursor=sort_key
-- query.partition=run_id
-- query.filter=run_suite_id,run_id,clip_id,track_id
-- query.order=sort_key
create view handdetect_story_tracks_v1 as
select * from handdetect_story_rows_v1
where package_id = 'handdetect_quality_adapter'
  and event_type = 'mot_track_summary';

-- berg10:view id=handdetect_story_timeline_v1
-- layer=presentation kind=timeline materialization=pass_through
-- output=C.handdetect.story.L2.as_is schema=schemas/handdetect-story-row.schema.json
-- query.cursor=sort_key
-- query.partition=run_id
-- query.filter=run_suite_id,run_id,clip_id,event_type,frame,track_id,reason
-- query.order=sort_key
create view handdetect_story_timeline_v1 as
select * from handdetect_story_rows_v1
where package_id = 'handdetect_quality_adapter'
  and event_type in ('adapter_decision', 'mot_track_summary', 'clip_summary');

-- berg10:view id=handdetect_story_platforms_v1
-- layer=presentation kind=artifact_list materialization=pass_through
-- output=C.handdetect.story.L2.as_is schema=schemas/handdetect-story-row.schema.json
-- query.cursor=sort_key
-- query.partition=run_id
-- query.filter=run_suite_id,run_id,artifact_path,url
-- query.order=sort_key
create view handdetect_story_platforms_v1 as
select * from handdetect_story_rows_v1
where package_id = 'handdetect_quality_adapter'
  and event_type = 'platform_link';

-- berg10:view id=handdetect_story_diagnostics_v1
-- layer=presentation kind=detail materialization=pass_through
-- output=C.handdetect.story.L2.as_is schema=schemas/handdetect-story-row.schema.json
-- query.cursor=sort_key
-- query.partition=run_id
-- query.filter=run_suite_id,run_id,status
-- query.order=sort_key
create view handdetect_story_diagnostics_v1 as
select * from handdetect_story_rows_v1
where package_id = 'handdetect_quality_adapter';
