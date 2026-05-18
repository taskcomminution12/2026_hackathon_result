// 설정 페이지

function _setText(selector, text) {
  const el = $(selector);
  if (el) el.textContent = text;
}

async function loadSettings() {
  const [me, st, hist, kakao, sched] = await Promise.all([
    jget("/me").catch(() => null),
    jget("/settings").catch(() => null),
    jget("/sync/history?limit=20").catch(() => []),
    jget("/kakao/status").catch(() => ({ connected: false })),
    jget("/sync/scheduler").catch(() => null),
  ]);

  if (me) {
    _setText('[data-bind="settings.user"]', `${me.name} (학번 ${me.login_id})`);
  } else {
    _setText('[data-bind="settings.user"]', "Canvas 토큰을 입력하세요");
  }

  if (st) {
    _setText('[data-bind="settings.base_url"]', st.canvas_base_url);
    const tokenEl = $('[data-bind="settings.token_state"]');
    if (tokenEl) {
      tokenEl.textContent = st.has_canvas_token ? "연결됨" : "토큰 없음";
      tokenEl.className = "badge " + (st.has_canvas_token ? "badge--success" : "badge--danger");
    }
    const previewEl = $('[data-bind="settings.token_preview"]');
    if (previewEl) previewEl.textContent = st.canvas_token_preview || "";
    const rootInput = $("#downloadRoot");
    if (rootInput) rootInput.value = st.download_root || "";
  }

  try { renderKakao(kakao); } catch (e) { console.warn("renderKakao", e); }
  try { renderScheduler(sched); } catch (e) { console.warn("renderScheduler", e); }
  try { renderHistory(hist); } catch (e) { console.warn("renderHistory", e); }
}

function renderKakao(k) {
  const badge = $('[data-bind="kakao.badge"]');
  const state = $('[data-bind="kakao.state"]');
  const btnConn = $('[data-bind="kakao.btn-connect"]');
  const btnTest = $('[data-action="kakao-test"]');
  const btnNotify = $('[data-action="kakao-notify-now"]');
  const btnDisc = $('[data-action="kakao-disconnect"]');

  if (k && k.connected) {
    badge.textContent = "연결됨";
    badge.className = "badge badge--success";
    state.textContent = `유효 (만료 ${fmtDateTime(k.expires_at)})`;
    btnConn.hidden = true;
    btnTest.hidden = false;
    btnNotify.hidden = false;
    btnDisc.hidden = false;
  } else {
    badge.textContent = "미연결";
    badge.className = "badge badge--soft";
    state.textContent = "카카오톡으로 마감 알림을 받으려면 연결하세요.";
    btnConn.hidden = false;
    btnTest.hidden = true;
    btnNotify.hidden = true;
    btnDisc.hidden = true;
  }
}

function renderScheduler(s) {
  if (!s) return;
  const sel = $("#syncInterval");
  if (sel) sel.value = String(s.interval_minutes);  
  const next = $('[data-bind="scheduler.next"]');
  if (next) {
    if (s.realtime) next.textContent = "실시간 모드 — sync 종료 직후 자동 재시작";
    else next.textContent = s.next_run ? fmtDateTime(s.next_run) : "—";
  }
}

function renderHistory(rows) {
  const tbody = $('[data-bind="sync.history"]');
  if (!tbody) return;
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-row">기록이 없습니다.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const cls = r.status === "done" ? "badge--success"
              : r.status === "running" ? "badge--warn"
              : "badge--danger";
    return `
      <tr>
        <td><span class="mono">${fmtDateTime(r.started_at)}</span></td>
        <td><span class="mono">${fmtDateTime(r.finished_at)}</span></td>
        <td>${r.files_added}</td>
        <td>${r.files_skipped}</td>
        <td>${r.files_failed}</td>
        <td><span class="badge ${cls}">${r.status}</span></td>
      </tr>`;
  }).join("");
}

async function saveFolder() {
  const v = $("#downloadRoot").value.trim();
  if (!v) return;
  try {
    const r = await jput("/settings", { download_root: v });
    toast({ title: "저장됨", message: `다운로드 폴더 → ${r.download_root}` });
  } catch (e) {
    toast({ title: "저장 실패", message: String(e), kind: "fail" });
  }
}

async function kakaoTest() {
  try {
    const r = await jpost("/kakao/test");
    toast({ title: "카톡 테스트", message: r.ok ? "발송 성공 — 본인 카톡 확인" : "발송 실패", kind: r.ok ? "ok" : "fail" });
  } catch (e) { toast({ title: "오류", message: String(e), kind: "fail" }); }
}
async function kakaoNotifyNow() {
  try {
    await jpost("/kakao/notify-now");
    toast({ title: "임박 과제 알림 실행", message: "마감 임박 과제가 있으면 카톡으로 발송됨" });
  } catch (e) { toast({ title: "오류", message: String(e), kind: "fail" }); }
}
async function kakaoDisconnect() {
  if (!confirm("카카오톡 연결을 해제하시겠어요?")) return;
  try {
    await jpost("/kakao/disconnect");
    toast({ title: "연결 해제됨", message: "" });
    loadSettings();
  } catch (e) { toast({ title: "오류", message: String(e), kind: "fail" }); }
}
async function saveInterval() {
  const v = parseInt($("#syncInterval").value, 10);
  try {
    const r = await jput("/sync/scheduler", { minutes: v });
    const label = v === 0 ? "실시간 모드로 설정" : `${v}분마다 자동 동기화`;
    toast({ title: "주기 변경", message: label });
    renderScheduler(r);
  } catch (e) { toast({ title: "저장 실패", message: String(e), kind: "fail" }); }
}

function toggleTokenVisibility() {
  const input = $("#canvasTokenInput");
  if (!input) return;
  const showing = input.type === "text";
  input.type = showing ? "password" : "text";
  const btn = $('[data-action="toggle-token-visibility"]');
  if (btn) {
    btn.innerHTML = showing
      ? '<i data-lucide="eye"></i>'
      : '<i data-lucide="eye-off"></i>';
    if (window.lucide) lucide.createIcons();
  }
}
async function saveToken() {
  const v = $("#canvasTokenInput").value.trim();
  if (!v) {
    toast({ title: "토큰 비어있음", message: "토큰을 입력하세요", kind: "fail" });
    return;
  }
  try {
    await jput("/settings", { canvas_token: v });
    toast({ title: "토큰 저장됨", message: "다음 sync 부터 새 토큰 사용" });
    $("#canvasTokenInput").value = "";
    loadSettings();
  } catch (e) {
    toast({ title: "저장 실패", message: String(e), kind: "fail" });
  }
}

function _bind(selector, handler) {
  const el = $(selector);
  if (el) el.addEventListener("click", handler);
}

window.addEventListener("DOMContentLoaded", () => {
  _bind('[data-action="save-folder"]', saveFolder);
  _bind('[data-action="kakao-test"]', kakaoTest);
  _bind('[data-action="kakao-notify-now"]', kakaoNotifyNow);
  _bind('[data-action="kakao-disconnect"]', kakaoDisconnect);
  _bind('[data-action="save-interval"]', saveInterval);

  document.addEventListener("click", (e) => {
    if (e.target.closest('[data-action="toggle-token-visibility"]')) {
      e.preventDefault();
      toggleTokenVisibility();
    } else if (e.target.closest('[data-action="save-token"]')) {
      e.preventDefault();
      saveToken();
    }
  });

  loadSettings().catch((e) => console.warn("loadSettings failed:", e));
});
