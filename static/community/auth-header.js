/**
 * 헤더 로그인 상태: 로그인·가입 ↔ 로그아웃·프로필
 * window.jaegunRefreshAuthHeader() 로 동일 탭에서 토큰 변경 후 갱신
 */
(function () {
  var KEY = "jaegun_access_token";

  function mount(root) {
    if (!root) return;
    var t = localStorage.getItem(KEY);
    if (t) {
      root.innerHTML =
        '<a class="header-pill" href="register.html">프로필</a>' +
        '<button type="button" class="header-pill header-pill--outline" id="jaegun-header-logout" aria-label="로그아웃">' +
        "로그아웃</button>";
      var btn = document.getElementById("jaegun-header-logout");
      if (btn) {
        btn.addEventListener("click", function () {
          localStorage.removeItem(KEY);
          window.location.reload();
        });
      }
    } else {
      root.innerHTML =
        '<a class="header-pill header-pill--primary" href="login.html">로그인</a>' +
        '<a class="header-pill" href="signup.html">가입</a>';
    }
  }

  function init() {
    mount(document.getElementById("header-auth"));
  }

  document.addEventListener("DOMContentLoaded", init);
  window.addEventListener("pageshow", function (ev) {
    if (ev.persisted) init();
  });
  window.jaegunRefreshAuthHeader = init;
})();
