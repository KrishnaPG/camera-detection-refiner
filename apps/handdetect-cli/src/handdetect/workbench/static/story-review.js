const root = document.querySelector(".shell");
const story = JSON.parse(root.dataset.story);
const suiteId = root.dataset.suiteId;
const runId = root.dataset.runId;
const rawVideo = document.getElementById("rawVideo");
const adapterVideo = document.getElementById("adapterVideo");
const rawOverlaySvg = document.getElementById("rawOverlaySvg");
const adapterOverlaySvg = document.getElementById("adapterOverlaySvg");
const timeLabel = document.getElementById("timeLabel");
const decisionCard = document.getElementById("decisionCard");
const timeSurface = document.querySelector(".timeSurface");
const timeContent = document.getElementById("timeContent");
const playhead = document.getElementById("playhead");
const zoomSlider = document.getElementById("zoomSlider");
const thumbStrip = document.getElementById("thumbStrip");
const markerCanvas = document.getElementById("markerCanvas");
const markerContext = markerCanvas.getContext("2d");
const markerLaneCount = 6;
const markerMinGapPct = 2.4;
const markerHitRadiusPx = 11;
let activeClip = story.clips[0] || null;
let events = [];
let eventIndex = 0;
let activeTimeline = null;
let markerPositions = [];
let boxesByFrame = new Map();
let selectedTrackId = null;
let isScrubbing = false;
let scrubStartX = 0;
let scrubMoved = false;
let pendingSeekFrame = null;
let seekAnimationFrame = 0;
let syncLock = false;

function artifactUrl(path) {
  return `/artifacts/${suiteId}/${runId}/${path}`;
}

async function loadClip(clip) {
  if (!clip) return;
  activeClip = clip;
  rawVideo.src = artifactUrl(clip.raw_overlay_url);
  adapterVideo.src = artifactUrl(clip.adapter_overlay_url);
  thumbStrip.src = artifactUrl(clip.thumbnail_strip_url);
  const payloads = await Promise.all([
    fetch(artifactUrl(clip.events_path)).then((response) => response.json()),
    fetch(artifactUrl(clip.timeline_path)).then((response) => response.json()),
    fetch(artifactUrl(clip.tracks_path)).then((response) => response.json()),
    fetch(artifactUrl(clip.boxes_path)).then((response) => response.json()),
  ]);
  applyClipPayloads(payloads);
}

function applyClipPayloads([eventPayload, timelinePayload, trackPayload, boxPayload]) {
  events = eventPayload.events.filter((event) => event.decision !== "kept");
  boxesByFrame = new Map(boxPayload.frames.map((frame) => [frame.frame, frame.boxes]));
  rawOverlaySvg.setAttribute("viewBox", `0 0 ${boxPayload.video_width} ${boxPayload.video_height}`);
  adapterOverlaySvg.setAttribute("viewBox", `0 0 ${boxPayload.video_width} ${boxPayload.video_height}`);
  eventIndex = 0;
  selectedTrackId = null;
  renderTimeline(timelinePayload);
  renderTracks(trackPayload);
  selectEvent(0, true);
}

function renderTimeline(timeline) {
  activeTimeline = timeline;
  document.getElementById("ruler").textContent =
    `${timeline.frame_count} frames · ${timeline.fps} FPS · ${timeline.markers.length} decisions`;
  markerPositions = layoutMarkerPositions(timeline.markers, timeline.frame_count);
  renderTrackLanes(timeline.track_lanes);
  applyZoom();
}

function layoutMarkerPositions(markers, frameCount) {
  const laneLastLeft = [];
  return markers.map((marker, index) => {
    const left = Math.min(99, (marker.frame / Math.max(frameCount, 1)) * 100);
    const lane = markerLane(left, laneLastLeft, index);
    laneLastLeft[lane] = left;
    return { ...marker, eventIndex: index, lane, left };
  });
}

function markerLane(left, laneLastLeft, index) {
  let lane = laneLastLeft.findIndex((lastLeft) => left - lastLeft > markerMinGapPct);
  if (lane === -1 && laneLastLeft.length < markerLaneCount) lane = laneLastLeft.length;
  return lane === -1 ? index % markerLaneCount : lane;
}

function renderTrackLanes(trackLanes) {
  const lanes = document.getElementById("lanes");
  lanes.innerHTML = trackLanes.slice(0, 8).map((trackId) =>
    `<div class="lane"><span style="left:0;width:100%" title="Track ${trackId}"></span></div>`
  ).join("");
}

function drawMarkerCanvas() {
  const box = markerCanvas.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  markerCanvas.width = Math.max(1, Math.floor(box.width * pixelRatio));
  markerCanvas.height = Math.max(1, Math.floor(box.height * pixelRatio));
  markerContext.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  markerContext.clearRect(0, 0, box.width, box.height);
  markerPositions.forEach((marker) => drawMarker(marker, box));
}

