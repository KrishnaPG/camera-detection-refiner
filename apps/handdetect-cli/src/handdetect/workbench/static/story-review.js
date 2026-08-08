const QUALITY_TRACK_MODES = {
  RAW_ONLY: "rawOnly",
  KEPT_ONLY: "keptOnly",
  REJECTED_ONLY: "rejectedOnly",
  ALL: "all",
};

const REASON_CHANNELS = {
  duplicate_overlap: {
    label: "Duplicate Detections",
    color: "#ffd166",
    shape: "diamond",
    reasonPriority: 5,
  },
  implausible_size: {
    label: "Implausible Size",
    color: "#ff7ab6",
    shape: "square",
    reasonPriority: 4,
  },
  implausible_shape: {
    label: "Implausible Shape",
    color: "#c77dff",
    shape: "triangle",
    reasonPriority: 6,
  },
  implausible_displacement: {
    label: "Implausible Motion",
    color: "#8fd3ff",
    shape: "triangle-down",
    reasonPriority: 7,
  },
  unsupported_track: {
    label: "Unsupported Detection",
    color: "#9ad8ff",
    shape: "pentagon",
    reasonPriority: 3,
  },
  hand_exit_side_border: {
    label: "Hand Exit Side Border",
    color: "#f97316",
    shape: "triangle-down",
    reasonPriority: 11,
  },
  brief_occlusion_candidate: {
    label: "Brief Occlusion Candidate",
    color: "#8ec6ff",
    shape: "circle",
    reasonPriority: 11,
  },
  possible_bystander_hand: {
    label: "Possible Bystander Hand",
    color: "#8d98a5",
    shape: "circle",
    reasonPriority: 12,
  },
  false_negative_interpolation: {
    label: "False-Negative Interpolation",
    color: "#a78bfa",
    shape: "square",
    reasonPriority: 12,
  },
  implausible_detection: {
    label: "Implausible Detection",
    color: "#ff7a45",
    shape: "triangle",
    reasonPriority: 10,
  },
  unsupported_detection: {
    label: "Unsupported Detection",
    color: "#9ad8ff",
    shape: "pentagon",
    reasonPriority: 3,
  },
  short_track: {
    label: "Short Track",
    color: "#7aa2ff",
    shape: "pentagon",
    reasonPriority: 3,
  },
  track_length_gate: {
    label: "Unsupported Detection",
    color: "#9ad8ff",
    shape: "pentagon",
    reasonPriority: 3,
  },
  motion_gate: {
    label: "Implausible Motion",
    color: "#8fd3ff",
    shape: "triangle-down",
    reasonPriority: 7,
  },
  duplicate_merge: {
    label: "Duplicate Merge",
    color: "#ffd166",
    shape: "diamond",
    reasonPriority: 5,
  },
  static_detection: {
    label: "Static Detection",
    color: "#92ffb0",
    shape: "circle",
    reasonPriority: 2,
  },
  max_two_selection: {
    label: "Max-Two Selection",
    color: "#bf8cff",
    shape: "octagon",
    reasonPriority: 8,
  },
  max_two_selector: {
    label: "Max-Two Selection",
    color: "#bf8cff",
    shape: "octagon",
    reasonPriority: 8,
  },
  shape_gate: {
    label: "Implausible Shape",
    color: "#c77dff",
    shape: "triangle",
    reasonPriority: 6,
  },
  size_gate: {
    label: "Implausible Size",
    color: "#ff7ab6",
    shape: "square",
    reasonPriority: 4,
  },
  displacement_gate: {
    label: "Implausible Motion",
    color: "#8fd3ff",
    shape: "triangle-down",
    reasonPriority: 7,
  },
  track_support_gate: {
    label: "Unsupported Detection",
    color: "#9ad8ff",
    shape: "pentagon",
    reasonPriority: 3,
  },
  kept: {
    label: "Kept",
    color: "#30d158",
    shape: "cross",
    reasonPriority: 0,
  },
  merged: {
    label: "Merged",
    color: "#ffd60a",
    shape: "diamond",
    reasonPriority: 1,
  },
  rejected: {
    label: "Rejected",
    color: "#ff453a",
    shape: "square",
    reasonPriority: 9,
  },
  unknown: {
    label: "Unknown",
    color: "#9ca3af",
    shape: "circle",
    reasonPriority: 10,
  },
};

const DECISION_COLOR = {
  kept: "#30d158",
  merged: "#ffd60a",
  rejected: "#ff453a",
};

const TRACK_COLORS = [
  "#30d158",
  "#ff453a",
  "#2f7dff",
  "#ffd166",
  "#bf8cff",
  "#2ee6d6",
  "#f97316",
  "#ff77b7",
  "#5eead4",
  "#7c3aed",
  "#facc15",
  "#4ade80",
  "#38bdf8",
  "#f472b6",
  "#fb7185",
  "#a78bfa",
  "#86efac",
  "#60a5fa",
  "#fca5a5",
];

const MARKER_LANE_COUNT = 6;
const MARKER_GAP_PCT = 2.4;
const MARKER_HOVER_RADIUS = 15;
const MAX_TRACK_ROWS = 160;
const MAX_LANE_EVENT_MARKERS = 72;
const MAX_OVERVIEW_MARKERS = 180;
const DENSITY_BIN_TARGET_PX = 9;
const SPAN_MERGE_GAP_FRAMES = 18;
const SELECTION_DECORATOR_SIZE = 7;
const MARKER_BASE_SIZE = 4;
const MIN_EVENT_MARKER_SIZE = 4.2;

const REASON_ALIAS = {
  duplicate_merge: "duplicate_overlap",
  duplicate_boxes_on_one_hand: "duplicate_overlap",
  shape_gate: "implausible_shape",
  size_gate: "implausible_size",
  displacement_gate: "implausible_displacement",
  track_support_gate: "unsupported_track",
  track_length_gate: "unsupported_track",
  short_track: "unsupported_track",
  unsupported_detection: "unsupported_track",
  unsupported_track: "unsupported_track",
  motion_gate: "implausible_displacement",
  max_two_selector: "max_two_selection",
  over_max_hands: "max_two_selection",
  implausible_detection: "implausible_detection",
  hand_exit_side_border: "hand_exit_side_border",
  brief_occlusion_candidate: "brief_occlusion_candidate",
  possible_bystander_hand: "possible_bystander_hand",
  false_negative_interpolation: "false_negative_interpolation",
};

const TRACK_EVENT_LIMIT = 120;

const root = document.querySelector(".shell");
const story = JSON.parse(root.dataset.story);
const suiteId = root.dataset.suiteId;
const runId = root.dataset.runId;

const rawVideo = document.getElementById("rawVideo");
const adapterVideo = document.getElementById("adapterVideo");
const rawOverlaySvg = document.getElementById("rawOverlaySvg");
const adapterOverlaySvg = document.getElementById("adapterOverlaySvg");

const timeSurface = document.querySelector(".timeSurface");
const timeContent = document.getElementById("timeContent");
const playhead = document.getElementById("playhead");
const playheadHandle = playhead.querySelector(".playheadHandle");
const zoomSlider = document.getElementById("zoomSlider");
const zoomText = document.getElementById("zoomText");
const zoomBadge = document.getElementById("zoomBadge");
const thumbStrip = document.getElementById("thumbStrip");
const ruler = document.getElementById("ruler");
const rulerLabel = document.getElementById("rulerLabel");
const markerCanvas = document.getElementById("markerCanvas");
const spanCanvas = document.getElementById("spanCanvas");
const markerContext = markerCanvas.getContext("2d");
const spanContext = spanCanvas.getContext("2d");

const trackContainer = document.getElementById("trackList");
const laneContainer = document.getElementById("lanes");
const decisionCard = document.getElementById("decisionCard");
const chapterList = document.getElementById("chapterList");

const timelineLegend = document.getElementById("timelineLegend");
const timeLabel = document.getElementById("timeLabel");
const cursorFrame = document.getElementById("cursorFrame");
const cursorDecision = document.getElementById("cursorDecision");
const cursorReason = document.getElementById("cursorReason");
const trackSummary = document.getElementById("trackSummary");

const selectedTrackLabel = document.getElementById("selectedTrackLabel");
const selectedTrackChanges = document.getElementById("selectedTrackChanges");
const selectedTrackKept = document.getElementById("selectedTrackKept");
const selectedTrackRejected = document.getElementById("selectedTrackRejected");
const selectedTrackSpan = document.getElementById("selectedTrackSpan");
const trackEventList = document.getElementById("trackEventList");
const timelineSummaryText = document.getElementById("timelineSummaryText");
const demoStory = document.getElementById("demoStory");

const showOnlyActiveTrack = document.getElementById("showOnlyActiveTrack");
const showOnlyLowQuality = document.getElementById("showOnlyLowQuality");

const prevEventButton = document.getElementById("prevEvent");
const nextEventButton = document.getElementById("nextEvent");
const playPauseButton = document.getElementById("playPause");
const fitToTrackButton = document.getElementById("fitToTrackBtn");
const clearTrackButton = document.getElementById("clearTrackBtn");
const focusTrackButton = document.getElementById("focusTrackBtn");
const prevTrackEventButton = document.getElementById("prevTrackEvent");
const nextTrackEventButton = document.getElementById("nextTrackEvent");
const showRawButton = document.getElementById("showRaw");
const showAdapterKeptOnlyButton = document.getElementById("showAdapterKeptOnly");
const showAdapterRejectedOnlyButton = document.getElementById("showAdapterRejectedOnly");

