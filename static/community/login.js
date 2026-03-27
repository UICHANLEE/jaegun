const ACCESS = "jaegun_access_token";

function show(msg) {
  const el = document.getElementById("login-alert");
  el.textContent = msg;
  el.hidden = false;
}

function readHashToken() {
  const h = location.hash || "";
  if (!h.startsWith("#access_token=")) return;
  const t = decodeURIComponent(h.slice("#access_token=".length).trim());
  if (t) {
    localStorage.setItem(ACCESS, t);
    history.replaceState(null, "", "login.html");
  }
}

readHashToken();

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const phone = document.getElementById("login-phone").value.trim();
  const password = document.getElementById("login-password").value;
  show("");
  document.getElementById("login-alert").hidden = true;
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ phone, password }),
    });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }
    if (!res.ok) {
      const detail =
        data && typeof data === "object" && data.detail != null
          ? String(data.detail)
          : text || res.statusText;
      show(detail);
      return;
    }
    if (data && data.access_token) {
      localStorage.setItem(ACCESS, data.access_token);
      window.location.href = "index.html";
    }
  } catch (err) {
    show(err instanceof Error ? err.message : "로그인 요청 실패");
  }
});