function drawMarker(marker, box) {
  const x = (marker.left / 100) * box.width;
  const y = box.height - 8 - marker.lane * 12;
  markerContext.save();
  markerContext.translate(x, y);
  markerContext.rotate(Math.PI / 4);
  markerContext.fillStyle = marker.decision === "merged" ? "#ffd60a" : "#ff453a";
  markerContext.fillRect(-4, -4, 8, 8);
  markerContext.restore();
}

function renderTracks(payload) {
  const trackList = document.getElementById("trackList");
  trackList.innerHTML = payload.tracks.slice(0, 12).map((track) =>
    `<button class="trackButton" data-track-id="${track.track_id}">ID ${track.track_id}<br /><span>${track.start_frame}-${track.end_frame} · ${track.observation_count} observations</span></button>`
  ).join("");
  trackList.querySelectorAll(".trackButton").forEach((button) => {
    button.addEventListener("click", () => toggleTrack(Number(button.dataset.trackId)));
  });
  renderTrackButtons();
}

function toggleTrack(trackId) {
  selectedTrackId = selectedTrackId === trackId ? null : trackId;
  renderTrackButtons();
  renderFrameBoxes();
}

function renderTrackButtons() {
  document.querySelectorAll(".trackButton").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.trackId) === selectedTrackId);
  });
}

function selectEvent(index, scrollIntoView = false) {
  if (events.length === 0) {
    decisionCard.textContent = "No adapter decision events for this clip.";
    return;
  }
  eventIndex = Math.max(0, Math.min(index, events.length - 1));
  const event = events[eventIndex];
  queueSeekToFrame(event.frame, scrollIntoView);
  showDecision(event);
}

function showDecision(event) {
  decisionCard.innerHTML = `
    <span class="decisionLabel">${event.decision.toUpperCase()}</span>
    <div class="kv">
      <span>Frame</span><strong>${event.frame}</strong>
      <span>Detection</span><strong>${event.detection_id}</strong>
      <span>Track</span><strong>${event.track_id ?? "--"}</strong>
      <span>Confidence</span><strong>${event.confidence.toFixed(3)}</strong>
      <span>Stage</span><strong>${event.stage}</strong>
      <span>Reason</span><strong>${event.display_label}</strong>
      <span>Box</span><strong>${boxText(event.box)}</strong>
    </div>`;
}

function boxText(box) {
  return `${Math.round(box.x1)},${Math.round(box.y1)} -> ${Math.round(box.x2)},${Math.round(box.y2)}`;
}

function queueSeekToFrame(frame, scrollIntoView = false) {
  pendingSeekFrame = frame;
  updatePlayheadForFrame(frame);
  if (scrollIntoView) scrollTimelineToFrame(frame);
  if (seekAnimationFrame !== 0) return;
  seekAnimationFrame = window.requestAnimationFrame(flushQueuedSeek);
}

function flushQueuedSeek() {
  seekAnimationFrame = 0;
  const frame = pendingSeekFrame;
  pendingSeekFrame = null;
  if (frame === null) return;
  seekToFrame(frame);
}

function seekToFrame(frame) {
  const seconds = frame / Math.max(activeClip.fps, 1);
  rawVideo.currentTime = seconds;
  adapterVideo.currentTime = seconds;
  renderFrameBoxesForFrame(frame);
}

function syncVideos(source, target) {
  if (syncLock || Math.abs(source.currentTime - target.currentTime) <= 0.08) return;
  syncLock = true;
  target.currentTime = source.currentTime;
  syncLock = false;
}

function renderFrameBoxes() {
  const frame = Math.round(rawVideo.currentTime * Math.max(activeClip.fps, 1));
  renderFrameBoxesForFrame(frame);
}

function renderFrameBoxesForFrame(frame) {
  const rows = boxesByFrame.get(frame) || [];
  renderSvg(rawOverlaySvg, rows, "raw");
  renderSvg(adapterOverlaySvg, rows, "adapter");
}

function renderSvg(svg, rows, mode) {
  svg.innerHTML = "";
  rows.forEach((row) => appendBox(svg, row, mode));
}

function appendBox(svg, row, mode) {
  if (mode === "adapter" && row.decision !== "kept") return;
  const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  rect.setAttribute("x", row.x1);
  rect.setAttribute("y", row.y1);
  rect.setAttribute("width", Math.max(row.x2 - row.x1, 1));
  rect.setAttribute("height", Math.max(row.y2 - row.y1, 1));
  rect.classList.add("overlayBox", row.decision);
  rect.classList.toggle("dimmed", selectedTrackId !== null && row.track_id !== selectedTrackId);
  rect.addEventListener("click", () => inspectBox(row));
  svg.appendChild(rect);
}