let activeClip = story.clips[0] || null;
let events = [];
let markerRows = [];
let activeTimeline = null;
let markerPositions = [];
let trackRows = [];
let trackById = new Map();
let boxesByFrame = new Map();
let detectionToBox = new Map();
let eventsByFrame = new Map();
let frameLevelEvents = [];
let eventIndex = 0;
let selectedTrackId = null;
let frameByTrackEvents = new Map();
let isScrubbing = false;
let scrubStartX = 0;
let scrubMoved = false;
let pendingSeekFrame = null;
let seekAnimationFrame = 0;
let syncLock = false;
let timelineHoverFrame = null;
let selectedMarkerIndex = null;
let adapterMode = QUALITY_TRACK_MODES.KEPT_ONLY;
let selectedTrackEventIndex = null;

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function toNumber(value, fallback = 0) {
  if (value === null || value === undefined) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toInt(value, fallback = 0) {
  if (value === null || value === undefined || value === "") return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) && Number.isInteger(parsed) ? parsed : Math.trunc(parsed);
}

function toNullableInt(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function toFloat(value, fallback = 0.0) {
  if (value === null || value === undefined) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function artifactUrl(path) {
  return `/artifacts/${suiteId}/${runId}/${path}`;
}

function frameToPercent(frame, frameCount) {
  if (!Number.isFinite(frameCount) || frameCount <= 1) return 0;
  return clamp((frame / (frameCount - 1)) * 100, 0, 100);
}

function normalizeAlias(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return "";
  if (normalized.includes(":")) {
    const short = normalized.split(":")[0];
    if (REASON_ALIAS[short]) return REASON_ALIAS[short];
  }
  return REASON_ALIAS[normalized] || normalized;
}

function stageToReason(stage) {
  if (!stage) return "kept";
  const normalized = normalizeAlias(stage);
  return normalized || "kept";
}

function normalizeReason(eventRow) {
  const explicit = normalizeAlias(eventRow?.reason);
  if (explicit) return explicit;
  return stageToReason(eventRow?.stage) || "kept";
}

function reasonSpec(reason) {
  return REASON_CHANNELS[reason] || REASON_CHANNELS.unknown;
}

function hexToRgba(hex, alpha) {
  const match = String(hex).trim().replace(/^#/, "");
  if (!/^[0-9a-fA-F]{6}$/.test(match)) {
    return `rgba(255, 255, 255, ${alpha})`;
  }
  const value = Number.parseInt(match, 16);
  const red = (value >> 16) & 255;
  const green = (value >> 8) & 255;
  const blue = value & 255;
  const safeAlpha = clamp(Number.isFinite(alpha) ? alpha : 1, 0, 1);
  return `rgba(${red}, ${green}, ${blue}, ${safeAlpha})`;
}

function confidenceToOpacity(value) {
  const score = toFloat(value, 0.5);
  return clamp(0.25 + score * 0.7, 0.22, 0.98);
}

function confidenceToMarkerSize(value) {
  const score = toFloat(value, 0.5);
  return clamp(MARKER_BASE_SIZE + score * 5.5, MIN_EVENT_MARKER_SIZE, 9.5);
}

function decisionColor(decision, reason) {
  if (decision === "kept") return DECISION_COLOR.kept;
  if (decision === "merged") return DECISION_COLOR.merged;
  if (decision === "rejected") return DECISION_COLOR.rejected;
  return reasonSpec(reason || "unknown").color;
}

function reasonColor(decision, reason) {
  if (decision === "kept") return DECISION_COLOR.kept;
  if (decision === "merged") return DECISION_COLOR.merged;
  if (decision === "rejected") return reasonSpec(reason || "unknown").color;
  return reasonSpec(reason || "unknown").color;
}

function decisionStroke(decision, reason) {
  if (decision === "rejected") return DECISION_COLOR.rejected;
  if (decision === "merged") return DECISION_COLOR.merged;
  if (decision === "kept") return DECISION_COLOR.kept;
  return reasonColor(decision, reason);
}

function reasonLabel(reason) {
  return reasonSpec(reason).label;
}

function trackColor(trackId) {
  if (!Number.isFinite(trackId) || trackId < 0) return "#9ca3af";
  return TRACK_COLORS[trackId % TRACK_COLORS.length];
}

function formatCount(value) {
  return new Intl.NumberFormat("en-US").format(toInt(value, 0));
}

function summarizeReasonCounts(rows) {
  const counts = new Map();
  for (const row of rows) {
    const reason = normalizeReason(row);
    counts.set(reason, (counts.get(reason) || 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || reasonSpec(a[0]).reasonPriority - reasonSpec(b[0]).reasonPriority)
    .map(([reason, count]) => ({ reason, count }));
}

function updateDemoStory() {
  if (!demoStory || !activeClip) return;
  const removed = toInt(activeClip.rejected_detection_count, events.length);
  const total = Math.max(toInt(activeClip.raw_detection_count, 0), 1);
  const removedPct = ((removed / total) * 100).toFixed(1);
  const trackedEvents = events.length - frameLevelEvents.length;
  const topReasons = summarizeReasonCounts(events)
    .slice(0, 3)
    .map(({ reason, count }) => `${reasonLabel(reason)} ${formatCount(count)}`)
    .join(" · ");
  demoStory.innerHTML = `
    <strong>Remove low-quality robotics data, one trajectory at a time</strong>
    <span>${formatCount(removed)} of ${formatCount(total)} raw detections cleaned (${removedPct}%). ${formatCount(trackedEvents)} track-linked edits, ${formatCount(frameLevelEvents.length)} frame-level gate edits.</span>
    <span>${topReasons || "No low-quality classes in this clip."}</span>
  `;
}

async function loadClip(clip) {
  if (!clip) return;
  activeClip = clip;
  rawVideo.src = artifactUrl(clip.raw_overlay_url);
  adapterVideo.src = artifactUrl(clip.adapter_overlay_url);
  thumbStrip.src = artifactUrl(clip.thumbnail_strip_url);
  rawVideo.addEventListener(
    "loadedmetadata",
    () => {
      updatePlayheadForFrame(Math.round(rawVideo.currentTime * Math.max(activeClip.fps, 1)));
    },
    { once: true },
  );

  const payloads = await Promise.all([
    fetch(artifactUrl(clip.events_path)).then((response) => response.json()),
    fetch(artifactUrl(clip.timeline_path)).then((response) => response.json()),
    fetch(artifactUrl(clip.tracks_path)).then((response) => response.json()),
    fetch(artifactUrl(clip.chapters_path)).then((response) => response.json()),
    fetch(artifactUrl(clip.boxes_path)).then((response) => response.json()),
  ]);

  applyClipPayloads(payloads);
}

function applyClipPayloads([eventPayload, timelinePayload, trackPayload, chapterPayload, boxPayload]) {
  const eventsPayload = Array.isArray(eventPayload?.events) ? eventPayload.events : [];
  const timelinePayloadValue = timelinePayload || {};
  const tracksPayload = Array.isArray(trackPayload?.tracks) ? trackPayload.tracks : [];
  const chapterPayloadValue = chapterPayload || {};
  const boxesPayload = boxPayload || {};

  boxesByFrame = new Map();
  detectionToBox = new Map();

  const videoWidth = toInt(boxesPayload.video_width, 1920);
  const videoHeight = toInt(boxesPayload.video_height, 1200);
  rawOverlaySvg.setAttribute("viewBox", `0 0 ${videoWidth} ${videoHeight}`);
  adapterOverlaySvg.setAttribute("viewBox", `0 0 ${videoWidth} ${videoHeight}`);

  (boxesPayload.frames || []).forEach((frameRow) => {
    const frame = toInt(frameRow.frame);
    const boxes = Array.isArray(frameRow.boxes) ? frameRow.boxes : [];
    const normalizedBoxes = boxes.map((box) => {
      const decision = String(box.decision || "kept");
      const normalized = {
        detection_id: String(box.detection_id ?? ""),
        frame,
        decision,
        stage: String(box.stage || ""),
        reason: normalizeReason(box),
        track_id: toNullableInt(box.track_id),
        x1: toFloat(box.x1),
        y1: toFloat(box.y1),
        x2: toFloat(box.x2),
        y2: toFloat(box.y2),
        score: toFloat(box.score, toFloat(box.confidence)),
        confidence: toFloat(box.confidence, toFloat(box.score)),
      };
      return normalized;
    });
    boxesByFrame.set(frame, normalizedBoxes);
    for (const box of normalizedBoxes) {
      if (box.detection_id) {
        detectionToBox.set(box.detection_id, box);
      }
    }
  });

  events = eventsPayload
    .map((eventRow, index) => {
      const detection = detectionToBox.get(String(eventRow.detection_id)) || {};
      const reason = normalizeReason({
        ...eventRow,
        reason: eventRow.reason,
        stage: eventRow.stage,
      });
      const trackId = toNullableInt(eventRow.track_id) ?? toNullableInt(detection.track_id);
      return {
        index,
        event_id: String(eventRow.event_id || `event-${index}`),
        detection_id: String(eventRow.detection_id || ""),
        frame: toInt(eventRow.frame),
        decision: String(eventRow.decision || "kept"),
        stage: String(eventRow.stage || ""),
        reason,
        track_id: trackId,
        confidence: toFloat(eventRow.confidence, toFloat(eventRow.score, toFloat(detection.confidence))),
        box: eventRow.box || detection || {},
        display_label: String(eventRow.display_label || reasonLabel(reason)),
      };
    })
    .filter((row) => row.decision !== "kept")
    .sort((a, b) => a.frame - b.frame || a.index - b.index);

  activeTimeline = timelinePayloadValue;
  activeTimeline.frame_count = toInt(activeTimeline.frame_count, activeClip.frame_count || 1);
  activeTimeline.fps = toFloat(activeTimeline.fps, activeClip.fps || 1);

  eventsByFrame = buildEventsByFrame(events);
  frameLevelEvents = events.filter((event) => !Number.isFinite(event.track_id));
  markerRows = (timelinePayloadValue.markers || [])
    .map((row, index) => {
      const reason = normalizeReason(row);
      const frame = toInt(row.frame);
      const frameEvents = eventsByFrame.get(frame) || [];
      const representative = frameEvents.length > 0 ? frameEvents[0] : null;
      return {
        index,
        frame,
        decision: String(row.decision || (representative?.decision || "kept")),
        stage: String(row.stage || ""),
        reason,
        track_id: representative?.track_id ?? toNullableInt(row.track_id),
        confidence: toFloat(
          representative?.confidence,
          toFloat(row.confidence, toFloat(row.score, toFloat(representative?.confidence, 0.5))),
        ),
        label: String(row.label || reasonLabel(reason)),
      };
    })
    .filter((row) => Number.isFinite(row.frame))
    .sort((a, b) => a.frame - b.frame || a.index - b.index);
  buildTrackRows(tracksPayload);
  updateDemoStory();
  renderChapters(chapterPayloadValue);
  renderTracks();
  renderTimeline();
  updateTrackSelectionUI();
  renderTrackStats();
  renderTrackButtonsForNavigation();
  setSelectedTrack(selectedTrackId, true);
  if (events.length > 0) {
    selectEvent(0, true);
  } else {
    decisionCard.textContent = "No adapter change events for this clip.";
  }
  setAdapterMode(QUALITY_TRACK_MODES.KEPT_ONLY);
  queueSeekToFrame(0, true);
  drawMarkerState();
  applyZoom();
}

function buildEventsByFrame(rows) {
  const byFrame = new Map();
  rows.forEach((row, rowIndex) => {
    if (!byFrame.has(row.frame)) byFrame.set(row.frame, []);
    byFrame.get(row.frame).push({ ...row, eventIndex: rowIndex });
  });
  byFrame.forEach((frameRows) => {
    frameRows.sort((a, b) => {
      const reasonPriority = reasonSpec(a.reason).reasonPriority - reasonSpec(b.reason).reasonPriority;
      if (reasonPriority !== 0) return reasonPriority;
      return a.index - b.index;
    });
  });
  return byFrame;
}

function buildTrackRows(trackRowsPayload) {
  const rowsByTrack = new Map();
  for (const row of trackRowsPayload) {
    const trackId = toInt(row.track_id, -1);
    if (trackId < 0) continue;
    rowsByTrack.set(trackId, {
      track_id: trackId,
      start_frame: toInt(row.start_frame),
      end_frame: toInt(row.end_frame),
      duration_frames: toInt(row.duration_frames),
      observation_count: toInt(row.observation_count),
      average_confidence: toFloat(row.average_confidence),
      color_id: toInt(row.color_id, trackId),
      kept_count: 0,
      rejected_count: 0,
      merged_count: 0,
      quality_count: 0,
      reasonCounts: {},
      spansByReason: [],
      raw_quality_reasons: [],
    });
  }

  for (const event of events) {
    if (!Number.isFinite(event.track_id)) {
      continue;
    }
    const row = rowsByTrack.get(event.track_id);
    if (!row) {
      rowsByTrack.set(event.track_id, {
        track_id: event.track_id,
        start_frame: event.frame,
        end_frame: event.frame,
        duration_frames: 1,
        observation_count: 0,
        average_confidence: 0,
        color_id: toInt(event.track_id),
        kept_count: 0,
        rejected_count: 0,
        merged_count: 0,
        quality_count: 0,
        reasonCounts: {},
        spansByReason: [],
      });
    }
    const target = rowsByTrack.get(event.track_id);
    if (!target) continue;
    target.start_frame = Math.min(target.start_frame, event.frame);
    target.end_frame = Math.max(target.end_frame, event.frame);
    target.duration_frames = target.end_frame - target.start_frame + 1;
    target._qualityEventCount = Math.max(toInt(target._qualityEventCount, 0) + 1, 1);
    target.average_confidence = toFloat(
      (target.average_confidence * (target._qualityEventCount - 1) + event.confidence) /
        target._qualityEventCount,
    );
    if (event.decision === "merged") target.merged_count += 1;
    else target.rejected_count += 1;
    const reason = normalizeReason(event);
    target.raw_quality_reasons.push({
      decision: event.decision,
      reason,
      frame: event.frame,
      confidence: toFloat(event.confidence),
      event_index: event.index,
      source: "event",
    });
    target.reasonCounts[reason] = (target.reasonCounts[reason] || 0) + 1;
    target.quality_count = target.rejected_count + target.merged_count;
  }

  trackRows = [];
  for (const row of rowsByTrack.values()) {
    row.spansByReason = buildSpanGroups(row);
    row.kept_count = Math.max(0, (row.observation_count || 0) - row.quality_count);
    delete row._qualityEventCount;
    trackRows.push(row);
  }

  frameByTrackEvents = buildTrackEventFrames(events);
  trackById = new Map(trackRows.map((row) => [row.track_id, row]));
  trackRows.sort((a, b) => {
    if (a.quality_count !== b.quality_count) return b.quality_count - a.quality_count;
    return a.track_id - b.track_id;
  });
}

function buildTrackEventFrames(eventRows) {
  const buckets = new Map();
  for (const event of eventRows) {
    const trackId = event.track_id;
    if (!Number.isFinite(trackId)) continue;
    if (!buckets.has(trackId)) buckets.set(trackId, []);
    buckets.get(trackId).push(event);
  }
  for (const rows of buckets.values()) {
    rows.sort((a, b) => a.frame - b.frame || a.index - b.index);
  }
  return buckets;
}

function buildSpanGroups(row) {
  const trackEvents = (events || []).filter((event) => event.track_id === row.track_id);
  const byReason = new Map();
  for (const event of trackEvents) {
    const reason = normalizeReason(event);
    if (!byReason.has(reason)) byReason.set(reason, []);
    byReason.get(reason).push({
      start: event.frame,
      end: event.frame + 1,
      kind: event.decision,
      confidence: event.confidence,
    });
  }
  const spans = [];
  byReason.forEach((pointRows, reason) => {
    pointRows.sort((a, b) => a.start - b.start);
    let activeSpan = null;
    for (const point of pointRows) {
      if (!activeSpan || point.start > activeSpan.end + SPAN_MERGE_GAP_FRAMES) {
        if (activeSpan) {
          spans.push({ ...activeSpan, reason });
        }
        activeSpan = { ...point };
        continue;
      }
      activeSpan.end = Math.max(activeSpan.end, point.end);
      if (point.kind !== activeSpan.kind) activeSpan.kind = "merged";
    }
    if (activeSpan) spans.push({ ...activeSpan, reason });
  });
  return spans;
}

function eventPriority(row) {
  const reason = normalizeReason(row);
  const confidence = toFloat(row.confidence, 0.5);
  const decisionBoost = row.decision === "merged" ? 0.8 : 0;
  return reasonSpec(reason).reasonPriority * 10 + confidence * 6 + decisionBoost;
}

function representativeEvents(rows, limit) {
  if (!Array.isArray(rows) || rows.length <= limit) return rows || [];

  const selected = new Map();
  const add = (row) => {
    if (row && Number.isFinite(row.index)) selected.set(row.index, row);
  };
  add(rows[0]);
  add(rows[rows.length - 1]);

  let previousReason = "";
  for (const row of rows) {
    const reason = normalizeReason(row);
    if (reason !== previousReason) {
      add(row);
      previousReason = reason;
    }
  }

  const byReason = new Map();
  for (const row of rows) {
    const reason = normalizeReason(row);
    if (!byReason.has(reason)) byReason.set(reason, []);
    byReason.get(reason).push(row);
  }
  for (const reasonRows of byReason.values()) {
    reasonRows
      .slice()
      .sort((a, b) => eventPriority(b) - eventPriority(a) || a.frame - b.frame)
      .slice(0, 10)
      .forEach(add);
  }

  const stride = Math.max(1, Math.floor(rows.length / Math.max(limit - selected.size, 1)));
  for (let index = 0; index < rows.length && selected.size < limit; index += stride) {
    add(rows[index]);
  }

  if (selected.size > limit) {
    return [...selected.values()]
      .sort((a, b) => eventPriority(b) - eventPriority(a) || a.frame - b.frame)
      .slice(0, limit)
      .sort((a, b) => a.frame - b.frame || a.index - b.index);
  }
  return [...selected.values()].sort((a, b) => a.frame - b.frame || a.index - b.index);
}

function representativeMarkers(rows, limit) {
  return representativeEvents(rows, limit);
}

function renderChapters(chapterPayload) {
  const chapters = chapterPayload?.chapters || [];
  if (!Array.isArray(chapters) || chapters.length === 0) {
    chapterList.innerHTML =
      '<div class="chapterPill"><strong>Chapters</strong><div class="meta">No decision clusters available yet.</div></div>';
    return;
  }

  const byReason = Object.create(null);
  for (const chapter of chapters) {
    byReason[String(chapter.reason)] = chapter;
  }
  chapterList.innerHTML = "";
  Object.entries(byReason)
    .sort((a, b) => reasonSpec(a[0]).reasonPriority - reasonSpec(b[0]).reasonPriority)
    .forEach(([reason, chapter]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "trackButton";
      button.dataset.reason = reason;
      const count = events.filter((event) => normalizeReason(event) === normalizeAlias(reason)).length;
      button.innerHTML = `<strong>${chapter.label || reasonLabel(reason)}</strong><span class="meta">${formatCount(count)} events · frame ${chapter.start_frame}-${chapter.end_frame}</span>`;
      button.addEventListener("click", () => {
        selectEventByFrame(chapter.start_frame, true);
      });
      chapterList.appendChild(button);
    });
}

function renderTimeline() {
  if (!activeTimeline) return;
  rulerLabel.textContent = `${activeTimeline.frame_count} frames · ${activeTimeline.fps} FPS · ${markerRows.length} decision markers`;
  markerPositions = layoutMarkerPositions(markerRows, Math.max(activeTimeline.frame_count, 1));
  updateTimelineLegend();
  drawCanvasLayers();
  drawMarkerState();
}

function layoutMarkerPositions(markers, frameCount) {
  const laneLastLeft = [];
  return markers.map((marker, markerIndex) => {
    const left = frameToPercent(marker.frame, Math.max(frameCount, 1));
    let lane = -1;
    for (let index = 0; index < laneLastLeft.length; index += 1) {
      if (left - laneLastLeft[index] > MARKER_GAP_PCT) {
        lane = index;
        break;
      }
    }
    if (lane === -1) {
      if (laneLastLeft.length < MARKER_LANE_COUNT) lane = laneLastLeft.length;
      else lane = markerIndex % MARKER_LANE_COUNT;
    }
    laneLastLeft[lane] = left;
    return { ...marker, markerIndex, lane, left };
  });
}

function updateTimelineLegend() {
  const counts = {};
  for (const marker of markerRows) {
    const reason = normalizeReason(marker);
    counts[reason] = (counts[reason] || 0) + 1;
  }
  timelineLegend.innerHTML = "";
  const keys = Object.keys(counts).filter((reason) => counts[reason] > 0).sort((a, b) => reasonSpec(a).reasonPriority - reasonSpec(b).reasonPriority);
  if (keys.length === 0) {
    timelineLegend.innerHTML = "<span class=\"legendItem\">No low-quality markers</span>";
    return;
  }
  for (const reason of keys) {
    const item = document.createElement("span");
    item.className = "legendItem";
    const spec = reasonSpec(reason);
    item.innerHTML = `<span class="legendSwatch" style="background:${spec.color}"></span>${spec.label} <span>(${counts[reason]})</span>`;
    timelineLegend.appendChild(item);
  }
  const breakEl = document.createElement("span");
  breakEl.className = "legendBreak";
  timelineLegend.appendChild(breakEl);
  const rejectedItem = document.createElement("span");
  rejectedItem.className = "legendItem";
  rejectedItem.innerHTML = '<span class="legendSwatch strokeRed"></span>Rejected stroke';
  timelineLegend.appendChild(rejectedItem);
  const mergedItem = document.createElement("span");
  mergedItem.className = "legendItem";
  mergedItem.innerHTML = '<span class="legendSwatch strokeAmber"></span>Merged stroke';
  timelineLegend.appendChild(mergedItem);
  const trackItem = document.createElement("span");
  trackItem.className = "legendItem";
  trackItem.innerHTML = '<span class="legendSwatch trackRing"></span>Track ring';
  timelineLegend.appendChild(trackItem);
  const keepItem = document.createElement("span");
  keepItem.className = "legendItem";
  keepItem.innerHTML = `<span class="legendSwatch" style="background:${DECISION_COLOR.kept}33;border:1px solid ${DECISION_COLOR.kept}"></span>Accepted span`;
  timelineLegend.appendChild(keepItem);
}

function renderTracks() {
  const showLowQuality = showOnlyLowQuality.checked;
  const showActive = showOnlyActiveTrack.checked;
  const rows = trackRows.filter((track) => {
    if (selectedTrackId !== null && showActive) return track.track_id === selectedTrackId;
    if (showLowQuality) return track.quality_count > 0;
    return true;
  });

  trackContainer.innerHTML = "";
  rows.slice(0, MAX_TRACK_ROWS).forEach((track) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "trackButton";
    row.dataset.trackId = String(track.track_id);
    const color = trackColor(track.track_id);
    const topReason = Object.entries(track.reasonCounts || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 2)
      .map(([reason, count]) => `${reasonLabel(reason)}: ${count}`)
      .join("  •  ");
    const reasonText = topReason || "kept-only";
    row.innerHTML = `
      <strong><span class="trackSwatch" style="background:${color}"></span>Track ${track.track_id}</strong>
      <span class="meta">Frames ${track.start_frame}–${track.end_frame} · Q ${(track.quality_count || 0)}</span>
      <span class="meta">${reasonText}</span>
    `;
    row.addEventListener("click", () => {
      setSelectedTrack(track.track_id === selectedTrackId ? null : track.track_id, true);
    });
    trackContainer.appendChild(row);
  });
  renderTrackLanes(rows);
  renderTrackStats();
  updateTrackSelectionUI();
}


function updateTrackSelectionUI() {
  trackContainer.querySelectorAll(".trackButton").forEach((button) => {
    const trackId = toInt(button.dataset.trackId, -1);
    button.classList.toggle("active", trackId === selectedTrackId);
  });
}

function renderTrackStats() {
  if (selectedTrackId === null) {
    selectedTrackLabel.textContent = "Not selected";
    selectedTrackChanges.textContent = "0";
    selectedTrackKept.textContent = "0";
    selectedTrackRejected.textContent = "0";
    selectedTrackSpan.textContent = "--";
    if (timelineSummaryText) timelineSummaryText.textContent = "No track selected · choose track row or timeline event.";
    return;
  }
  const row = trackById.get(selectedTrackId);
  if (!row) {
    selectedTrackLabel.textContent = String(selectedTrackId);
    selectedTrackChanges.textContent = "0";
    selectedTrackKept.textContent = "0";
    selectedTrackRejected.textContent = "0";
    selectedTrackSpan.textContent = "--";
    return;
  }
  const rejected = (row.rejected_count || 0) + (row.merged_count || 0);
  selectedTrackLabel.textContent = String(row.track_id);
  selectedTrackChanges.textContent = String(row.quality_count || 0);
  selectedTrackKept.textContent = String(row.kept_count || 0);
  selectedTrackRejected.textContent = String(rejected);
  selectedTrackSpan.textContent = `${row.start_frame}-${row.end_frame}`;
  if (timelineSummaryText) {
    const total = row.quality_count || 0;
    timelineSummaryText.textContent = `Track ${row.track_id}: ${total} quality edits · ${rejected} rejected, ${row.merged_count || 0} merged.`;
  }
}

function appendLaneEventMarker(lane, event, frameCount, trackEvents = null) {
  const from = frameToPercent(Math.max(event.frame, 0), frameCount);
  const markEl = document.createElement("span");
  markEl.className = "laneSpan laneEventMarker";
  const reason = normalizeReason(event);
  const spec = reasonSpec(reason);
  const opacity = confidenceToOpacity(event.confidence);
  const size = clamp(0.34 + opacity * 0.34, 0.34, 0.72);
  markEl.style.left = `${from}%`;
  markEl.style.width = `${size}rem`;
  markEl.style.height = `${size}rem`;
  markEl.style.top = "50%";
  markEl.style.transform = "translate(-50%, -50%)";
  markEl.style.borderRadius = "999px";
  markEl.style.background = hexToRgba(spec.color, opacity);
  markEl.style.borderColor = decisionStroke(event.decision, reason);
  markEl.style.boxShadow = Number.isFinite(event.track_id)
    ? `0 0 0 2px ${hexToRgba(trackColor(event.track_id), 0.42)}`
    : "0 0 0 1px rgba(216, 231, 255, 0.2)";
  markEl.title = `${Number.isFinite(event.track_id) ? `Track ${event.track_id}` : "Frame-level gate"} ${event.decision}: ${reasonLabel(reason)} · frame ${event.frame}`;
  markEl.style.cursor = "pointer";
  if (events[eventIndex]?.index === event.index) {
    markEl.classList.add("active");
  }
  markEl.addEventListener("click", (eventObj) => {
    eventObj.stopPropagation();
    if (trackEvents) {
      const trackEventIndex = trackEvents.findIndex((trackEvent) => trackEvent.index === event.index);
      selectedTrackEventIndex = trackEventIndex >= 0 ? trackEventIndex : null;
    }
    const selectedEventIndex = events.findIndex((row) => row.index === event.index);
    if (selectedEventIndex >= 0) {
      selectEvent(selectedEventIndex, true);
    }
  });
  lane.appendChild(markEl);
}

function appendFrameLevelLane(frameCount) {
  if (frameLevelEvents.length === 0) return;
  const lane = document.createElement("div");
  lane.className = "lane frameLane";
  const label = document.createElement("div");
  label.className = "laneLabel";
  label.innerHTML = `<span class="trackSwatch" style="background:#d8e7ff"></span>Frame gates <span style="color:#93a4ba">·</span> ${formatCount(frameLevelEvents.length)}`;
  lane.appendChild(label);
  for (const event of representativeEvents(frameLevelEvents, MAX_LANE_EVENT_MARKERS)) {
    appendLaneEventMarker(lane, event, frameCount, null);
  }
  lane.addEventListener("click", () => {
    const frame = Math.round(rawVideo.currentTime * Math.max(activeClip?.fps || 1, 1));
    const nearest = nearestEventByFrame(frame);
    if (nearest) {
      const index = events.findIndex((row) => row.index === nearest.index);
      if (index >= 0) selectEvent(index, true);
    }
  });
  laneContainer.appendChild(lane);
}

function renderTrackLanes(visibleRows) {
  const rows = visibleRows && visibleRows.length > 0 ? visibleRows : trackRows.slice(0, 20);
  laneContainer.innerHTML = "";
  const frameCount = Math.max(activeTimeline?.frame_count || 1, 1);
  const visibleTrackIds = new Set(rows.map((row) => row.track_id));
  appendFrameLevelLane(frameCount);
  for (const track of rows) {
    const lane = document.createElement("div");
    lane.className = "lane";
    if (track.track_id === selectedTrackId) lane.classList.add("activeTrack");
    const label = document.createElement("div");
    label.className = "laneLabel";
    const color = trackColor(track.track_id);
    const acceptedColor = color;
    label.innerHTML = `<span class="trackSwatch" style="background:${color}"></span>Track ${track.track_id} <span style="color:#93a4ba">·</span> ${track.quality_count || 0}`;
    lane.appendChild(label);

    const acceptance = document.createElement("span");
    acceptance.className = "laneSpan laneAcceptedSpan";
    acceptance.style.left = `${frameToPercent(track.start_frame, frameCount)}%`;
    acceptance.style.width = `${Math.max(frameToPercent(track.end_frame, frameCount) - frameToPercent(track.start_frame, frameCount), 0.24)}%`;
    acceptance.style.background = `${acceptedColor}18`;
    acceptance.style.borderColor = acceptedColor;
    acceptance.title = `Track ${track.track_id} ByteTrack span: frame ${track.start_frame}-${track.end_frame}`;
    lane.appendChild(acceptance);

    for (const span of track.spansByReason || []) {
      const widthPct = frameToPercent(span.end, frameCount) - frameToPercent(span.start, frameCount);
      const spanEl = document.createElement("span");
      spanEl.className = "laneSpan laneProblemSpan";
      const from = frameToPercent(Math.max(span.start, 0), frameCount);
      const to = Math.max(0.16, widthPct);
      const spec = reasonSpec(span.reason || "unknown");
      spanEl.style.left = `${from}%`;
      spanEl.style.width = `${Math.max(to, 0.16)}%`;
      spanEl.style.background = `${spec.color}2d`;
      spanEl.style.borderColor = spec.color;
      spanEl.title = `${spec.label}: frame ${span.start}-${span.end}`;
      lane.appendChild(spanEl);
    }

    const trackEvents = frameByTrackEvents.get(track.track_id) || [];
    const laneEvents = representativeEvents(trackEvents, MAX_LANE_EVENT_MARKERS);
    for (let laneIndex = 0; laneIndex < laneEvents.length; laneIndex += 1) {
      const event = laneEvents[laneIndex];
      appendLaneEventMarker(lane, event, frameCount, trackEvents);
    }
    lane.addEventListener("click", () => {
      setSelectedTrack(track.track_id, true);
    });
    laneContainer.appendChild(lane);
  }

  if (selectedTrackId === null && visibleTrackIds.size > 0 && showOnlyLowQuality.checked) {
    const first = rows.find((track) => (track.quality_count || 0) > 0);
    if (first) {
      const rowsToSelect = rows.filter((track) => (track.quality_count || 0) > 0);
      const candidate = rowsToSelect[0] || first;
      setSelectedTrack(candidate.track_id, false);
      renderTrackStats();
      renderTrackButtonsForNavigation();
      renderTrackEventList();
      drawTimelineState();
      drawMarkerState();
    }
  }
}

function drawCanvasLayers() {
  const box = markerCanvasRect();
  if (!box.width || !box.height) return;
  const pixelRatio = window.devicePixelRatio || 1;
  markerCanvas.width = Math.max(1, Math.floor(box.width * pixelRatio));
  markerCanvas.height = Math.max(1, Math.floor(box.height * pixelRatio));
  spanCanvas.width = markerCanvas.width;
  spanCanvas.height = markerCanvas.height;
  markerContext.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  spanContext.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  drawSpanCanvas(box);
  drawMarkerCanvas(box);
}

function drawSpanCanvas(box) {
  spanContext.clearRect(0, 0, box.width, box.height);
  const frameCount = Math.max(activeTimeline?.frame_count || 1, 1);
  const binCount = clamp(Math.floor(box.width / DENSITY_BIN_TARGET_PX), 80, 360);
  const bins = Array.from({ length: binCount }, () => ({ total: 0, reasons: new Map() }));
  for (const event of events) {
    const binIndex = clamp(Math.floor((toInt(event.frame, 0) / Math.max(frameCount - 1, 1)) * binCount), 0, binCount - 1);
    const reason = normalizeReason(event);
    const bin = bins[binIndex];
    bin.total += 1;
    bin.reasons.set(reason, (bin.reasons.get(reason) || 0) + 1);
  }
  const maxTotal = Math.max(1, ...bins.map((bin) => bin.total));
  const graphTop = 8;
  const graphHeight = Math.max(18, box.height - 18);
  const binWidth = Math.max(1.2, box.width / binCount);
  spanContext.fillStyle = "rgba(216, 231, 255, 0.06)";
  spanContext.fillRect(0, graphTop + graphHeight - 1, box.width, 1);
  for (let index = 0; index < bins.length; index += 1) {
    const bin = bins[index];
    if (bin.total === 0) continue;
    const x = index * binWidth;
    const totalHeight = Math.max(3, (bin.total / maxTotal) * graphHeight);
    let offset = 0;
    const reasons = [...bin.reasons.entries()].sort(
      (a, b) => reasonSpec(a[0]).reasonPriority - reasonSpec(b[0]).reasonPriority,
    );
    for (const [reason, count] of reasons) {
      const segmentHeight = Math.max(1.2, (count / bin.total) * totalHeight);
      const spec = reasonSpec(reason);
      spanContext.fillStyle = hexToRgba(spec.color, 0.52);
      spanContext.fillRect(x, graphTop + graphHeight - offset - segmentHeight, Math.max(1, binWidth - 1), segmentHeight);
      offset += segmentHeight;
    }
  }
}

function drawMarkerCanvas(box = markerCanvasRect()) {
  markerContext.clearRect(0, 0, box.width, box.height);
  markerContext.lineWidth = 1;
  const overviewMarkers = representativeMarkers(markerPositions, MAX_OVERVIEW_MARKERS);
  for (const marker of overviewMarkers) {
    const x = (marker.left / 100) * box.width;
    const y = Math.max(9, box.height - 10 - marker.lane * 7);
    const spec = reasonSpec(marker.reason || "unknown");
    const color = reasonColor(marker.decision, marker.reason);
    const trackColorValue = trackColor(marker.track_id);
    const opacity = confidenceToOpacity(marker.confidence);
    const size = clamp(confidenceToMarkerSize(marker.confidence) * 0.48, 2.1, 4.8);
    markerContext.fillStyle = hexToRgba(color, opacity * 0.82);
    markerContext.strokeStyle = hexToRgba(decisionStroke(marker.decision, marker.reason), opacity * 0.9);
    drawMarkerShape(markerContext, spec.shape, x, y, size);
    if (Number.isFinite(marker.track_id)) {
      markerContext.strokeStyle = hexToRgba(trackColorValue, opacity * 0.5);
      markerContext.lineWidth = 1.2;
      markerContext.beginPath();
      markerContext.arc(x, y, size * 1.15, 0, Math.PI * 2);
      markerContext.stroke();
    }
  }

  if (selectedMarkerIndex !== null && markerPositions[selectedMarkerIndex]) {
    const marker = markerPositions[selectedMarkerIndex];
    const x = (marker.left / 100) * box.width;
    const y = Math.max(9, box.height - 10 - marker.lane * 7);
    const spec = reasonSpec(marker.reason || "unknown");
    markerContext.lineWidth = 2.5;
    markerContext.strokeStyle = spec.color;
    markerContext.beginPath();
    markerContext.moveTo(x, 0);
    markerContext.lineTo(x, box.height);
    markerContext.stroke();
  }

  if (timelineHoverFrame !== null) {
    const hoverX = (frameToPercent(timelineHoverFrame, Math.max(activeTimeline?.frame_count || 1, 1)) / 100) * box.width;
    markerContext.strokeStyle = "rgba(255,255,255,0.45)";
    markerContext.lineWidth = 1;
    markerContext.beginPath();
    markerContext.moveTo(hoverX, 0);
    markerContext.lineTo(hoverX, box.height);
    markerContext.stroke();
  }
}

function drawMarkerShape(context, shape, x, y, size) {
  context.save();
  context.translate(x, y);
  switch (shape) {
    case "circle": {
      context.beginPath();
      context.arc(0, 0, size, 0, Math.PI * 2);
      context.fill();
      context.stroke();
      break;
    }
    case "diamond": {
      context.beginPath();
      context.moveTo(-size, 0);
      context.lineTo(0, -size);
      context.lineTo(size, 0);
      context.lineTo(0, size);
      context.closePath();
      context.fill();
      context.stroke();
      break;
    }
    case "triangle": {
      context.beginPath();
      context.moveTo(0, -size);
      context.lineTo(size, size);
      context.lineTo(-size, size);
      context.closePath();
      context.fill();
      context.stroke();
      break;
    }
    case "triangle-down": {
      context.beginPath();
      context.moveTo(0, size);
      context.lineTo(size, -size);
      context.lineTo(-size, -size);
      context.closePath();
      context.fill();
      context.stroke();
      break;
    }
    case "octagon": {
      const radius = size;
      context.beginPath();
      for (let index = 0; index < 8; index += 1) {
        const angle = -Math.PI / 8 + (Math.PI * 2 * index) / 8;
        const x0 = Math.cos(angle) * radius;
        const y0 = Math.sin(angle) * radius;
        if (index === 0) context.moveTo(x0, y0);
        else context.lineTo(x0, y0);
      }
      context.closePath();
      context.fill();
      context.stroke();
      break;
    }
    case "square":
    default: {
      const s = size;
      context.fillRect(-s, -s, s * 2, s * 2);
      context.strokeRect(-s, -s, s * 2, s * 2);
      break;
    }
    case "pentagon": {
      const radius = size;
      context.beginPath();
      for (let angle = -Math.PI / 2; angle < Math.PI * 2; angle += (Math.PI * 2) / 5) {
        const x0 = Math.cos(angle) * radius;
        const y0 = Math.sin(angle) * radius;
        if (angle === -Math.PI / 2) context.moveTo(x0, y0);
        else context.lineTo(x0, y0);
      }
      context.closePath();
      context.fill();
      context.stroke();
      break;
    }
    case "cross": {
      context.beginPath();
      context.moveTo(-size, 0);
      context.lineTo(size, 0);
      context.moveTo(0, -size);
      context.lineTo(0, size);
      context.stroke();
      break;
    }
  }
  context.restore();
}

function markerCanvasRect() {
  const rect = markerCanvas.getBoundingClientRect();
  return {
    width: rect.width,
    height: rect.height,
  };
}

function nearestMarkerFromPointer(event) {
  const rect = markerCanvas.getBoundingClientRect();
  const markerToSurfaceX = event.clientX - rect.left + (timeSurface.scrollLeft || 0);
  const localX = clamp(markerToSurfaceX, 0, timeContent.scrollWidth || rect.width);
  const localY = event.clientY - rect.top;
  const totalWidth = Math.max(timeContent.scrollWidth || rect.width, 1);
  const totalHeight = Math.max(rect.height, 1);
  let best = null;
  for (const marker of markerPositions) {
    const x = (marker.left / 100) * totalWidth;
    const y = Math.max(8, totalHeight - 16 - marker.lane * 12);
    const distance = Math.hypot(localX - x, localY - y);
    if (distance <= MARKER_HOVER_RADIUS && (best === null || distance < best.distance)) {
      best = { distance, markerIndex: marker.markerIndex };
    }
  }
  if (!best) return null;
  return best.markerIndex;
}

function nearestEventByFrame(frame) {
  if (events.length === 0) return null;
  const rows = eventsByFrame.get(toInt(frame)) || [];
  if (rows.length) return rows[0];
  let lo = 0;
  let hi = events.length - 1;
  while (lo < hi) {
    const mid = ((lo + hi) / 2) | 0;
    if (events[mid].frame < frame) lo = mid + 1;
    else hi = mid;
  }
  const next = events[lo];
  const prev = lo > 0 ? events[lo - 1] : null;
  if (!next) return prev || null;
  if (!prev) return next;
  return Math.abs(frame - prev.frame) <= Math.abs(next.frame - frame) ? prev : next;
}

function showDecision(event) {
  const reason = normalizeReason(event);
  const color = decisionColor(event.decision, reason);
  const source = event.source ? (event.source.source === "tracks" ? "Track row" : "Detector") : "Detector";
  const trajectoryText = Number.isFinite(event.track_id)
    ? `Trajectory ${event.track_id} was reviewed at frame ${toInt(event.frame, 0)}.`
    : `Frame ${toInt(event.frame, 0)} was handled by a frame-level quality gate before MOT assignment.`;
  const actionText = event.decision === "merged"
    ? "The adapter merged duplicate evidence into a cleaner trajectory."
    : event.decision === "rejected"
      ? "The adapter removed this low-quality detection from the approved robotics trajectory data."
      : "The adapter kept this detection as approved trajectory evidence.";
  decisionCard.innerHTML = `
    <span class="decisionLabel" style="background:${color}22;color:${color}">${event.decision.toUpperCase()}</span>
    <div class="kv">
      <span>Frame</span><strong>${toInt(event.frame, 0)}</strong>
      <span>Detection ID</span><strong>${event.detection_id || "—"}</strong>
      <span>Track ID</span><strong>${event.track_id === null ? "—" : event.track_id}</strong>
      <span>Decision</span><strong>${event.decision}</strong>
      <span>Reason</span><strong>${reasonLabel(reason)}</strong>
      <span>Decision Mode</span><strong>${reason || "unknown"}</strong>
      <span>Stage</span><strong>${event.stage || "n/a"}</strong>
      <span>Confidence</span><strong>${toFloat(event.confidence).toFixed(3)}</strong>
      <span>Timestamp</span><strong>${(toInt(event.frame, 0) / Math.max(activeClip?.fps || 1, 1)).toFixed(3)} s</strong>
      <span>Source</span><strong>${source}</strong>
      <span>Track Color</span><strong>${event.track_id === null ? "—" : `rgb ${trackColor(toInt(event.track_id))}`}</strong>
    </div>
    <div class="decisionList">
      <span class="decisionPill"><span class="dot" style="background:${decisionColor(event.decision, reason)}"></span>Reason channel (color)</span>
      <span class="decisionPill"><span class="dot" style="background:${trackColor(event.track_id)}"></span>Track channel</span>
      <span class="decisionPill">Shape channel: ${reasonSpec(reason).shape}</span>
    </div>
    <div class="decisionStory">${trajectoryText} ${actionText}</div>
  `;

  if (trackEventList) {
    renderTrackEventList();
  }
}

function renderTrackEventList() {
  if (!trackEventList) return;

  if (selectedTrackId === null) {
    trackEventList.innerHTML = '<div class="trackEventEmpty">Select a trajectory to inspect low-quality timeline events.</div>';
    return;
  }

  const eventsForTrack = frameByTrackEvents.get(selectedTrackId) || [];
  if (eventsForTrack.length === 0) {
    trackEventList.innerHTML = `<div class="trackEventEmpty">No quality events recorded for Track ${selectedTrackId}.</div>`;
    selectedTrackEventIndex = null;
    return;
  }

  trackEventList.innerHTML = `
    <div class="trackEventHeader">
      <span>Frame</span><span>Decision</span><span>Class</span><span>Confidence</span>
    </div>
  `;

  const list = document.createElement("div");
  list.className = "trackEventItems";
  const displayRows = eventsForTrack.slice(0, TRACK_EVENT_LIMIT);

  for (let rowIndex = 0; rowIndex < displayRows.length; rowIndex += 1) {
    const row = displayRows[rowIndex];
    const reason = normalizeReason(row);
    const color = decisionColor(row.decision, reason);
    const spec = reasonSpec(reason);
    const isActive = events[eventIndex]?.index === row.index;
    const rowNode = document.createElement("button");
    rowNode.type = "button";
    rowNode.className = `trackEventItem ${isActive ? "active" : ""}`;
    rowNode.dataset.eventIndex = String(row.index);
    rowNode.title = `Frame ${row.frame} · ${spec.label}`;
    rowNode.innerHTML = `
      <span>${toInt(row.frame)}</span>
      <span style="color:${color}">${row.decision.toUpperCase()}</span>
      <span>${reasonLabel(reason)}</span>
      <span>${toFloat(row.confidence).toFixed(3)}</span>
    `;
    rowNode.addEventListener("click", () => {
      const idx = events.findIndex((eventRow) => eventRow.index === row.index);
      if (idx >= 0) {
        selectedTrackEventIndex = rowIndex;
        selectEvent(idx, true);
      }
    });
    list.appendChild(rowNode);
  }

  if (eventsForTrack.length > displayRows.length) {
    const overflow = document.createElement("div");
    overflow.className = "trackEventOverflow";
    overflow.textContent = `+${eventsForTrack.length - displayRows.length} more events`;
    list.appendChild(overflow);
  }

  trackEventList.appendChild(list);
  scrollActiveTrackEventIntoView();
}

function scrollActiveTrackEventIntoView() {
  if (!trackEventList) return;
  const activeRow = trackEventList.querySelector(".trackEventItem.active");
  if (!activeRow) return;
  requestAnimationFrame(() => {
    activeRow.scrollIntoView({ block: "nearest", inline: "nearest" });
  });
}

function renderFrame(frame = null) {
  if (!activeClip) return;
  const frameToRender = Math.max(0, toInt(frame, Math.round(rawVideo.currentTime * Math.max(activeClip.fps, 1))));
  const rows = boxesByFrame.get(frameToRender) || [];
  showFrameInfo(frameToRender);
  renderSvg(rawOverlaySvg, rows, "raw");
  const filtered = filterAdapterRows(rows);
  renderSvg(adapterOverlaySvg, filtered, "adapter");
  updatePlayheadForFrame(frameToRender);
}

function showFrameInfo(frame) {
  cursorFrame.textContent = String(toInt(frame));
  const nearest = nearestEventByFrame(toInt(frame));
  cursorDecision.textContent = nearest ? nearest.decision : "No change";
  cursorReason.textContent = nearest ? reasonLabel(normalizeReason(nearest)) : "No decision";
}

function filterAdapterRows(rows) {
  return rows.filter((row) => {
    const rowDecision = String(row.decision || "kept");
    if (adapterMode === QUALITY_TRACK_MODES.RAW_ONLY) return false;
    if (showOnlyActiveTrack.checked && selectedTrackId !== null) {
      if (row.track_id !== selectedTrackId) return false;
    }
    if (adapterMode === QUALITY_TRACK_MODES.REJECTED_ONLY) {
      return rowDecision === "rejected" || rowDecision === "merged";
    }
    if (adapterMode === QUALITY_TRACK_MODES.KEPT_ONLY) {
      return rowDecision === "kept";
    }
    if (adapterMode === QUALITY_TRACK_MODES.RAW_ONLY) {
      return false;
    }
    if (adapterMode === QUALITY_TRACK_MODES.ALL) {
      return true;
    }
    return rowDecision === "kept";
  });
}

function renderSvg(svg, rows, mode) {
  svg.innerHTML = "";
  for (const row of rows) {
    appendBox(svg, row, mode);
  }
}

function appendBox(svg, row, mode) {
  const x1 = toFloat(row.x1);
  const y1 = toFloat(row.y1);
  const x2 = toFloat(row.x2);
  const y2 = toFloat(row.y2);
  if (!(x2 > x1 && y2 > y1)) return;
  const decision = String(row.decision || "kept");
  const reason = normalizeReason(row);
  const trackId = toNullableInt(row.track_id);
  const color = decision === "kept" ? trackColor(trackId) : decisionColor(decision, reason);

  const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  rect.setAttribute("x", x1);
  rect.setAttribute("y", y1);
  rect.setAttribute("width", Math.max(x2 - x1, 1));
  rect.setAttribute("height", Math.max(y2 - y1, 1));
  rect.classList.add("overlayBox");
  rect.classList.add(decision);
  rect.style.stroke = color;
  rect.style.strokeWidth = String(mode === "adapter" ? 4 : 3);
  rect.style.opacity = mode === "adapter" ? "1" : "0.95";
  if (mode === "adapter" && selectedTrackId !== null && row.track_id !== selectedTrackId) {
    rect.classList.add("track-fade");
  } else if (mode === "raw" && showOnlyActiveTrack.checked && selectedTrackId !== null && row.track_id !== selectedTrackId) {
    rect.classList.add("track-fade");
  }

  rect.addEventListener("click", (event) => {
    event.stopPropagation();
    const sourceFrame = toInt(row.frame);
    const eventByFrame = nearestEventByFrame(sourceFrame);
    if (eventByFrame) {
      const index = events.findIndex((entry) => entry.index === eventByFrame.index);
      selectEvent(index >= 0 ? index : 0, true);
    }
    inspectRow(row);
  });
  svg.appendChild(rect);

  const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
  label.classList.add("overlayLabel");
  label.setAttribute("x", x1 + 4);
  label.setAttribute("y", y1 + 16);
  label.setAttribute("fill", color);
  label.textContent = `${trackId === null ? "T?" : `T${trackId}`}·${decision[0].toUpperCase()}/${reasonLabel(reason).slice(0, 8)}`;
  svg.appendChild(label);
}

function inspectRow(row) {
  const reason = normalizeReason(row);
  showDecision({
    decision: String(row.decision || "kept"),
    frame: toInt(row.frame),
    detection_id: String(row.detection_id || ""),
    track_id: toNullableInt(row.track_id),
    confidence: toFloat(row.score, toFloat(row.confidence)),
    stage: String(row.stage || ""),
    reason,
    display_label: reasonLabel(reason),
    source: row,
  });
}

function setAdapterMode(mode) {
  adapterMode = mode;
  showRawButton.style.opacity = mode === QUALITY_TRACK_MODES.RAW_ONLY ? "1" : "0.72";
  showAdapterKeptOnlyButton.style.opacity = mode === QUALITY_TRACK_MODES.KEPT_ONLY ? "1" : "0.72";
  showAdapterRejectedOnlyButton.style.opacity = mode === QUALITY_TRACK_MODES.REJECTED_ONLY ? "1" : "0.72";
  renderFrame(Math.round(rawVideo.currentTime * Math.max(activeClip.fps, 1)));
}

function setSelectedTrack(trackId, shouldRender = true) {
  selectedTrackId = toNullableInt(trackId);
  if (selectedTrackId === null || !trackById.has(selectedTrackId)) {
    selectedTrackId = null;
  }
  if (showOnlyActiveTrack.checked && selectedTrackId === null) {
    showOnlyActiveTrack.checked = false;
  }
  if (shouldRender) {
    renderTracks();
    if (selectedTrackId !== null && events.length > 0) {
      const rows = frameByTrackEvents.get(selectedTrackId) || [];
      if (rows.length > 0) {
        const frame = rows[0].frame;
        const event = nearestEventByFrame(frame);
        if (event) {
          const eventArrayIndex = events.findIndex((row) => row.index === event.index);
          selectEvent(eventArrayIndex >= 0 ? eventArrayIndex : 0, true);
        } else {
          selectedTrackEventIndex = null;
          renderTrackEventList();
        }
      } else {
        selectedTrackEventIndex = null;
        renderTrackEventList();
      }
    }
    trackSummary.textContent = selectedTrackId === null ? "No track selected" : `Track ${selectedTrackId} selected`;
    renderTrackEventList();
    drawTimelineState();
  }
}

function renderTrackButtonsForNavigation() {
  const hasTrackEvents = Number.isFinite(selectedTrackId) && (frameByTrackEvents.get(selectedTrackId) || []).length > 0;
  prevTrackEventButton.disabled = !hasTrackEvents;
  nextTrackEventButton.disabled = !hasTrackEvents;
}

function drawTimelineState() {
  if (!activeTimeline) return;
  playheadHandle.style.left = "0.0rem";
  playheadHandle.style.top = "-0.3rem";
  updatePlayheadForFrame(Math.round(rawVideo.currentTime * Math.max(activeClip.fps || 1, 1)));
}

function updatePlayheadForFrame(frame) {
  if (!activeTimeline) return;
  const percent = frameToPercent(frame, Math.max(activeTimeline.frame_count, 1));
  playhead.style.left = `${percent}%`;
  timeLabel.textContent = `${(frame / Math.max(activeClip?.fps || 1, 1)).toFixed(3)}s · frame ${toInt(frame)}`;
}

function selectEvent(eventIdx, scrollToEvent = false) {
  if (events.length === 0) {
    decisionCard.textContent = "No adapter decision events for this clip.";
    renderTrackEventList();
    return;
  }
  eventIndex = clamp(eventIdx, 0, events.length - 1);
  const event = events[eventIndex];
  if (!event) return;
  selectedMarkerIndex = markerPositions.findIndex((marker) => marker.frame === event.frame);
  if (Number.isFinite(event.track_id)) {
    const rows = frameByTrackEvents.get(event.track_id) || [];
    selectedTrackEventIndex = rows.findIndex((row) => row.index === event.index);
    if (selectedTrackEventIndex < 0) {
      selectedTrackEventIndex = null;
    }
  } else {
    selectedTrackEventIndex = null;
  }
  if (Number.isFinite(event.track_id) && selectedTrackId !== event.track_id) {
    selectedTrackId = event.track_id;
    updateTrackSelectionUI();
    renderTrackStats();
    renderTrackButtonsForNavigation();
    renderTrackLanes(
      trackRows.filter((track) => {
        if (showOnlyActiveTrack.checked) return track.track_id === selectedTrackId;
        if (showOnlyLowQuality.checked) return track.quality_count > 0;
        return true;
      }),
    );
  }
  showDecision(event);
  queueSeekToFrame(event.frame, scrollToEvent);
  if (showOnlyActiveTrack.checked && Number.isFinite(event.track_id)) {
    setSelectedTrack(event.track_id, false);
  }
  if (selectedTrackId !== null) renderTrackButtonsForNavigation();
  drawMarkerState();
  renderTrackEventList();
}

function selectEventByFrame(targetFrame, scrollToEvent = false) {
  const nearest = nearestEventByFrame(toInt(targetFrame));
  if (!nearest) return;
  const index = events.findIndex((row) => row.index === nearest.index);
  if (index >= 0) selectEvent(index, scrollToEvent);
}

function selectAdjacentTrackEvent(direction) {
  if (!Number.isFinite(selectedTrackId)) return;
  const rows = frameByTrackEvents.get(selectedTrackId) || [];
  if (rows.length === 0) return;
  const pointerFrame = Math.round(rawVideo.currentTime * Math.max(activeClip?.fps || 1, 1));
  const nearest = nearestEventByFrame(pointerFrame);
  if (!Number.isFinite(selectedTrackEventIndex) || !rows[selectedTrackEventIndex]) {
    const pointerNearestIndex = rows.findIndex((row) => row.frame >= (nearest?.frame ?? pointerFrame));
    selectedTrackEventIndex = clamp(pointerNearestIndex === -1 ? rows.length - 1 : pointerNearestIndex, 0, rows.length - 1);
  }
  const targetIndex = clamp(selectedTrackEventIndex + direction, 0, rows.length - 1);
  selectedTrackEventIndex = targetIndex;
  const target = rows[targetIndex];
  const event = events.find((row) => row.index === target.index);
  if (!event) return;
  const eventArrayIndex = events.findIndex((row) => row.index === event.index);
  if (eventArrayIndex >= 0) selectEvent(eventArrayIndex, true);
}

function queueSeekToFrame(frame, scrollToTimeline = false) {
  pendingSeekFrame = toInt(frame, 0);
  if (scrollToTimeline) scrollTimelineToFrame(pendingSeekFrame);
  if (seekAnimationFrame !== 0) return;
  seekAnimationFrame = window.requestAnimationFrame(flushQueuedSeek);
}

function flushQueuedSeek() {
  seekAnimationFrame = 0;
  const targetFrame = pendingSeekFrame;
  pendingSeekFrame = null;
  if (targetFrame === null) return;
  seekToFrame(targetFrame);
}

function seekToFrame(frame) {
  const seconds = frame / Math.max(activeClip?.fps || 1, 1);
  rawVideo.currentTime = seconds;
  adapterVideo.currentTime = seconds;
  renderFrame(frame);
  drawMarkerState();
}

function syncVideos(source, target) {
  if (syncLock || Math.abs(source.currentTime - target.currentTime) <= 0.08) return;
  syncLock = true;
  target.currentTime = source.currentTime;
  syncLock = false;
}

function updatePlayheadForViewport() {
  const frame = Math.round(rawVideo.currentTime * Math.max(activeClip.fps, 1));
  updatePlayheadForFrame(frame);
  showFrameInfo(frame);
  drawMarkerState();
}

function scrollTimelineToFrame(frame) {
  if (!activeTimeline) return;
  const percent = frameToPercent(frame, Math.max(activeTimeline.frame_count, 1));
  const width = timeContent.getBoundingClientRect().width;
  const target = (percent / 100) * width - timeSurface.clientWidth / 2;
  timeSurface.scrollLeft = clamp(target, 0, Math.max(0, timeContent.scrollWidth - timeSurface.clientWidth));
}

function frameFromPointer(event, sourceRect = markerCanvas) {
  const rect = sourceRect.getBoundingClientRect();
  const localX = clamp(
    event.clientX - rect.left + (timeSurface.scrollLeft || 0),
    0,
    Math.max(sourceRect.scrollWidth || rect.width, 1),
  );
  const spanWidth = Math.max(sourceRect.scrollWidth || rect.width, 1);
  const percent = localX / spanWidth;
  return Math.round(percent * Math.max((activeTimeline?.frame_count || 1) - 1, 0));
}

function bindTimelinePointerEvents() {
  timeSurface.addEventListener("pointerdown", (event) => {
    isScrubbing = true;
    scrubMoved = false;
    scrubStartX = event.clientX;
    const frame = frameFromPointer(event, timeSurface);
    timelineHoverFrame = frame;
    queueSeekToFrame(frame);
    drawMarkerState();
    timeSurface.setPointerCapture(event.pointerId);
  });
  timeSurface.addEventListener("pointermove", (event) => {
    if (!isScrubbing) return;
    scrubMoved = scrubMoved || Math.abs(event.clientX - scrubStartX) > 3;
    const frame = frameFromPointer(event, timeSurface);
    timelineHoverFrame = frame;
    queueSeekToFrame(frame);
    if (!scrubMoved) {
      showFrameInfo(frame);
    }
  });
  timeSurface.addEventListener("pointerup", (event) => {
    if (!isScrubbing) return;
    isScrubbing = false;
    const frame = frameFromPointer(event, timeSurface);
    timelineHoverFrame = frame;
    if (!scrubMoved) {
      const nearest = nearestMarkerAtFrame(frame);
      if (nearest !== null) {
        selectEventByIndex(nearest, true);
      }
    }
    queueSeekToFrame(frame, true);
  });
  timeSurface.addEventListener("pointerleave", () => {
    timelineHoverFrame = null;
    drawMarkerState();
  });
}

function bindMarkerCanvasPointerEvents() {
  markerCanvas.addEventListener("pointerdown", (event) => {
    event.stopPropagation();
    const markerIndex = nearestMarkerFromPointer(event);
    if (markerIndex !== null) {
      selectEventByIndex(markerIndex, true);
      return;
    }
    const frame = frameFromPointer(event, markerCanvas);
    timelineHoverFrame = frame;
    queueSeekToFrame(frame);
  });
  markerCanvas.addEventListener("pointermove", (event) => {
    event.stopPropagation();
    const markerIndex = nearestMarkerFromPointer(event);
    selectedMarkerIndex = markerIndex;
    if (markerIndex !== null && markerPositions[markerIndex]) {
      const marker = markerPositions[markerIndex];
      const frame = toInt(marker.frame, 0);
      timelineHoverFrame = frame;
      showFrameInfo(frame);
    }
    drawMarkerState();
  });
  markerCanvas.addEventListener("mouseout", () => {
    if (!isScrubbing) {
      const frame = Math.round(rawVideo.currentTime * Math.max(activeClip.fps || 1, 1));
      timelineHoverFrame = null;
      showFrameInfo(frame);
      drawMarkerState();
    }
  });
}

function selectEventByIndex(index, scrollToEvent = false) {
  const marker = markerPositions[index];
  if (!marker) return;
  const frameRows = eventsByFrame.get(toInt(marker.frame)) || [];
  if (frameRows.length === 0) return;
  const event = frameRows[0];
  const idx = events.findIndex((row) => row.index === event.index);
  if (idx >= 0) {
    selectEvent(idx, scrollToEvent);
  }
}

function nearestMarkerAtFrame(frame) {
  let best = null;
  for (let index = 0; index < markerPositions.length; index += 1) {
    const marker = markerPositions[index];
    if (!best) {
      best = { index, distance: Math.abs(marker.frame - frame) };
      continue;
    }
    const distance = Math.abs(marker.frame - frame);
    if (distance < best.distance) {
      best = { index, distance };
    }
  }
  return best ? best.index : null;
}

function bindWheelZoom() {
  timeSurface.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const nextValue = clamp(
        Number(zoomSlider.value) + (event.deltaY < 0 ? 0.25 : -0.25),
        1,
        8,
      );
      zoomSlider.value = String(nextValue);
      applyZoom();
    },
    { passive: false },
  );
}

function bindClipButtons() {
  document.querySelectorAll(".clip").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".clip").forEach((node) => node.classList.remove("active"));
      button.classList.add("active");
      activeClip = story.clips[Number(button.dataset.clipIndex)] || null;
      loadClip(activeClip);
    });
  });
}

