const ACCESS = "jaegun_access_token";

function token() {
  return localStorage.getItem(ACCESS) || "";
}

function showRegAlert(msg) {
  const el = document.getElementById("reg-alert");
  el.textContent = msg;
  el.hidden = false;
}

function hideRegAlert() {
  const el = document.getElementById("reg-alert");
  el.hidden = true;
}

async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...options.headers };
  const t = token();
  if (t) headers.Authorization = `Bearer ${t}`;
  const res = await fetch(path, { ...options, headers });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const detail =
      data && typeof data === "object" && data.detail != null ? String(data.detail) : text || res.statusText;
    throw new Error(detail);
  }
  return data;
}

function showGuest() {
  document.getElementById("prof-guest").hidden = false;
  document.getElementById("prof-form-wrap").hidden = true;
}

function showForm() {
  document.getElementById("prof-guest").hidden = true;
  document.getElementById("prof-form-wrap").hidden = false;
}

async function loadMe() {
  if (!token()) {
    showGuest();
    return;
  }
  try {
    const me = await api("/api/me");
    document.getElementById("reg-name").value = me.display_name || "";
    document.getElementById("reg-gender").value = me.gender || "";
    document.getElementById("reg-age").value =
      me.age != null && me.age !== "" ? String(me.age) : "";
    document.getElementById("reg-church").value = me.church || "";
    document.getElementById("reg-visibility").value = me.phone_visibility || "admin_only";
    const prev = document.getElementById("prof-avatar-preview");
    if (me.avatar_url) {
      prev.src = me.avatar_url;
      prev.hidden = false;
    } else {
      prev.removeAttribute("src");
      prev.hidden = true;
    }
    showForm();
  } catch {
    localStorage.removeItem(ACCESS);
    showGuest();
  }
}

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideRegAlert();
  const display_name = document.getElementById("reg-name").value.trim();
  if (!display_name) {
    showRegAlert("이름을 입력해 주세요.");
    return;
  }
  const gender = document.getElementById("reg-gender").value;
  const ageRaw = document.getElementById("reg-age").value.trim();
  let age = null;
  if (ageRaw !== "") {
    const n = parseInt(ageRaw, 10);
    if (Number.isNaN(n) || n < 1 || n > 120) {
      showRegAlert("나이는 1~120 사이 숫자로 입력해 주세요.");
      return;
    }
    age = n;
  }
  const church = document.getElementById("reg-church").value.trim();
  const phone_visibility = document.getElementById("reg-visibility").value;
  try {
    await api("/api/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        display_name,
        gender,
        age,
        church,
        phone_visibility,
      }),
    });
    showRegAlert("저장했습니다.");
    document.getElementById("reg-alert").classList.remove("alert-error");
    await loadMe();
  } catch (err) {
    showRegAlert(err instanceof Error ? err.message : "저장 실패");
  }
});

document.getElementById("prof-avatar").addEventListener("change", async () => {
  const input = document.getElementById("prof-avatar");
  const f = input.files && input.files[0];
  if (!f || !token()) return;
  hideRegAlert();
  const fd = new FormData();
  fd.append("file", f);
  try {
    const headers = { Accept: "application/json", Authorization: `Bearer ${token()}` };
    const res = await fetch("/api/me/avatar", { method: "POST", headers, body: fd });
    const text = await res.text();
    if (!res.ok) {
      let detail = text;
      try {
        const j = JSON.parse(text);
        if (j.detail) detail = String(j.detail);
      } catch {
        /* */
      }
      throw new Error(detail);
    }
    const me = JSON.parse(text);
    const prev = document.getElementById("prof-avatar-preview");
    if (me.avatar_url) {
      prev.src = me.avatar_url;
      prev.hidden = false;
    }
    showRegAlert("프로필 사진을 올렸습니다.");
  } catch (err) {
    showRegAlert(err instanceof Error ? err.message : "업로드 실패");
  }
  input.value = "";
});

document.getElementById("prof-logout").addEventListener("click", () => {
  localStorage.removeItem(ACCESS);
  showGuest();
});

loadMe();