function inspectBox(row) {
  showDecision({ ...row, box: row, display_label: row.reason || row.stage || row.decision });
}

function updatePlayhead() {
  if (!activeTimeline) return;
  const frame = rawVideo.currentTime * Math.max(activeClip.fps, 1);
  updatePlayheadForFrame(frame);
}

function updatePlayheadForFrame(frame) {
  if (!activeTimeline) return;
  const percent = Math.min(100, Math.max(0, frame / Math.max(activeTimeline.frame_count, 1) * 100));
  playhead.style.left = `${percent}%`;
  timeLabel.textContent = `${(frame / Math.max(activeClip.fps, 1)).toFixed(3)}s · frame ${Math.round(frame)}`;
}

function timelineFrameFromEvent(event) {
  const box = timeContent.getBoundingClientRect();
  const localX = event.clientX - box.left;
  const percent = Math.min(1, Math.max(0, localX / Math.max(box.width, 1)));
  return Math.round(percent * Math.max(activeTimeline.frame_count - 1, 0));
}

function nearestMarker(event) {
  const box = markerCanvas.getBoundingClientRect();
  const localX = event.clientX - box.left;
  const localY = event.clientY - box.top;
  let nearest = null;
  markerPositions.forEach((marker) => {
    const x = (marker.left / 100) * box.width;
    const y = box.height - 8 - marker.lane * 12;
    const distance = Math.hypot(localX - x, localY - y);
    if (distance <= markerHitRadiusPx && (nearest === null || distance < nearest.distance)) {
      nearest = { distance, eventIndex: marker.eventIndex };
    }
  });
  return nearest;
}

function scrollTimelineToFrame(frame) {
  const percent = frame / Math.max(activeTimeline.frame_count, 1);
  const target = percent * timeContent.getBoundingClientRect().width - timeSurface.clientWidth / 2;
  timeSurface.scrollLeft = Math.max(0, target);
}

function applyZoom() {
  timeContent.style.width = `${Number(zoomSlider.value) * 100}%`;
  drawMarkerCanvas();
  updatePlayhead();
}

function bindClipButtons() {
  document.querySelectorAll(".clip").forEach((button) => {
    button.addEventListener("click", () => activateClipButton(button));
  });
}

function activateClipButton(button) {
  document.querySelectorAll(".clip").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  loadClip(story.clips[Number(button.dataset.clipIndex)]);
}

function togglePlayback() {
  if (rawVideo.paused) {
    rawVideo.play();
    adapterVideo.play();
    return;
  }
  rawVideo.pause();
  adapterVideo.pause();
}

function bindTimelinePointerEvents() {
  timeSurface.addEventListener("pointerdown", startScrub);
  timeSurface.addEventListener("pointermove", continueScrub);
  timeSurface.addEventListener("pointerup", finishScrub);
  timeSurface.addEventListener("pointercancel", cancelScrub);
}

function startScrub(event) {
  isScrubbing = true;
  scrubStartX = event.clientX;
  scrubMoved = false;
  timeSurface.setPointerCapture(event.pointerId);
  queueSeekToFrame(timelineFrameFromEvent(event));
}

function continueScrub(event) {
  if (!isScrubbing) return;
  scrubMoved = scrubMoved || Math.abs(event.clientX - scrubStartX) > 3;
  queueSeekToFrame(timelineFrameFromEvent(event));
}

function finishScrub(event) {
  if (!isScrubbing) return;
  isScrubbing = false;
  const marker = scrubMoved ? null : nearestMarker(event);
  if (marker !== null) selectEvent(marker.eventIndex, false);
}

function cancelScrub() {
  isScrubbing = false;
}

function bindWheelZoom() {
  timeSurface.addEventListener("wheel", (event) => {
    event.preventDefault();
    const delta = event.deltaY < 0 ? 0.25 : -0.25;
    zoomSlider.value = String(Math.min(8, Math.max(1, Number(zoomSlider.value) + delta)));
    applyZoom();
  }, { passive: false });
}

function bindVideoEvents() {
  rawVideo.addEventListener("timeupdate", () => {
    syncVideos(rawVideo, adapterVideo);
    updatePlayhead();
    renderFrameBoxes();
  });
  adapterVideo.addEventListener("timeupdate", () => syncVideos(adapterVideo, rawVideo));
}

bindClipButtons();
bindTimelinePointerEvents();
bindWheelZoom();
bindVideoEvents();
window.addEventListener("resize", drawMarkerCanvas);
document.getElementById("playPause").addEventListener("click", togglePlayback);
document.getElementById("prevEvent").addEventListener("click", () => selectEvent(eventIndex - 1, true));
document.getElementById("nextEvent").addEventListener("click", () => selectEvent(eventIndex + 1, true));
zoomSlider.addEventListener("input", applyZoom);
loadClip(activeClip);
