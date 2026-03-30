/**
 * Jaegun 관리자 UI — `/admin/` 정적 페이지
 * 토큰: sessionStorage `jaegun_admin_token`
 */

const TOKEN_KEY = "jaegun_admin_token";

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY) || "";
}

function setToken(value) {
  if (value) sessionStorage.setItem(TOKEN_KEY, value);
  else sessionStorage.removeItem(TOKEN_KEY);
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

function showAlert(msg, isError) {
  const el = document.getElementById("alert");
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    el.classList.remove("alert-error", "alert-ok");
    return;
  }
  el.hidden = false;
  el.textContent = msg;
  el.classList.toggle("alert-error", !!isError);
  el.classList.toggle("alert-ok", !isError);
}

async function fetchJson(url, opts = {}) {
  const res = await fetch(url, {
    ...opts,
    headers: {
      Accept: "application/json",
      ...(opts.body && typeof opts.body === "string"
        ? { "Content-Type": "application/json" }
        : {}),
      ...opts.headers,
    },
  });
  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail =
      data && typeof data === "object" && data.detail != null
        ? typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail)
        : text || res.statusText;
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return data;
}

async function fetchAdmin(url, opts = {}) {
  const token = getToken().trim();
  if (!token) throw new Error("관리자 토큰을 먼저 저장하세요.");
  return fetchJson(url, {
    ...opts,
    headers: {
      Authorization: `Bearer ${token}`,
      ...opts.headers,
    },
  });
}

function formatDt(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" });
}

async function loadAdminOrgSelects() {
  const aOrg = document.getElementById("a-org");
  const eOrg = document.getElementById("e-org");
  if (!aOrg || !eOrg) return;
  let orgs = [];
  try {
    orgs = await fetchJson("/api/orgs");
  } catch {
    return;
  }
  const fill = (sel, emptyLabel) => {
    sel.innerHTML = "";
    sel.appendChild(new Option(emptyLabel, ""));
    for (const o of orgs) {
      sel.appendChild(new Option(`${o.name} (${o.kind})`, o.id));
    }
  };
  fill(aOrg, "전체 공지 (소속 없음)");
  fill(eOrg, "전체 일정 (소속 없음)");
}

async function loadDashboard() {
  const summary = document.getElementById("dash-summary");
  try {
    const [ann, ev, posts, annual] = await Promise.all([
      fetchJson("/api/announcements?limit=200"),
      fetchJson("/api/events?upcoming_only=false&limit=200"),
      fetchJson("/api/board/posts?limit=200"),
      fetchJson("/api/plans/annual"),
    ]);
    const y = new Date().getFullYear();
    let monthlyCount = 0;
    try {
      const monthly = await fetchJson(`/api/plans/monthly?year=${y}`);
      monthlyCount = Array.isArray(monthly) ? monthly.length : 0;
    } catch {
      monthlyCount = 0;
    }
    let bmText = "";
    try {
      const tok = getToken().trim();
      if (tok) {
        const bm = await fetchAdmin("/admin/big-meeting/tickets");
        bmText = ` · 큰모임 번호 ${Array.isArray(bm) ? bm.length : 0}명`;
      }
    } catch {
      /* 토큰 없으면 생략 */
    }
    summary.textContent = `공지 ${ann.length}건 · 일정 ${ev.length}건 · 게시글 ${posts.length}건 · 연간 계획 ${annual.length}년 · 올해(${y}) 월간 ${monthlyCount}건${bmText}`;
  } catch (e) {
    summary.textContent = `불러오기 실패: ${e.message}`;
  }
}

