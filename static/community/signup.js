const ACCESS = "jaegun_access_token";

function show(msg) {
  const el = document.getElementById("signup-alert");
  el.textContent = msg;
  el.hidden = false;
}

document.getElementById("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  document.getElementById("signup-alert").hidden = true;
  const phone = document.getElementById("su-phone").value.trim();
  const password = document.getElementById("su-password").value;
  const display_name = document.getElementById("su-name").value.trim();
  const gender = document.getElementById("su-gender").value;
  const ageRaw = document.getElementById("su-age").value.trim();
  let age = null;
  if (ageRaw !== "") {
    const n = parseInt(ageRaw, 10);
    if (Number.isNaN(n) || n < 1 || n > 120) {
      show("나이는 1~120 사이로 입력하세요.");
      return;
    }
    age = n;
  }
  const church = document.getElementById("su-church").value.trim();
  const phone_visibility = document.getElementById("su-visibility").value;

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        phone,
        password,
        display_name,
        gender,
        age,
        church,
        phone_visibility,
      }),
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
    if (data?.access_token) {
      localStorage.setItem(ACCESS, data.access_token);
      window.location.href = "index.html";
    }
  } catch (err) {
    show(err instanceof Error ? err.message : "가입 요청 실패");
  }
});
