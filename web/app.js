/* 모션인식 탐색 키오스크 — 화면 쪽 로직
 *
 * 서버(WebSocket /ws)에서 오는 이벤트
 *   cursor {x,y}   : 손 커서 이동 (0~1 정규화)
 *   click          : 가리키다 주먹 → 커서 아래 버튼 클릭
 *   swipe {direction: left|right} : 손바닥 좌우 쓸기 → 페이지 넘김
 *   hold {gesture, progress}      : 👍/👎/✌️ 유지 중 게이지
 *   confirm / back / home         : 유지형 명령 완료
 *   hand_lost                     : 손이 사라짐
 *   status                        : FPS·지연시간 등
 *
 * 카메라·모델이 없어도 개발할 수 있게 마우스·키보드로 같은 동작을 흉내냅니다.
 *   마우스 이동 = 커서, 클릭 = 선택, ←/→ = 스와이프, Enter = 확인, Backspace = 뒤로, H = 처음, P = 카메라 미리보기
 */
"use strict";

const DWELL_MS = 1500;          // 같은 버튼을 이만큼 가리키면 자동 클릭
const IDLE_MS = 45000;          // 입력이 없으면 대기 화면으로
const PER_PAGE = 3;             // 목록 한 페이지 카드 수

const $ = (id) => document.getElementById(id);
const state = {
  content: null,
  screen: "idle",
  cat: null,          // 현재 카테고리
  page: 0,
  item: null,
  cursor: { x: 0.5, y: 0.5, visible: false },
  hoverEl: null,
  hoverSince: 0,
  lastInput: Date.now(),
  history: [],
};

/* ------------------------------------------------------------ 콘텐츠 */
async function loadContent() {
  const res = await fetch("/api/content");
  state.content = await res.json();
  $("kiosk-title").textContent = state.content.title;
  $("kiosk-sub").textContent = state.content.subtitle;
  const grid = $("tile-grid");
  grid.innerHTML = "";
  state.content.categories.forEach((c) => {
    const el = document.createElement("div");
    el.className = "tile target";
    el.dataset.action = "open-cat";
    el.dataset.id = c.id;
    el.innerHTML = `<div class="icon">${c.icon}</div><div><div class="name">${c.name}</div><div class="desc">${c.desc}</div></div>`;
    grid.appendChild(el);
  });
}

/* ------------------------------------------------------------ 화면 전환 */
function show(screen, push = true) {
  if (push && state.screen !== screen && state.screen !== "idle") state.history.push(state.screen);
  state.screen = screen;
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  $("screen-" + screen).classList.add("active");
}

function openCategory(id) {
  state.cat = state.content.categories.find((c) => c.id === id);
  state.page = 0;
  $("list-title").textContent = `${state.cat.icon} ${state.cat.name}`;
  renderList();
  show("list");
}

function pageCount() {
  return Math.max(1, Math.ceil(state.cat.items.length / PER_PAGE));
}

function renderList(slide) {
  const row = $("card-row");
  row.innerHTML = "";
  const start = state.page * PER_PAGE;
  for (let i = 0; i < PER_PAGE; i++) {
    const it = state.cat.items[start + i];
    const el = document.createElement("div");
    if (!it) { el.className = "card empty"; row.appendChild(el); continue; }
    el.className = "card target";
    el.dataset.action = "open-item";
    el.dataset.index = start + i;
    el.innerHTML = `<h3>${it.title}</h3><div class="sub">${it.subtitle}</div><div class="body">${it.body}</div>`;
    row.appendChild(el);
  }
  const pager = $("pager");
  pager.innerHTML = "";
  for (let p = 0; p < pageCount(); p++) {
    const d = document.createElement("i");
    if (p === state.page) d.className = "on";
    pager.appendChild(d);
  }
  if (slide) {
    row.classList.remove("slide-left", "slide-right");
    void row.offsetWidth;
    row.classList.add(slide === "next" ? "slide-left" : "slide-right");
  }
}

