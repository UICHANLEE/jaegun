const API = "";
const ACCESS_TOKEN_KEY = "jaegun_access_token";

function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY) || "";
}

function showAlert(msg) {
  const el = document.getElementById("alert");
  el.textContent = msg;
  el.hidden = false;
}

function hideAlert() {
  const el = document.getElementById("alert");
  el.hidden = true;
  el.textContent = "";
}

function fmtDateTime(iso) {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

function fmtDateOnly(iso) {
  return new Intl.DateTimeFormat("ko-KR", {
    weekday: "short",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

async function fetchJson(path, options = {}) {
  const headers = { Accept: "application/json", ...options.headers };
  const t = getAccessToken();
  if (t) headers.Authorization = `Bearer ${t}`;
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers["Content-Type"]
  ) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    let msg = await res.text();
    try {
      const j = JSON.parse(msg);
      if (j.detail) msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* raw text */
    }
    throw new Error(msg || String(res.status));
  }
  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

function refreshLoginHint() {
  const h = document.getElementById("profile-hint");
  if (!h) return;
  h.hidden = !!getAccessToken();
}

let upcomingOnly = true;

async function loadFeed() {
  hideAlert();
  document.getElementById("home-loading").hidden = false;
  document.getElementById("announcement-list").hidden = true;
  document.getElementById("announcement-empty").hidden = true;
  document.getElementById("events-loading").hidden = false;
  document.getElementById("event-list").hidden = true;
  document.getElementById("event-empty").hidden = true;

  try {
    const [announcements, events] = await Promise.all([
      fetchJson("/api/announcements"),
      fetchJson(`/api/events?upcoming_only=${upcomingOnly ? "true" : "false"}`),
    ]);

    document.getElementById("home-loading").hidden = true;
    const ul = document.getElementById("announcement-list");
    ul.innerHTML = "";
    if (!announcements.length) {
      document.getElementById("announcement-empty").hidden = false;
    } else {
      ul.hidden = false;
      for (const a of announcements) {
        const li = document.createElement("li");
        li.className = "card";
        li.innerHTML = `
          <div class="card-meta">${fmtDateTime(a.created_at)}</div>
          <h4>${escapeHtml(a.title)}</h4>
          ${a.body ? `<div class="card-body">${escapeHtml(a.body)}</div>` : ""}
        `;
        ul.appendChild(li);
      }
    }

    document.getElementById("events-loading").hidden = true;
    const evUl = document.getElementById("event-list");
    evUl.innerHTML = "";
    if (!events.length) {
      document.getElementById("event-empty").hidden = false;
    } else {
      evUl.hidden = false;
      for (const ev of events) {
        const d = new Date(ev.starts_at);
        const li = document.createElement("li");
        li.className = "card event-row";
        li.innerHTML = `
          <div class="event-date">
            <span class="mo">${new Intl.DateTimeFormat("ko-KR", { month: "short" }).format(d)}</span>
            <span class="day">${d.getDate()}</span>
          </div>
          <div style="min-width:0;flex:1">
            <h4 style="margin:0;font-size:1rem">${escapeHtml(ev.title)}</h4>
            <p style="margin:0.25rem 0 0;font-size:0.75rem;color:#78716c">${fmtDateOnly(ev.starts_at)}</p>
            ${ev.location ? `<p style="margin:0.25rem 0 0;font-size:0.75rem">📍 ${escapeHtml(ev.location)}</p>` : ""}
            <button type="button" class="event-detail-btn" data-open-event="${ev.id}">일정 상세 · 설문 · 번호 발급</button>
          </div>
        `;
        evUl.appendChild(li);
      }
      evUl.querySelectorAll("[data-open-event]").forEach((btn) => {
        btn.addEventListener("click", () => openEventModal(btn.getAttribute("data-open-event")));
      });
    }
  } catch (e) {
    showAlert(
      e instanceof Error
        ? e.message
        : "API에 연결할 수 없습니다. `uv run uvicorn jaegun.main:app`으로 서버를 실행했는지 확인하세요."
    );
    document.getElementById("home-loading").hidden = true;
    document.getElementById("events-loading").hidden = true;
  }
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function normalizeUrl(u) {
  const t = (u || "").trim();
  if (!t) return "";
  if (/^https?:\/\//i.test(t)) return t;
  return `https://${t.replace(/^\/+/, "")}`;
}

let currentEventId = null;

function closeEventModal() {
  document.getElementById("event-modal").hidden = true;
  const out = document.getElementById("event-modal-ticket-result");
  out.hidden = true;
  out.textContent = "";
  currentEventId = null;
}

async function openEventModal(eventId) {
  currentEventId = eventId;
  hideAlert();
  const modal = document.getElementById("event-modal");
  try {
    const ev = await fetchJson(`/api/events/${eventId}`);
    document.getElementById("event-modal-title").textContent = ev.title;
    let meta = fmtDateOnly(ev.starts_at);
    if (ev.location) meta += ` · ${ev.location}`;
    document.getElementById("event-modal-meta").textContent = meta;
    const bodyEl = document.getElementById("event-modal-body");
    bodyEl.textContent = ev.description?.trim()
      ? ev.description
      : "등록된 상세 설명이 없습니다.";
    const survey = document.getElementById("event-modal-survey");
    const link = document.getElementById("event-modal-survey-link");
    const heading = survey.querySelector(".event-modal-survey-heading");
    const url = normalizeUrl(ev.survey_url || "");
    if (url) {
      survey.hidden = false;
      heading.textContent = ev.survey_label || "참석 여부 설문조사";
      link.href = url;
    } else {
      survey.hidden = true;
    }
    document.getElementById("event-modal-ticket-result").hidden = true;
    document.getElementById("event-modal-ticket-result").textContent = "";
    const needLogin = document.getElementById("event-modal-need-login");
    if (needLogin) needLogin.hidden = !!getAccessToken();
    modal.hidden = false;
  } catch (e) {
    showAlert(e instanceof Error ? e.message : "일정을 불러오지 못했습니다.");
  }
}

document.getElementById("event-modal")?.addEventListener("click", (e) => {
  if (e.target.closest("[data-close-modal]")) closeEventModal();
});

document.getElementById("event-modal-issue-btn")?.addEventListener("click", async () => {
  if (!currentEventId) return;
  if (!getAccessToken()) {
    window.alert("번호 발급은 로그인 후에만 가능합니다. 회원가입 또는 로그인해 주세요.");
    return;
  }
  const btn = document.getElementById("event-modal-issue-btn");
  const out = document.getElementById("event-modal-ticket-result");
  btn.disabled = true;
  hideAlert();
  try {
    const r = await fetchJson(`/api/events/${currentEventId}/tickets`, {
      method: "POST",
    });
    out.hidden = false;
    out.textContent = `발급 번호: ${r.sequence_number}`;
  } catch (e) {
    const msg = e instanceof Error ? e.message : "번호 발급에 실패했습니다.";
    if (msg.includes("이미 이 일정에서 번호") || msg.includes("409")) {
      window.alert(msg);
    } else {
      showAlert(msg);
    }
  } finally {
    btn.disabled = false;
  }
});

const MONTH_LABELS = [
  "1월",
  "2월",
  "3월",
  "4월",
  "5월",
  "6월",
  "7월",
  "8월",
  "9월",
  "10월",
  "11월",
  "12월",
];

let planSubTab = "annual";
let planYear = new Date().getFullYear();
let selectedAnnualYear = planYear;
let annualList = [];
let monthlyList = [];

function fmtPlanUpdated(iso) {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

function setTab(tab) {
  document.querySelectorAll(".tab-panel").forEach((p) => {
    p.hidden = p.id !== `panel-${tab}`;
  });
  document.querySelectorAll(".nav-btn").forEach((b) => {
    const active = b.dataset.tab === tab;
    b.classList.toggle("active", active);
    if (active) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  if (tab === "plans") {
    void loadPlans();
  }
  if (tab === "board") {
    void loadBoard();
  }
  if (tab === "more") {
    refreshLoginHint();
    void loadSocialPanels();
  }
}

async function loadBoard() {
  hideAlert();
  document.getElementById("board-loading").hidden = false;
  document.getElementById("board-list").hidden = true;
  document.getElementById("board-empty").hidden = true;
  try {
    const posts = await fetchJson("/api/board/posts");
    document.getElementById("board-loading").hidden = true;
    const ul = document.getElementById("board-list");
    ul.innerHTML = "";
    if (!posts.length) {
      document.getElementById("board-empty").hidden = false;
    } else {
      ul.hidden = false;
      for (const p of posts) {
        const li = document.createElement("li");
        li.className = "card";
        const author = p.author_name ? ` · ${escapeHtml(p.author_name)}` : "";
        const kind =
          p.kind === "user_meeting"
            ? ` <span class="muted" style="font-size:0.75rem">(소모임 공유)</span>`
            : "";
        li.innerHTML = `
          <div class="card-meta">${fmtDateTime(p.created_at)}${author}</div>
          <h4>${escapeHtml(p.title)}${kind}</h4>
          ${p.body ? `<div class="card-body">${escapeHtml(p.body)}</div>` : ""}
        `;
        ul.appendChild(li);
      }
    }
  } catch (e) {
    showAlert(e instanceof Error ? e.message : "게시판을 불러오지 못했습니다.");
    document.getElementById("board-loading").hidden = true;
  }
}

async function loadPlans() {
  hideAlert();
  const loading = document.getElementById("plans-loading");
  loading.hidden = false;
  document.getElementById("plan-annual-wrap").hidden = true;
  document.getElementById("plan-monthly-wrap").hidden = true;
  try {
    annualList = await fetchJson("/api/plans/annual");
    monthlyList = await fetchJson(`/api/plans/monthly?year=${planYear}`);
    if (annualList.length) {
      const years = annualList.map((a) => a.year);
      if (!years.includes(selectedAnnualYear)) {
        selectedAnnualYear = Math.max(...years);
      }
    }
    renderPlanPanels();
  } catch (e) {
    showAlert(
      e instanceof Error ? e.message : "계획을 불러오지 못했습니다."
    );
  } finally {
    loading.hidden = true;
  }
}

function renderPlanPanels() {
  document.getElementById("plan-annual-wrap").hidden = planSubTab !== "annual";
  document.getElementById("plan-monthly-wrap").hidden = planSubTab !== "monthly";
  if (planSubTab === "annual") renderAnnual();
  else renderMonthly();
}

function renderAnnual() {
  const wrap = document.getElementById("plan-annual-wrap");
  wrap.hidden = false;
  if (!annualList.length) {
    wrap.innerHTML = '<p class="empty">등록된 연간 계획이 없습니다.</p>';
    return;
  }
  const years = [...new Set(annualList.map((a) => a.year))].sort((a, b) => b - a);
  if (!years.includes(selectedAnnualYear)) {
    selectedAnnualYear = years[0];
  }
  const item = annualList.find((a) => a.year === selectedAnnualYear);
  if (!item) {
    wrap.innerHTML = '<p class="empty">해당 연도 계획을 찾을 수 없습니다.</p>';
    return;
  }
  const yearOpts = years
    .map(
      (y) =>
        `<option value="${y}" ${y === selectedAnnualYear ? "selected" : ""}>${y}년</option>`
    )
    .join("");
  wrap.innerHTML = `
    <div class="plan-toolbar">
      <label>연도 <select id="annual-year-select">${yearOpts}</select></label>
    </div>
    <div class="card">
      <h4 style="margin:0;font-size:1rem">${escapeHtml(item.title)}</h4>
      <p class="card-meta">${fmtPlanUpdated(item.updated_at)}</p>
      <div class="plan-body-text">${escapeHtml(item.body)}</div>
    </div>
  `;
  document.getElementById("annual-year-select").addEventListener("change", (e) => {
    selectedAnnualYear = Number(e.target.value);
    renderAnnual();
  });
}

function renderMonthly() {
  const wrap = document.getElementById("plan-monthly-wrap");
  wrap.hidden = false;
  const byMonth = new Map(monthlyList.map((m) => [m.month, m]));
  const y0 = new Date().getFullYear();
  const yearMin = y0 - 2;
  const yearMax = y0 + 3;
  let yearOpts = "";
  for (let y = yearMin; y <= yearMax; y++) {
    yearOpts += `<option value="${y}" ${y === planYear ? "selected" : ""}>${y}년</option>`;
  }
  let grid = "";
  for (let m = 1; m <= 12; m++) {
    const row = byMonth.get(m);
    grid += `
      <div class="card month-card ${row ? "" : "muted"}">
        <h4 style="margin:0;font-size:0.9rem">${MONTH_LABELS[m - 1]}</h4>
        ${
          row
            ? `
          <p style="margin:0.35rem 0 0;font-size:0.85rem;font-weight:600">${escapeHtml(row.title)}</p>
          <p class="card-meta">${fmtPlanUpdated(row.updated_at)}</p>
          <div class="plan-body-text" style="margin-top:0.5rem;font-size:0.8rem">${escapeHtml(row.body)}</div>
        `
            : `<p class="muted" style="margin:0.35rem 0 0;font-size:0.8rem">등록된 계획 없음</p>`
        }
      </div>
    `;
  }
  wrap.innerHTML = `
    <div class="plan-toolbar">
      <label>연도 <select id="monthly-year-select">${yearOpts}</select></label>
    </div>
    <div class="month-grid">${grid}</div>
  `;
  document.getElementById("monthly-year-select").addEventListener("change", async (e) => {
    planYear = Number(e.target.value);
    document.getElementById("plans-loading").hidden = false;
    hideAlert();
    try {
      monthlyList = await fetchJson(`/api/plans/monthly?year=${planYear}`);
      renderMonthly();
    } catch (err) {
      showAlert(err instanceof Error ? err.message : "불러오기 실패");
    } finally {
      document.getElementById("plans-loading").hidden = true;
    }
  });
}

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => setTab(btn.dataset.tab));
});

document.querySelectorAll("[data-plan-sub]").forEach((btn) => {
  btn.addEventListener("click", () => {
    planSubTab = btn.dataset.planSub;
    document.querySelectorAll("[data-plan-sub]").forEach((b) => {
      const on = b.dataset.planSub === planSubTab;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    renderPlanPanels();
  });
});

document.getElementById("upcoming-only").addEventListener("change", (e) => {
  upcomingOnly = e.target.checked;
  loadFeed();
});

document.getElementById("board-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("board-title").value.trim();
  const body = document.getElementById("board-body").value;
  const author_name = document.getElementById("board-author").value.trim();
  if (!title) return;
  const btn = document.getElementById("board-submit");
  btn.disabled = true;
  hideAlert();
  try {
    await fetchJson("/api/board/posts", {
      method: "POST",
      body: JSON.stringify({ title, body, author_name }),
    });
    document.getElementById("board-title").value = "";
    document.getElementById("board-body").value = "";
    await loadBoard();
  } catch (err) {
    showAlert(err instanceof Error ? err.message : "등록 실패");
  } finally {
    btn.disabled = false;
  }
});

async function loadSocialPanels() {
  const inc = document.getElementById("incoming-friends");
  const fl = document.getElementById("friends-list");
  if (!inc || !fl) return;
  if (!getAccessToken()) {
    inc.innerHTML = "";
    fl.innerHTML = '<p class="muted">로그인 후 친구·쪽지를 사용할 수 있습니다.</p>';
    return;
  }
  try {
    const incoming = await fetchJson("/api/friends/incoming");
    if (!incoming.length) {
      inc.innerHTML = '<p class="muted" style="margin:0">대기 중인 요청이 없습니다.</p>';
    } else {
      inc.innerHTML = incoming
        .map(
          (r) => `
        <div class="card" style="padding:0.65rem;margin-bottom:0.5rem">
          <strong>${escapeHtml(r.from_display_name || "회원")}</strong> 님이 친구 요청
          <div style="margin-top:0.4rem;display:flex;gap:0.35rem">
            <button type="button" class="event-detail-btn btn-accept-friend" data-req="${r.id}">수락</button>
            <button type="button" class="event-detail-btn" style="background:#78716c" data-reject="${r.id}">거절</button>
          </div>
        </div>`
        )
        .join("");
      inc.querySelectorAll(".btn-accept-friend").forEach((b) => {
        b.addEventListener("click", async () => {
          await fetchJson(`/api/friends/${b.getAttribute("data-req")}/accept`, { method: "POST" });
          await loadSocialPanels();
        });
      });
      inc.querySelectorAll("[data-reject]").forEach((b) => {
        b.addEventListener("click", async () => {
          await fetchJson(`/api/friends/${b.getAttribute("data-reject")}/reject`, { method: "POST" });
          await loadSocialPanels();
        });
      });
    }
  } catch {
    inc.innerHTML = '<p class="muted">요청 목록을 불러오지 못했습니다.</p>';
  }
  try {
    const friends = await fetchJson("/api/friends");
    if (!friends.length) {
      fl.innerHTML = '<p class="muted" style="margin:0">아직 친한 친구가 없습니다. 전화번호로 요청해 보세요.</p>';
    } else {
      fl.innerHTML = friends
        .map(
          (u) => `
        <div class="card" style="padding:0.65rem;margin-bottom:0.5rem">
          <strong>${escapeHtml(u.display_name)}</strong>
          <button type="button" class="event-detail-btn btn-msg-peer" style="margin-top:0.35rem" data-peer="${u.id}">쪽지 보내기</button>
        </div>`
        )
        .join("");
      fl.querySelectorAll(".btn-msg-peer").forEach((b) => {
        b.addEventListener("click", () => openPeerChat(b.getAttribute("data-peer")));
      });
    }
  } catch {
    fl.innerHTML = '<p class="muted">친구 목록을 불러오지 못했습니다.</p>';
  }
}

async function openPeerChat(peerId) {
  if (!peerId || !getAccessToken()) return;
  try {
    const msgs = await fetchJson(`/api/messages/${peerId}?limit=50`);
    const pid = String(peerId);
    const lines = msgs.map((m) => `${String(m.sender_id) === pid ? "상대" : "나"}: ${m.body}`).join("\n");
    window.alert(lines || "(아직 대화 없음)");
  } catch (e) {
    window.alert(e instanceof Error ? e.message : "대화를 불러오지 못했습니다.");
    return;
  }
  const body = window.prompt("보낼 메시지를 입력하세요.");
  if (body == null || !body.trim()) return;
  try {
    await fetchJson("/api/messages", {
      method: "POST",
      body: JSON.stringify({ to_user_id: String(peerId), body: body.trim() }),
    });
    window.alert("보냈습니다.");
  } catch (e) {
    window.alert(e instanceof Error ? e.message : "전송 실패");
  }
}

document.getElementById("friend-request-btn")?.addEventListener("click", async () => {
  const phone = document.getElementById("friend-phone")?.value?.trim();
  if (!phone) {
    showAlert("전화번호를 입력하세요.");
    return;
  }
  hideAlert();
  try {
    await fetchJson(`/api/friends/request-by-phone?phone=${encodeURIComponent(phone)}`, {
      method: "POST",
    });
    showAlert("친구 요청을 보냈습니다.");
    document.getElementById("friend-phone").value = "";
    await loadSocialPanels();
  } catch (e) {
    showAlert(e instanceof Error ? e.message : "요청 실패");
  }
});

document.getElementById("meeting-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!getAccessToken()) {
    showAlert("로그인이 필요합니다.");
    return;
  }
  const title = document.getElementById("meet-title").value.trim();
  const body = document.getElementById("meet-body").value;
  const starts = document.getElementById("meet-starts").value;
  const location = document.getElementById("meet-loc").value.trim();
  const share = document.getElementById("meet-share").checked;
  if (!title) return;
  hideAlert();
  const btn = document.getElementById("meet-submit");
  btn.disabled = true;
  try {
    const payload = {
      title,
      body,
      location,
      share_to_board: share,
    };
    if (starts) payload.starts_at = new Date(starts).toISOString();
    await fetchJson("/api/meetings", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showAlert("소모임을 등록했습니다. 게시판 공유를 선택했다면 게시판 탭에서 확인할 수 있습니다.");
    e.target.reset();
  } catch (err) {
    showAlert(err instanceof Error ? err.message : "등록 실패");
  } finally {
    btn.disabled = false;
  }
});

refreshLoginHint();
loadFeed();