async function loadAnnouncements() {
  const loading = document.getElementById("announce-loading");
  const list = document.getElementById("announce-list");
  const empty = document.getElementById("announce-empty");
  loading.textContent = "불러오는 중…";
  loading.hidden = false;
  list.hidden = true;
  empty.hidden = true;
  try {
    const rows = await fetchJson("/api/announcements?limit=200");
    loading.hidden = true;
    if (!rows.length) {
      empty.hidden = false;
      return;
    }
    list.hidden = false;
    list.innerHTML = rows
      .map(
        (a) => `
      <li class="item-row">
        <div class="item-main">
          <strong>${escapeHtml(a.title)}</strong>
          <span class="item-meta">${formatDt(a.created_at)}${a.organization_id ? ` · org ${escapeHtml(String(a.organization_id).slice(0, 8))}…` : ""}</span>
        </div>
        <button type="button" class="btn-danger btn-small" data-del-announce="${a.id}">삭제</button>
      </li>`
      )
      .join("");
    list.querySelectorAll("[data-del-announce]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("이 공지를 삭제할까요?")) return;
        try {
          await fetchAdmin(`/admin/announcements/${btn.dataset.delAnnounce}`, { method: "DELETE" });
          showAlert("삭제했습니다.", false);
          loadAnnouncements();
          loadDashboard();
        } catch (e) {
          showAlert(e.message, true);
        }
      });
    });
  } catch (e) {
    loading.textContent = `오류: ${e.message}`;
  }
}

async function loadEvents() {
  const loading = document.getElementById("events-loading");
  const list = document.getElementById("event-list");
  const empty = document.getElementById("event-empty");
  loading.textContent = "불러오는 중…";
  loading.hidden = false;
  list.hidden = true;
  empty.hidden = true;
  try {
    const rows = await fetchJson("/api/events?upcoming_only=false&limit=200");
    loading.hidden = true;
    if (!rows.length) {
      empty.hidden = false;
      return;
    }
    list.hidden = false;
    list.innerHTML = rows
      .map(
        (ev) => `
      <li class="item-row event-admin-item" style="flex-wrap:wrap">
        <div class="item-main" style="min-width:12rem;flex:1">
          <strong>${escapeHtml(ev.title)}</strong>
          <span class="item-meta">${formatDt(ev.starts_at)}${ev.location ? ` · ${escapeHtml(ev.location)}` : ""}${ev.organization_id ? ` · org ${escapeHtml(String(ev.organization_id).slice(0, 8))}…` : ""}</span>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:0.35rem;align-items:center">
          <button type="button" class="btn-secondary btn-small" data-tickets-event="${ev.id}">발급 목록</button>
          <button type="button" class="btn-danger btn-small" data-del-event="${ev.id}">삭제</button>
        </div>
        <ul class="admin-ticket-list muted" id="admin-tickets-${ev.id}" hidden style="width:100%;margin:0.35rem 0 0;padding-left:1.1rem;font-size:0.8rem;list-style:disc"></ul>
      </li>`
      )
      .join("");
    list.querySelectorAll("[data-tickets-event]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-tickets-event");
        const ul = document.getElementById(`admin-tickets-${id}`);
        if (!ul) return;
        if (!ul.hidden && ul.dataset.loaded === "1") {
          ul.hidden = true;
          return;
        }
        try {
          const tickets = await fetchAdmin(`/admin/events/${id}/tickets`);
          ul.hidden = false;
          ul.dataset.loaded = "1";
          if (!tickets.length) {
            ul.innerHTML = `<li>아직 발급된 번호가 없습니다.</li>`;
            return;
          }
          ul.innerHTML = tickets
            .map((t) => {
              const age =
                t.participant_age != null && t.participant_age !== ""
                  ? `${t.participant_age}세`
                  : "—";
              const ch = t.participant_church ? escapeHtml(t.participant_church) : "—";
              const nm = t.participant_name ? escapeHtml(t.participant_name) : "(이름 없음)";
              const phone = t.member_phone ? escapeHtml(String(t.member_phone)) : "—";
              const gen = t.member_gender ? escapeHtml(t.member_gender) : "—";
              const memNm = t.member_display_name ? escapeHtml(t.member_display_name) : "";
              const memLine = t.user_id
                ? `<br /><span class="item-meta">회원: ${memNm || "—"} · 전화 ${phone} · 성별 ${gen}</span>`
                : "";
              return `<li><strong>#${t.sequence_number}</strong> ${nm} · ${age} · ${ch}${memLine}<br /><span class="item-meta">${formatDt(t.created_at)}</span></li>`;
            })
            .join("");
        } catch (e) {
          showAlert(e.message, true);
        }
      });
    });
    list.querySelectorAll("[data-del-event]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("이 일정을 삭제할까요?")) return;
        try {
          await fetchAdmin(`/admin/events/${btn.dataset.delEvent}`, { method: "DELETE" });
          showAlert("삭제했습니다.", false);
          loadEvents();
          loadDashboard();
        } catch (e) {
          showAlert(e.message, true);
        }
      });
    });
  } catch (e) {
    loading.textContent = `오류: ${e.message}`;
  }
}