function openItem(index) {
  state.item = state.cat.items[index];
  $("detail-cat").textContent = `${state.cat.icon} ${state.cat.name}`;
  $("detail-title").textContent = state.item.title;
  $("detail-sub").textContent = state.item.subtitle;
  $("detail-body").textContent = state.item.body;
  $("detail-tags").innerHTML = (state.item.tags || []).map((t) => `<span>#${t}</span>`).join("");
  $("detail-action").textContent = state.item.action || "확인";
  show("detail");
}

/* ------------------------------------------------------------ 명령 */
const commands = {
  start() { show("home", false); state.history = []; toast("환영합니다 👋"); },
  "open-cat"(el) { openCategory(el.dataset.id); },
  "open-item"(el) { openItem(Number(el.dataset.index)); },
  next() {
    if (state.screen !== "list") return;
    if (state.page < pageCount() - 1) { state.page++; renderList("next"); }
    else toast("마지막 페이지예요");
  },
  prev() {
    if (state.screen !== "list") return;
    if (state.page > 0) { state.page--; renderList("prev"); }
    else toast("첫 페이지예요");
  },
  confirm() {
    if ($("modal").classList.contains("show")) return commands["close-modal"]();
    if (state.screen === "idle") return commands.start();
    if (state.screen !== "detail") return toast("👍 상세 화면에서 사용할 수 있어요");
    $("modal-title").textContent = state.item.action || "완료";
    $("modal-body").textContent = `${state.item.title} — 휴대폰으로 QR을 찍어 주세요 (예시)`;
    $("modal").classList.add("show");
  },
  "close-modal"() { $("modal").classList.remove("show"); },
  back() {
    if ($("modal").classList.contains("show")) return commands["close-modal"]();
    const prev = state.history.pop();
    if (prev) show(prev, false);
    else if (state.screen !== "idle") show("home", false);
  },
  home() {
    commands["close-modal"]();
    state.history = [];
    show("home", false);
    toast("처음 화면");
  },
};

function run(action, el, label) {
  const fn = commands[action];
  if (!fn) return;
  state.lastInput = Date.now();
  if (label) toast(label);
  fn(el);
}

/* ------------------------------------------------------------ 커서 · 클릭 */
function moveCursor(nx, ny) {
  const c = $("cursor");
  state.cursor = { x: nx, y: ny, visible: true };
  const px = nx * window.innerWidth;
  const py = ny * window.innerHeight;
  c.style.left = px + "px";
  c.style.top = py + "px";
  c.classList.add("show");
  state.lastInput = Date.now();
  if (state.screen === "idle") commands.start();
  updateHover(px, py);
}

function targetAt(px, py) {
  const el = document.elementFromPoint(px, py);
  return el ? el.closest(".target") : null;
}

function updateHover(px, py) {
  const t = targetAt(px, py);
  if (t !== state.hoverEl) {
    if (state.hoverEl) state.hoverEl.classList.remove("hover");
    state.hoverEl = t;
    state.hoverSince = performance.now();
    if (t) t.classList.add("hover");
  }
}

function clickAtCursor(source) {
  const el = state.hoverEl;
  const c = $("cursor");
  c.classList.add("click");
  setTimeout(() => c.classList.remove("click"), 150);
  if (!el) return;
  el.classList.add("pressed");
  setTimeout(() => el.classList.remove("pressed"), 150);
  state.hoverSince = performance.now() + 99999; // 클릭 직후 dwell 재발동 방지
  run(el.dataset.action, el);
}

// dwell(가만히 가리키기) 진행 링
function dwellTick() {
  const ring = $("dwell-ring");
  const full = 163.4;
  if (state.hoverEl && state.cursor.visible) {
    const p = Math.min(1, (performance.now() - state.hoverSince) / DWELL_MS);
    ring.style.strokeDashoffset = full * (1 - Math.max(0, p));
    if (p >= 1) clickAtCursor("dwell");
  } else {
    ring.style.strokeDashoffset = full;
  }
  if (Date.now() - state.lastInput > IDLE_MS && state.screen !== "idle") {
    commands["close-modal"]();
    state.history = [];
    show("idle", false);
  }
  requestAnimationFrame(dwellTick);
}

/* ------------------------------------------------------------ 표시 요소 */
let toastTimer = null;
function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 1100);
}

