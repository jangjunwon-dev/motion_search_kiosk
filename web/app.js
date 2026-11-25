/* 모션인식 탐색 키오스크 — 화면 쪽 로직 (패스트푸드 비접촉 주문)
 *
 * 화면 흐름: 대기 → 홈(카테고리) → 메뉴 목록(스와이프) → 상세(단품/세트 담기) → 장바구니 → 주문 완료
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
  cart: [],           // [{key, title, emoji, option, price, qty}]
  orderNo: 100 + Math.floor(Math.random() * 800),
  ordered: false,     // 주문 완료 팝업이 떠 있는지
};

const won = (n) => n.toLocaleString("ko-KR") + "원";

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
  // 타일이 4개 이하면 2열로 크게 (멀리서 손으로 가리키기 쉽게)
  grid.style.gridTemplateColumns = `repeat(${state.content.categories.length <= 4 ? 2 : 3}, 1fr)`;
}

/* ------------------------------------------------------------ 화면 전환 */
function show(screen, push = true) {
  if (push && state.screen !== screen && state.screen !== "idle") state.history.push(state.screen);
  state.screen = screen;
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  $("screen-" + screen).classList.add("active");
  updateCartBar();
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
    el.innerHTML = `<div class="emoji">${it.emoji || state.cat.icon}</div><h3>${it.title}</h3><div class="sub">${it.subtitle}</div><div class="body">${it.body}</div>`;
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
  const it = (state.item = state.cat.items[index]);
  $("detail-cat").textContent = `${state.cat.icon} ${state.cat.name}`;
  $("detail-emoji").textContent = it.emoji || state.cat.icon;
  $("detail-title").textContent = it.title;
  $("detail-sub").textContent = it.subtitle;
  $("detail-body").textContent = it.body;
  $("detail-tags").innerHTML = (it.tags || []).map((t) => `<span>#${t}</span>`).join("");
  // 담기 버튼: 세트가 있으면 단품/세트 두 개, 가격만 있으면 하나, 가격 없으면(도움말) 확인
  const box = $("detail-actions");
  if (it.set_price) {
    box.innerHTML = `<button class="target big-btn ghost" data-action="add" data-opt="단품">단품 담기 · ${won(it.price)}</button>`
      + `<button class="target big-btn" data-action="add" data-opt="세트">세트 담기 · ${won(it.set_price)}</button>`;
    $("detail-hint").textContent = `${state.content.set_desc || ""}  ·  👍 엄지를 0.7초 유지하면 단품을 담아요`;
  } else if (it.price) {
    box.innerHTML = `<button class="target big-btn" data-action="add" data-opt="단품">담기 · ${won(it.price)}</button>`;
    $("detail-hint").textContent = "👍 엄지를 0.7초 유지해도 담겨요";
  } else {
    box.innerHTML = `<button class="target big-btn" data-action="back">${it.action || "확인"}</button>`;
    $("detail-hint").textContent = "";
  }
  show("detail");
}

/* ------------------------------------------------------------ 장바구니 */
function cartTotal() { return state.cart.reduce((s, c) => s + c.price * c.qty, 0); }
function cartCount() { return state.cart.reduce((s, c) => s + c.qty, 0); }

function addToCart(item, option) {
  const price = option === "세트" ? item.set_price : item.price;
  const key = `${item.id}:${option}`;
  const line = state.cart.find((c) => c.key === key);
  if (line) line.qty++;
  else state.cart.push({ key, title: item.title, emoji: item.emoji || "", option, price, qty: 1 });
  const name = item.set_price ? `${item.title} ${option}` : item.title;
  toast(`🛒 ${name} 담았어요`);
  updateCartBar(true);
}

function changeQty(key, delta) {
  const line = state.cart.find((c) => c.key === key);
  if (!line) return;
  line.qty += delta;
  if (line.qty <= 0) state.cart = state.cart.filter((c) => c !== line);
  renderCart();
}

function updateCartBar(bump) {
  const bar = $("cartbar");
  const visible = !["idle", "cart"].includes(state.screen);
  bar.classList.toggle("show", visible);
  $("cartbar-text").textContent = state.cart.length
    ? `🛒 ${cartCount()}개 · ${won(cartTotal())}` : "🛒 장바구니가 비어 있어요";
  if (bump) { bar.classList.remove("bump"); void bar.offsetWidth; bar.classList.add("bump"); }
}

function renderCart() {
  const list = $("cart-list");
  list.innerHTML = "";
  if (!state.cart.length) {
    list.innerHTML = `<div class="cart-empty">장바구니가 비어 있어요<br><small>👎 뒤로 가서 메뉴를 담아 주세요</small></div>`;
  }
  state.cart.forEach((c) => {
    const row = document.createElement("div");
    row.className = "cart-row";
    const opt = c.option === "세트" ? `<span class="opt">세트</span>` : "";
    row.innerHTML = `<div class="cart-name">${c.emoji} ${c.title} ${opt}</div>`
      + `<button class="target qty-btn" data-action="dec" data-key="${c.key}">−</button>`
      + `<div class="qty">${c.qty}</div>`
      + `<button class="target qty-btn" data-action="inc" data-key="${c.key}">+</button>`
      + `<div class="cart-price">${won(c.price * c.qty)}</div>`;
    list.appendChild(row);
  });
  $("cart-total").textContent = won(cartTotal());
  $("order-btn").disabled = !state.cart.length;
}

function placeOrder() {
  if (!state.cart.length) return toast("담은 메뉴가 없어요");
  state.orderNo++;
  $("modal-icon").textContent = "✅";
  $("modal-title").textContent = "주문이 접수되었어요";
  $("modal-num").textContent = `주문번호 ${state.orderNo}`;
  $("modal-body").textContent = `${cartCount()}개 · ${won(cartTotal())} — 결제는 카운터에서 (수업용 데모)`;
  $("modal").classList.add("show");
  state.ordered = true;
}

function resetSession() {
  state.cart = [];
  state.history = [];
  state.ordered = false;
}

/* ------------------------------------------------------------ 명령 */
const commands = {
  start() { show("home", false); state.history = []; toast("환영합니다 👋"); },
  "open-cat"(el) { openCategory(el.dataset.id); },
  "open-item"(el) { openItem(Number(el.dataset.index)); },
  add(el) { addToCart(state.item, el ? el.dataset.opt : "단품"); commands.back(); },
  "open-cart"() { renderCart(); show("cart"); },
  inc(el) { changeQty(el.dataset.key, +1); },
  dec(el) { changeQty(el.dataset.key, -1); },
  order() { placeOrder(); },
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
  // 👍 = 지금 화면의 '기본 동작' (대기: 시작, 상세: 단품 담기, 장바구니: 주문, 팝업: 닫기)
  confirm() {
    if ($("modal").classList.contains("show")) return commands["close-modal"]();
    if (state.screen === "idle") return commands.start();
    if (state.screen === "cart") return placeOrder();
    if (state.screen === "detail") {
      if (state.item.price) return commands.add(null);
      return commands.back();
    }
    toast("👍 메뉴 상세 · 장바구니에서 사용할 수 있어요");
  },
  "close-modal"() {
    const wasOrder = state.ordered && $("modal").classList.contains("show");
    $("modal").classList.remove("show");
    if (wasOrder) { resetSession(); show("idle", false); }  // 주문 끝 → 다음 손님
  },
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
    $("modal").classList.remove("show");
    resetSession();        // 손님이 떠나면 장바구니 비우기
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