function bindVideoEvents() {
  rawVideo.addEventListener("timeupdate", () => {
    syncVideos(rawVideo, adapterVideo);
    renderFrame(Math.round(rawVideo.currentTime * Math.max(activeClip.fps, 1)));
  });
  adapterVideo.addEventListener("timeupdate", () => {
    syncVideos(adapterVideo, rawVideo);
    renderFrame(Math.round(adapterVideo.currentTime * Math.max(activeClip.fps, 1)));
  });
}

function applyZoom() {
  const zoom = clamp(Number(zoomSlider.value), 1, 8);
  timeContent.style.width = `${zoom * 100}%`;
  zoomText.textContent = `${zoom.toFixed(2)}x`;
  zoomBadge.textContent = `${zoom.toFixed(1)}x`;
  drawTimelineState();
  drawCanvasLayers();
}

function drawMarkerState() {
  drawCanvasLayers();
}

function fitTrackInView() {
  if (selectedTrackId === null) return;
  const row = trackById.get(selectedTrackId);
  if (!row) return;
  const centerFrame = Math.floor((row.start_frame + row.end_frame) / 2);
  scrollTimelineToFrame(centerFrame);
  queueSeekToFrame(centerFrame, true);
}

function clearTrackSelection() {
  selectedTrackId = null;
  showOnlyActiveTrack.checked = false;
  renderTracks();
  renderTrackStats();
  trackSummary.textContent = "No track selected";
  selectedTrackEventIndex = null;
  renderTrackButtonsForNavigation();
  renderTrackEventList();
  drawMarkerState();
}