const HOLD_ICON = { like: "👍", dislike: "👎", peace: "✌️" };
let holdTimer = null;
function showHold(gesture, progress) {
  $("hold").classList.add("show");
  $("hold-icon").textContent = HOLD_ICON[gesture] || "✋";
  $("hold-fill").style.width = Math.round(progress * 100) + "%";
  clearTimeout(holdTimer);
  holdTimer = setTimeout(() => $("hold").classList.remove("show"), 300);
}

function highlightGuide(gesture) {
  document.querySelectorAll(".guide .g").forEach((g) => g.classList.toggle("on", g.dataset.g === gesture));
}

function setStatus(s) {
  const dot = $("status-dot");
  if (!s) { dot.className = "dot"; $("status-text").textContent = "서버 연결 끊김 — 재연결 중"; return; }
  dot.className = "dot " + (s.camera ? "on" : "warn");
  const mode = s.camera ? `${s.backend.toUpperCase()} · ${s.fps} FPS · ${s.latency_ms} ms`
                        : "카메라 없음 · 마우스/키보드 모드";
  $("status-text").textContent = mode;
  $("preview-stats").textContent = s.camera ? `${s.fps} FPS · 손 ${s.hands}` : "꺼짐";
  if (s.camera && !state.previewAuto) { state.previewAuto = true; if (!$("preview").classList.contains("show")) togglePreview(); }
  if (s.gesture !== undefined) highlightGuide(s.gesture);
}

/* ------------------------------------------------------------ 서버 이벤트 */
function handleEvent(e) {
  switch (e.type) {
    case "status": setStatus(e); break;
    case "cursor": moveCursor(e.x, e.y); highlightGuide(e.gesture); break;
    case "click": highlightGuide("fist"); clickAtCursor("fist"); break;
    case "swipe":
      highlightGuide("palm");
      // 손을 왼쪽으로 쓸면 다음 페이지 (스마트폰과 같은 방향)
      if (e.direction === "left") run("next", null, "다음 ▶");
      else run("prev", null, "◀ 이전");
      break;
    case "hold": showHold(e.gesture, e.progress); highlightGuide(e.gesture); break;
    case "confirm": highlightGuide("like"); run("confirm", null, "👍 확인"); break;
    case "back": highlightGuide("dislike"); run("back", null, "👎 뒤로"); break;
    case "home": highlightGuide("peace"); run("home", null); break;
    case "hand_lost":
      $("cursor").classList.remove("show");
      state.cursor.visible = false;
      if (state.hoverEl) state.hoverEl.classList.remove("hover");
      state.hoverEl = null;
      highlightGuide(null);
      break;
  }
}

function connect() {
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = (m) => handleEvent(JSON.parse(m.data));
  ws.onclose = () => { setStatus(null); setTimeout(connect, 1500); };
  window._ws = ws;
}

/* ------------------------------------------------------------ 마우스·키보드 (mock) */
window.addEventListener("mousemove", (ev) => moveCursor(ev.clientX / innerWidth, ev.clientY / innerHeight));
window.addEventListener("mousedown", () => clickAtCursor("mouse"));
window.addEventListener("keydown", (ev) => {
  const map = {
    ArrowLeft: () => handleEvent({ type: "swipe", direction: "right" }),
    ArrowRight: () => handleEvent({ type: "swipe", direction: "left" }),
    Enter: () => handleEvent({ type: "confirm" }),
    Backspace: () => handleEvent({ type: "back" }),
    h: () => handleEvent({ type: "home" }),
    p: () => togglePreview(),
  };
  const fn = map[ev.key] || map[ev.key.toLowerCase()];
  if (fn) { ev.preventDefault(); fn(); }
});

function togglePreview() {
  const p = $("preview");
  p.classList.toggle("show");
  $("preview-img").src = p.classList.contains("show") ? "/video" : "";
}

/* ------------------------------------------------------------ 시작 */
loadContent().then(() => {
  connect();
  requestAnimationFrame(dwellTick);
  fetch("/api/status").then((r) => r.json()).then(setStatus);
});