async function loadAnnualPlans() {
  const loading = document.getElementById("annual-loading");
  const list = document.getElementById("annual-list");
  loading.textContent = "목록 불러오는 중…";
  loading.hidden = false;
  list.hidden = true;
  try {
    const rows = await fetchJson("/api/plans/annual");
    loading.hidden = true;
    if (!rows.length) {
      list.innerHTML = "";
      list.hidden = false;
      list.innerHTML = `<li class="item-row muted">등록된 연간 계획이 없습니다.</li>`;
      return;
    }
    list.hidden = false;
    list.innerHTML = rows
      .map(
        (p) => `
      <li class="item-row">
        <div class="item-main">
          <strong>${p.year}년</strong> — ${escapeHtml(p.title)}
        </div>
        <button type="button" class="btn-danger btn-small" data-del-annual="${p.year}">삭제</button>
      </li>`
      )
      .join("");
    list.querySelectorAll("[data-del-annual]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm(`${btn.dataset.delAnnual}년 연간 계획을 삭제할까요?`)) return;
        try {
          await fetchAdmin(`/admin/plans/annual/${btn.dataset.delAnnual}`, { method: "DELETE" });
          showAlert("삭제했습니다.", false);
          loadAnnualPlans();
          loadDashboard();
        } catch (e) {
          showAlert(e.message, true);
        }
      });
    });
  } catch (e) {
    loading.textContent = `오류: ${e.message}`;
  }
}

function monthlyListYear() {
  const inp = document.getElementById("mo-list-year");
  const y = parseInt(inp.value, 10);
  if (Number.isFinite(y) && y >= 2000 && y <= 2100) return y;
  return new Date().getFullYear();
}

async function loadMonthlyPlans() {
  const loading = document.getElementById("monthly-loading");
  const list = document.getElementById("monthly-list");
  const empty = document.getElementById("monthly-empty");
  const year = monthlyListYear();
  loading.textContent = "불러오는 중…";
  loading.hidden = false;
  list.hidden = true;
  empty.hidden = true;
  try {
    const rows = await fetchJson(`/api/plans/monthly?year=${year}`);
    loading.hidden = true;
    if (!rows.length) {
      empty.hidden = false;
      return;
    }
    list.hidden = false;
    list.innerHTML = rows
      .map(
        (p) => `
      <li class="item-row">
        <div class="item-main">
          <strong>${p.year}년 ${p.month}월</strong> — ${escapeHtml(p.title)}
        </div>
        <button type="button" class="btn-danger btn-small" data-del-monthly="${p.year}-${p.month}">삭제</button>
      </li>`
      )
      .join("");
    list.querySelectorAll("[data-del-monthly]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const [yy, mm] = btn.dataset.delMonthly.split("-");
        if (!confirm(`${yy}년 ${mm}월 계획을 삭제할까요?`)) return;
        try {
          await fetchAdmin(`/admin/plans/monthly/${yy}/${mm}`, { method: "DELETE" });
          showAlert("삭제했습니다.", false);
          loadMonthlyPlans();
          loadDashboard();
        } catch (e) {
          showAlert(e.message, true);
        }
      });
    });
  } catch (e) {
    loading.textContent = `오류: ${e.message}`;
  }
}

