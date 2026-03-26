const API = "";

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
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
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
  return res.json();
}

async function fetchJsonAdmin(path, options = {}) {
  const t = sessionStorage.getItem("jaegun_admin_token");
  if (!t) {
    throw new Error("더보기 탭에서 관리자 토큰을 저장한 뒤 다시 시도하세요.");
  }
  return fetchJson(path, {
    ...options,
    headers: {
      Authorization: `Bearer ${t}`,
      ...options.headers,
    },
  });
}

function syncAdminFormsVisibility() {
  const el = document.getElementById("admin-forms");
  const t = sessionStorage.getItem("jaegun_admin_token");
  el.hidden = !t;
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
            ${ev.description ? `<p style="margin:0.5rem 0 0;font-size:0.875rem;color:#57534e;line-height:1.5">${escapeHtml(ev.description)}</p>` : ""}
          </div>
        `;
        evUl.appendChild(li);
      }
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
    syncAdminFormsVisibility();
    const saved = sessionStorage.getItem("jaegun_admin_token");
    if (saved) document.getElementById("admin-token").value = saved;
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
        li.innerHTML = `
          <div class="card-meta">${fmtDateTime(p.created_at)}${author}</div>
          <h4>${escapeHtml(p.title)}</h4>
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

document.getElementById("admin-token-save").addEventListener("click", () => {
  const v = document.getElementById("admin-token").value.trim();
  if (v) sessionStorage.setItem("jaegun_admin_token", v);
  else sessionStorage.removeItem("jaegun_admin_token");
  syncAdminFormsVisibility();
  const hint = document.getElementById("admin-token-hint");
  hint.textContent = v
    ? "저장됨. 아래에서 공식 공지·일정을 등록할 수 있습니다."
    : "토큰을 지웠습니다.";
});

document.getElementById("admin-announce-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("admin-a-title").value.trim();
  const body = document.getElementById("admin-a-body").value;
  if (!title) return;
  hideAlert();
  try {
    await fetchJsonAdmin("/api/announcements", {
      method: "POST",
      body: JSON.stringify({ title, body }),
    });
    document.getElementById("admin-a-title").value = "";
    document.getElementById("admin-a-body").value = "";
    setTab("home");
    await loadFeed();
  } catch (err) {
    showAlert(err instanceof Error ? err.message : "공지 등록 실패");
  }
});

document.getElementById("admin-event-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("admin-e-title").value.trim();
  const dt = document.getElementById("admin-e-starts").value;
  const location = document.getElementById("admin-e-loc").value.trim();
  const description = document.getElementById("admin-e-desc").value;
  if (!title || !dt) return;
  const starts_at = new Date(dt).toISOString();
  hideAlert();
  try {
    await fetchJsonAdmin("/api/events", {
      method: "POST",
      body: JSON.stringify({
        title,
        starts_at,
        location,
        description,
      }),
    });
    document.getElementById("admin-e-title").value = "";
    document.getElementById("admin-e-starts").value = "";
    document.getElementById("admin-e-loc").value = "";
    document.getElementById("admin-e-desc").value = "";
    setTab("events");
    await loadFeed();
  } catch (err) {
    showAlert(err instanceof Error ? err.message : "일정 등록 실패");
  }
});

syncAdminFormsVisibility();
loadFeed();