function togglePlay() {
  if (rawVideo.paused) {
    rawVideo.play();
    adapterVideo.play();
    return;
  }
  rawVideo.pause();
  adapterVideo.pause();
}

function onFocusTrack() {
  const event = events[eventIndex];
  if (!event || !Number.isFinite(event.track_id)) return;
  setSelectedTrack(event.track_id, true);
}

function setFiltersAndRender() {
  renderTracks();
  renderTrackStats();
  renderTrackButtonsForNavigation();
  renderTrackEventList();
  const currentFrame = Math.round(rawVideo.currentTime * Math.max(activeClip.fps, 1));
  renderFrame(currentFrame);
  drawMarkerState();
}

function wireInputs() {
  showOnlyActiveTrack.addEventListener("change", () => {
    if (showOnlyActiveTrack.checked && selectedTrackId === null) {
      const first = trackRows.find((row) => row.quality_count > 0) || trackRows[0];
      selectedTrackId = first ? first.track_id : null;
    }
    setFiltersAndRender();
  });
  showOnlyLowQuality.addEventListener("change", () => {
    setFiltersAndRender();
  });
}

function wireControls() {
  zoomSlider.addEventListener("input", applyZoom);
  prevEventButton.addEventListener("click", () => selectEvent(eventIndex - 1, true));
  nextEventButton.addEventListener("click", () => selectEvent(eventIndex + 1, true));
  playPauseButton.addEventListener("click", togglePlay);
  fitToTrackButton.addEventListener("click", fitTrackInView);
  clearTrackButton.addEventListener("click", clearTrackSelection);
  focusTrackButton.addEventListener("click", onFocusTrack);
  prevTrackEventButton.addEventListener("click", () => selectAdjacentTrackEvent(-1));
  nextTrackEventButton.addEventListener("click", () => selectAdjacentTrackEvent(1));

  showRawButton.addEventListener("click", () => {
    setAdapterMode(QUALITY_TRACK_MODES.RAW_ONLY);
    drawMarkerState();
    renderFrame(Math.round(rawVideo.currentTime * Math.max(activeClip.fps, 1)));
  });
  showAdapterKeptOnlyButton.addEventListener("click", () => {
    setAdapterMode(QUALITY_TRACK_MODES.KEPT_ONLY);
    drawMarkerState();
    renderFrame(Math.round(rawVideo.currentTime * Math.max(activeClip.fps, 1)));
  });
  showAdapterRejectedOnlyButton.addEventListener("click", () => {
    setAdapterMode(QUALITY_TRACK_MODES.REJECTED_ONLY);
    drawMarkerState();
    renderFrame(Math.round(rawVideo.currentTime * Math.max(activeClip.fps, 1)));
  });
}

function updateOnResize() {
  applyZoom();
  const currentFrame = Math.round(rawVideo.currentTime * Math.max(activeClip.fps || 1, 1));
  renderFrame(currentFrame);
}

bindClipButtons();
bindTimelinePointerEvents();
bindMarkerCanvasPointerEvents();
bindWheelZoom();
bindVideoEvents();
wireInputs();
wireControls();
window.addEventListener("resize", updateOnResize);

loadClip(activeClip);