async function loadBigMeetingTickets() {
  const loading = document.getElementById("bigmeet-loading");
  const list = document.getElementById("bigmeet-list");
  const empty = document.getElementById("bigmeet-empty");
  if (!loading || !list) return;
  loading.textContent = "불러오는 중…";
  loading.hidden = false;
  list.hidden = true;
  empty.hidden = true;
  try {
    const tickets = await fetchAdmin("/admin/big-meeting/tickets");
    loading.hidden = true;
    if (!tickets.length) {
      empty.hidden = false;
      return;
    }
    list.hidden = false;
    list.innerHTML = tickets
      .map((t) => {
        const age =
          t.participant_age != null && t.participant_age !== ""
            ? `${t.participant_age}세`
            : "—";
        const ch = t.participant_church ? escapeHtml(t.participant_church) : "—";
        const nm = t.participant_name ? escapeHtml(t.participant_name) : "(이름 없음)";
        const phone = t.member_phone ? escapeHtml(String(t.member_phone)) : "—";
        const gen = t.member_gender ? escapeHtml(t.member_gender) : "—";
        const memNm = t.member_display_name ? escapeHtml(t.member_display_name) : "";
        const memLine = t.user_id
          ? `<span class="item-meta">회원 ${memNm || "—"} · 전화 ${phone} · 성별 ${gen}</span>`
          : "";
        return `<li class="item-row" style="flex-wrap:wrap">
          <div class="item-main" style="min-width:12rem;flex:1">
            <strong>#${t.sequence_number}</strong> ${nm} · ${age} · 교회 ${ch}
            ${memLine ? `<br />${memLine}` : ""}
            <br /><span class="item-meta">${formatDt(t.created_at)}</span>
          </div>
        </li>`;
      })
      .join("");
  } catch (e) {
    loading.textContent = `오류: ${e.message}`;
  }
}

document.getElementById("bigmeet-refresh")?.addEventListener("click", () => loadBigMeetingTickets());

document.getElementById("bigmeet-clear")?.addEventListener("click", async () => {
  if (
    !confirm(
      "큰모임 번호를 모두 지울까요? 이 작업은 되돌릴 수 없습니다. 다음 행사 전에만 사용하세요."
    )
  )
    return;
  try {
    await fetchAdmin("/admin/big-meeting/tickets", { method: "DELETE" });
    showAlert("초기화했습니다.", false);
    loadBigMeetingTickets();
    loadDashboard();
  } catch (e) {
    showAlert(e.message, true);
  }
});

async function loadBoard() {
  const loading = document.getElementById("board-loading");
  const list = document.getElementById("board-list");
  const empty = document.getElementById("board-empty");
  loading.textContent = "불러오는 중…";
  loading.hidden = false;
  list.hidden = true;
  empty.hidden = true;
  try {
    const rows = await fetchAdmin("/admin/board/posts?limit=200");
    loading.hidden = true;
    if (!rows.length) {
      empty.hidden = false;
      return;
    }
    list.hidden = false;
    list.innerHTML = rows
      .map(
        (p) => `
      <li class="item-row" style="flex-wrap:wrap">
        <div class="item-main" style="min-width:12rem;flex:1">
          <strong>${escapeHtml(p.title)}</strong>
          <span class="item-meta">${formatDt(p.created_at)}</span>
          ${
            p.is_anonymous
              ? `<br /><span class="item-meta">익명 · 핸들 ${escapeHtml(p.anonymous_handle || "—")}</span>
                <br /><span class="item-meta">작성자 회원: ${p.author_user_id ? escapeHtml(p.author_member_display_name || p.author_user_id) : "—"} · ${p.author_member_phone ? escapeHtml(String(p.author_member_phone)) : ""}</span>`
              : `<br /><span class="item-meta">표시명 ${escapeHtml(p.author_name || "—")}${p.author_user_id ? ` · 회원 ${escapeHtml(p.author_member_display_name || "")}` : ""}</span>`
          }
        </div>
        <button type="button" class="btn-danger btn-small" data-del-board="${p.id}">삭제</button>
      </li>`
      )
      .join("");
    list.querySelectorAll("[data-del-board]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("이 글을 삭제할까요? 복구할 수 없습니다.")) return;
        try {
          await fetchAdmin(`/admin/board/posts/${btn.dataset.delBoard}`, { method: "DELETE" });
          showAlert("삭제했습니다.", false);
          loadBoard();
          loadDashboard();
        } catch (e) {
          showAlert(e.message, true);
        }
      });
    });
  } catch (e) {
    loading.textContent = `오류: ${e.message}`;
  }
}

