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

async function fetchJson(path, options) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || String(res.status));
  }
  if (res.status === 204) return null;
  return res.json();
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
}

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => setTab(btn.dataset.tab));
});

document.getElementById("upcoming-only").addEventListener("change", (e) => {
  upcomingOnly = e.target.checked;
  loadFeed();
});

document.getElementById("compose-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("draft-title").value.trim();
  const body = document.getElementById("draft-body").value;
  if (!title) return;
  const submitBtn = document.getElementById("submit-btn");
  submitBtn.disabled = true;
  hideAlert();
  try {
    await fetchJson("/api/announcements", {
      method: "POST",
      body: JSON.stringify({ title, body }),
    });
    document.getElementById("draft-title").value = "";
    document.getElementById("draft-body").value = "";
    setTab("home");
    await loadFeed();
  } catch (err) {
    showAlert(err instanceof Error ? err.message : "작성 실패");
  } finally {
    submitBtn.disabled = false;
  }
});

loadFeed();
