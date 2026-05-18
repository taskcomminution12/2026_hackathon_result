// 공통 — 사이드바 렌더링, fetch 헬퍼, toast.
const API = "/api";

const COLOR_TOKENS = {
  primary: "#2563EB", blue: "#3B82F6", purple: "#8B5CF6",
  teal: "#14B8A6", orange: "#F97316", pink: "#EC4899",
  amber: "#D97706", emerald: "#059669",
  danger: "#EF4444", warning: "#F59E0B", success: "#10B981",
  info: "#06B6D4", border: "#EEF1F5", text: "#0F172A", dim: "#94A3B8",
};

function $(sel, root = document) { return root.querySelector(sel); }
function $$(sel, root = document) { return [...root.querySelectorAll(sel)]; }

async function jget(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}
async function jpost(path, body) {
  const r = await fetch(API + path, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : null,
  });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}
async function jput(path, body) {
  const r = await fetch(API + path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

function escapeHTML(s) {
  return String(s ?? "").replace(/[&<>"']/g, c =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
}
function fmtRel(iso) {
  if (!iso) return "—";
  const dt = (Date.now() - new Date(iso).getTime()) / 1000;
  if (dt < 60) return "방금";
  if (dt < 3600) return `${Math.floor(dt/60)}분 전`;
  if (dt < 86400) return `${Math.floor(dt/3600)}시간 전`;
  if (dt < 86400 * 30) return `${Math.floor(dt/86400)}일 전`;
  return fmtDate(iso);
}
function iconForFile(name, contentType) {
  const ct = (contentType || "").toLowerCase();
  if (ct === "pdf") return "file-text";
  if (ct === "movie") return "film";
  if (!name) return "file";
  const ext = name.split(".").pop().toLowerCase();
  if (["zip","7z","rar","gz","tar"].includes(ext)) return "file-archive";
  if (["mp4","mov","avi","mkv","webm"].includes(ext)) return "film";
  if (["pdf"].includes(ext)) return "file-text";
  if (["doc","docx"].includes(ext)) return "file-type";
  if (["ppt","pptx"].includes(ext)) return "presentation";
  if (["xls","xlsx","csv"].includes(ext)) return "table";
  if (["jpg","jpeg","png","gif","svg","webp"].includes(ext)) return "image";
  if (["py","js","ts","java","c","cpp","cs","go","rb"].includes(ext)) return "file-code";
  return "file";
}

function fmtBytes(n) {
  if (!n && n !== 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n/1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n/1024/1024).toFixed(1)} MB`;
  return `${(n/1024/1024/1024).toFixed(2)} GB`;
}
function dayBadge(daysLeft) {
  const d = Math.ceil(daysLeft);
  if (d <= 0) return { cls: "badge--soft", text: "마감" };
  if (d <= 1) return { cls: "badge--danger", text: `D-${d}` };
  if (d <= 3) return { cls: "badge--warn",   text: `D-${d}` };
  if (d <= 7) return { cls: "badge--info",   text: `D-${d}` };
  return       { cls: "badge--success", text: `D-${d}` };
}
function todayKR() {
  const days = ["일","월","화","수","목","금","토"];
  const d = new Date();
  return `${d.getFullYear()}년 ${d.getMonth()+1}월 ${d.getDate()}일 · ${days[d.getDay()]}요일`;
}

// ----- Sidebar -----
async function renderSidebar(activeKey) {
  const aside = document.querySelector(".sidebar");
  if (!aside) return;
  const courses = await jget("/courses").catch(() => []);
  const totalFiles = courses.reduce((s, c) => s + (c.file_count || 0), 0);

  aside.innerHTML = `
    <div class="sidebar__brand">
      <div class="brand__logo">SU</div>
      <div class="brand__text">
        <div class="brand__title">수원대 LMS Sync</div>
        <div class="brand__sub">올인원 학습 도구</div>
      </div>
    </div>

    <nav class="nav">
      <div class="nav__group-label">메인</div>
      <a class="nav__item ${activeKey === 'dashboard' ? 'is-active' : ''}" href="/dashboard">
        <i data-lucide="layout-dashboard"></i><span>대시보드</span>
      </a>
      <a class="nav__item ${activeKey === 'settings' ? 'is-active' : ''}" href="/settings">
        <i data-lucide="settings"></i><span>설정</span>
      </a>

      <div class="nav__group-label">과목 <span class="nav__group-count">${courses.length}</span></div>
      ${courses.map(c => `
        <a class="nav__item nav__item--course ${activeKey === 'course-' + c.id ? 'is-active' : ''}"
           href="/course/${c.id}" title="${escapeHTML(c.name)}">
          <span class="dot dot--${c.color || 'blue'}"></span>
          <span class="nav__label">${escapeHTML(c.name)}</span>
          <span class="nav__count">${c.file_count}</span>
        </a>`).join("")}
    </nav>

    <div class="sidebar__foot">
      <div class="sync-card">
        <div class="sync-card__row">
          <span class="sync-dot" data-bind="sync.dot"></span>
          <span class="sync-card__label">자료 ${totalFiles}건</span>
        </div>
        <div class="sync-card__time" data-bind="sync.time">동기화 이력 없음</div>
      </div>
    </div>
  `;
  if (window.lucide) lucide.createIcons();
}

// ----- Toast -----
let _toastTimer = null;
function toast({ title = "알림", message = "", kind = "ok" } = {}) {
  const t = document.querySelector(".toast");
  if (!t) return;
  t.hidden = false;
  t.dataset.kind = kind;
  t.querySelector(".toast__title").textContent = title;
  t.querySelector(".toast__sub").textContent = message;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { t.hidden = true; }, 4500);
}

// ----- 동기화 트리거 + 폴링 -----
async function triggerSyncWithPolling(btn) {
  if (btn) {
    btn.disabled = true;
    btn.querySelector("span").textContent = "동기화 중…";
  }
  try {
    const r = await jpost("/sync");
    if (!r.started) toast({ title: "동기화", message: "이미 실행 중입니다." });
    else toast({ title: "동기화", message: "백그라운드 작업 시작" });

    const it = setInterval(async () => {
      try {
        const s = await jget("/sync/status");
        updateSyncIndicator(s);
        if (s.status === "done" || s.status === "failed") {
          clearInterval(it);
          if (btn) {
            btn.disabled = false;
            btn.querySelector("span").textContent = "지금 동기화";
          }
          if (s.status === "done") {
            toast({
              title: "동기화 완료",
              message: `신규 ${s.files_added} · 스킵 ${s.files_skipped} · 실패 ${s.files_failed}`,
              kind: s.files_failed ? "warn" : "ok",
            });
          } else {
            toast({ title: "동기화 실패", message: s.error || "원인 불명", kind: "fail" });
          }
          if (typeof onSyncFinished === "function") onSyncFinished();
        }
      } catch (e) {}
    }, 4000);
  } catch (e) {
    if (btn) {
      btn.disabled = false;
      btn.querySelector("span").textContent = "지금 동기화";
    }
    toast({ title: "오류", message: String(e), kind: "fail" });
  }
}

function updateSyncIndicator(s) {
  const time = document.querySelector('[data-bind="sync.time"]');
  const dot = document.querySelector('[data-bind="sync.dot"]');
  const last = document.querySelector('[data-bind="sync.last"]');

  let label;
  if (!s || s.status === "idle") label = "동기화 이력 없음";
  else if (s.status === "running") label = "동기화 진행 중…";
  else label = `마지막 동기화 ${fmtRel(s.finished_at)}`;

  if (time) time.textContent = label;
  if (last) last.textContent = label;
  if (dot) {
    const c = s?.status === "failed" ? COLOR_TOKENS.danger
            : s?.status === "running" ? COLOR_TOKENS.warning
            : COLOR_TOKENS.success;
    dot.style.background = c;
    dot.style.boxShadow = `0 0 0 4px ${c}26`;
  }
}

// ----- 공통 이벤트 바인딩 -----
function bindCommonActions() {
  // 동기화
  $$("[data-action='sync']").forEach(b => b.addEventListener("click", () => triggerSyncWithPolling(b)));
  // 토스트 닫기
  $$("[data-action='toast-close']").forEach(b =>
    b.addEventListener("click", () => { document.querySelector(".toast").hidden = true; }));
  // 다운로드 폴더 열기
  $$("[data-action='open-folder']").forEach(b =>
    b.addEventListener("click", async () => {
      try {
        await jpost("/files/open-root");
      } catch (e) { toast({ title: "오류", message: String(e), kind: "fail" }); }
    }));
}

window.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) lucide.createIcons();
  await renderSidebar(document.querySelector(".sidebar")?.dataset.active);
  bindCommonActions();
  jget("/sync/status").then(updateSyncIndicator).catch(() => {});
});