async function loadOrgDeletionRequests() {
  const loading = document.getElementById("orgdel-loading");
  const list = document.getElementById("orgdel-list");
  const empty = document.getElementById("orgdel-empty");
  if (!loading || !list) return;
  loading.textContent = "불러오는 중…";
  loading.hidden = false;
  list.hidden = true;
  empty.hidden = true;
  try {
    const rows = await fetchAdmin("/admin/org-deletion-requests?status=pending");
    loading.hidden = true;
    if (!rows.length) {
      empty.hidden = false;
      return;
    }
    list.hidden = false;
    list.innerHTML = rows
      .map(
        (r) => `
      <li class="item-row" style="flex-wrap:wrap;align-items:flex-start">
        <div class="item-main" style="min-width:12rem;flex:1">
          <strong>${escapeHtml(r.organization_name)}</strong>
          <span class="item-meta">${formatDt(r.created_at)} · 신청 ${escapeHtml(r.requester_display_name || "")}</span>
          ${r.reason ? `<p class="muted" style="margin:0.35rem 0 0;font-size:0.85rem">${escapeHtml(r.reason)}</p>` : ""}
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:0.35rem">
          <button type="button" class="btn-secondary btn-small" data-orgdel-approve="${r.id}">승인(삭제)</button>
          <button type="button" class="btn-danger btn-small" data-orgdel-reject="${r.id}">거절</button>
        </div>
      </li>`
      )
      .join("");
    list.querySelectorAll("[data-orgdel-approve]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("이 공동체(및 하위)를 비활성화할까요? 되돌리려면 DB에서 status를 다시 active로 바꿔야 합니다.")) return;
        try {
          await fetchAdmin(`/admin/org-deletion-requests/${btn.dataset.orgdelApprove}/approve`, { method: "POST" });
          showAlert("승인했습니다.", false);
          loadOrgDeletionRequests();
        } catch (e) {
          showAlert(e.message, true);
        }
      });
    });
    list.querySelectorAll("[data-orgdel-reject]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("이 삭제 신청을 거절할까요?")) return;
        try {
          await fetchAdmin(`/admin/org-deletion-requests/${btn.dataset.orgdelReject}/reject`, { method: "POST" });
          showAlert("거절했습니다.", false);
          loadOrgDeletionRequests();
        } catch (e) {
          showAlert(e.message, true);
        }
      });
    });
  } catch (e) {
    loading.textContent = `오류: ${e.message}`;
  }
}

document.getElementById("orgdel-refresh")?.addEventListener("click", () => loadOrgDeletionRequests());

function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tab);
  });
  document.querySelectorAll(".panel").forEach((p) => {
    p.hidden = p.id !== `panel-${tab}`;
  });
  showAlert("");

  if (tab === "dash") loadDashboard();
  if (tab === "announce") loadAnnouncements();
  if (tab === "events") loadEvents();
  if (tab === "plans") {
    loadAnnualPlans();
    loadMonthlyPlans();
  }
  if (tab === "board") loadBoard();
  if (tab === "orgdel") loadOrgDeletionRequests();
  if (tab === "bigmeet") loadBigMeetingTickets();
}

function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

document.getElementById("admin-token-save").addEventListener("click", () => {
  const v = document.getElementById("admin-token").value.trim();
  setToken(v);
  const hint = document.getElementById("admin-token-hint");
  hint.textContent = v ? "이 브라우저 세션에 저장했습니다." : "저장을 지웠습니다.";
});

document.getElementById("form-announce").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("a-title").value.trim();
  const body = document.getElementById("a-body").value;
  try {
    const orgId = document.getElementById("a-org").value.trim();
    const payload = { title, body };
    if (orgId) payload.organization_id = orgId;
    await fetchAdmin("/admin/announcements", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showAlert("공지를 등록했습니다.", false);
    e.target.reset();
    loadAnnouncements();
    loadDashboard();
  } catch (err) {
    showAlert(err.message, true);
  }
});

document.getElementById("form-event").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("e-title").value.trim();
  const startsRaw = document.getElementById("e-starts").value;
  if (!startsRaw) {
    showAlert("시작 시각을 입력하세요.", true);
    return;
  }
  const starts_at = new Date(startsRaw).toISOString();
  const description = document.getElementById("e-desc").value;
  const location = document.getElementById("e-loc").value.trim();
  const survey_url = document.getElementById("e-survey-url").value.trim();
  const survey_label =
    document.getElementById("e-survey-label").value.trim() || "참석 여부 설문조사";
  try {
    const orgIdEv = document.getElementById("e-org").value.trim();
    const payloadEv = {
      title,
      description,
      starts_at,
      ends_at: null,
      location,
      survey_url,
      survey_label,
    };
    if (orgIdEv) payloadEv.organization_id = orgIdEv;
    await fetchAdmin("/admin/events", {
      method: "POST",
      body: JSON.stringify(payloadEv),
    });
    showAlert("일정을 등록했습니다.", false);
    e.target.reset();
    loadEvents();
    loadDashboard();
  } catch (err) {
    showAlert(err.message, true);
  }
});

document.getElementById("form-annual").addEventListener("submit", async (e) => {
  e.preventDefault();
  const year = parseInt(document.getElementById("an-year").value, 10);
  const title = document.getElementById("an-title").value.trim();
  const body = document.getElementById("an-body").value;
  try {
    await fetchAdmin("/admin/plans/annual", {
      method: "POST",
      body: JSON.stringify({ year, title, body }),
    });
    showAlert("연간 계획을 등록했습니다.", false);
    e.target.reset();
    document.getElementById("an-year").value = String(new Date().getFullYear());
    loadAnnualPlans();
    loadDashboard();
  } catch (err) {
    showAlert(err.message, true);
  }
});

document.getElementById("form-monthly").addEventListener("submit", async (e) => {
  e.preventDefault();
  const year = parseInt(document.getElementById("mo-year").value, 10);
  const month = parseInt(document.getElementById("mo-month").value, 10);
  const title = document.getElementById("mo-title").value.trim();
  const body = document.getElementById("mo-body").value;
  try {
    await fetchAdmin("/admin/plans/monthly", {
      method: "POST",
      body: JSON.stringify({ year, month, title, body }),
    });
    showAlert("월간 계획을 등록했습니다.", false);
    e.target.reset();
    document.getElementById("mo-year").value = String(year);
    document.getElementById("mo-month").value = String(month);
    loadMonthlyPlans();
    loadDashboard();
  } catch (err) {
    showAlert(err.message, true);
  }
});

document.getElementById("mo-refresh").addEventListener("click", () => {
  loadMonthlyPlans();
});

document.getElementById("mo-list-year").addEventListener("change", () => {
  loadMonthlyPlans();
});

async function verifyAdminToken(token) {
  const t = token.trim();
  if (!t) return false;
  const res = await fetch("/admin/verify", {
    headers: { Authorization: `Bearer ${t}`, Accept: "application/json" },
  });
  return res.ok;
}

function finishBoot() {
  document.getElementById("admin-token").value = getToken();
  const y = new Date().getFullYear();
  document.getElementById("an-year").value = String(y);
  document.getElementById("mo-year").value = String(y);
  document.getElementById("mo-list-year").value = String(y);
  document.getElementById("mo-month").value = String(new Date().getMonth() + 1);
  initTabs();
  void loadAdminOrgSelects();
  loadDashboard();
}

async function boot() {
  const gate = document.getElementById("admin-gate");
  const gateErr = document.getElementById("gate-error");
  const gateInput = document.getElementById("gate-token-input");
  const gateBtn = document.getElementById("gate-submit");

  async function enterWith(tok) {
    gateErr.hidden = true;
    gateErr.textContent = "";
    if (!(await verifyAdminToken(tok))) {
      gate.hidden = false;
      gateErr.textContent = "토큰이 올바르지 않거나 서버에서 거부되었습니다.";
      gateErr.hidden = false;
      setToken("");
      return false;
    }
    setToken(tok.trim());
    gate.hidden = true;
    finishBoot();
    return true;
  }

  gateBtn.addEventListener("click", () => enterWith(gateInput.value));

  gateInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      enterWith(gateInput.value);
    }
  });

  const existing = getToken().trim();
  if (existing && (await enterWith(existing))) return;

  gate.hidden = false;
  gateInput.value = "";
  gateInput.focus();
}

boot();
