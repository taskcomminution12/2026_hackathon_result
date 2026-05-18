// 대시보드 페이지

let weeklyChart = null;
let deadlineChart = null;
const courseColorById = {};

async function refreshDashboard() {
  const today = $('[data-bind="today"]'); if (today) today.textContent = todayKR();

  const [me, courses, stats, ass, dist, files, anns, sync] = await Promise.all([
    jget("/me").catch(() => null),
    jget("/courses").catch(() => []),
    jget("/files/stats").catch(() => ({ total_files: 0, weekly: [] })),
    jget("/assignments/upcoming?limit=8").catch(() => []),
    jget("/assignments/deadline-distribution").catch(() => ({ d1: 0, d3: 0, d7: 0, d14: 0 })),
    jget("/files?limit=8").catch(() => []),
    jget("/announcements?limit=6").catch(() => []),
    jget("/sync/status").catch(() => ({ status: "idle" })),
  ]);

  // me
  const userBind = $('[data-bind="footer.user"]');
  if (userBind && me) userBind.textContent = `${me.name} · 학번 ${me.login_id}`;

  courses.forEach(c => courseColorById[c.id] = c.color);

  // KPI
  $('[data-bind="kpi.subjects"]').textContent = courses.length;
  $('[data-bind="kpi.subjects_sub"]').textContent = courses.length
    ? `자료 보유 ${courses.filter(c => c.file_count > 0).length}개`
    : "동기화 필요";

  $('[data-bind="kpi.files"]').textContent = stats.total_files;
  const recent = files.filter(f => {
    if (!f.downloaded_at) return false;
    return (Date.now() - new Date(f.downloaded_at).getTime()) < 7 * 86400 * 1000;
  });
  $('[data-bind="kpi.files_sub"]').textContent = recent.length
    ? `최근 7일 +${recent.length}` : "—";

  const upcomingCount = ass.filter(a => !a.submitted && a.days_left <= 7).length;
  $('[data-bind="kpi.assignments"]').textContent = upcomingCount;
  const d1 = ass.find(a => a.days_left <= 1 && !a.submitted);
  $('[data-bind="kpi.assignments_sub"]').textContent = d1 ? "D-1 임박" : (upcomingCount ? "D-7 이내" : "—");

  renderWeeklyChart(stats);
  renderDeadlineChart(dist);
  renderAssignments(ass);
  renderFeed(files);
  renderAnnouncements(anns);
  await renderCalendar();
  updateSyncIndicator(sync);
}

function onSyncFinished() {
  refreshDashboard();
  renderSidebar("dashboard");
}

function renderWeeklyChart(stats) {
  const ctx = document.getElementById("chartWeekly");
  if (!ctx || !stats.weekly?.length) return;

  const subjects = stats.weekly[0].by_subject || [];
  const datasets = subjects.map(sub => ({
    label: sub.subject_name,
    data: stats.weekly.map(w => {
      const cell = w.by_subject.find(x => x.subject_id === sub.subject_id);
      return cell ? cell.count : 0;
    }),
    backgroundColor: COLOR_TOKENS[sub.color] || COLOR_TOKENS.blue,
    borderRadius: 0,
    borderSkipped: false,
    barPercentage: 0.7,
    categoryPercentage: 0.7,
  }));

  if (weeklyChart) weeklyChart.destroy();
  weeklyChart = new Chart(ctx, {
    type: "bar",
    data: { labels: stats.weekly.map(w => `${w.week}주`), datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      layout: { padding: { top: 8, bottom: 4 } },
      plugins: {
        legend: {
          position: "bottom",
          align: "start",
          labels: {
            boxWidth: 8, boxHeight: 8,
            usePointStyle: true, pointStyle: "circle",
            padding: 14,
            font: { size: 11.5, weight: "500" },
            color: COLOR_TOKENS.text,
          },
        },
        tooltip: {
          backgroundColor: "#0F172A", padding: 10, cornerRadius: 8,
          titleFont: { size: 12, weight: "600" },
          bodyFont: { size: 12 },
        },
      },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { font: { size: 11 } } },
        y: {
          stacked: true,
          grid: { color: COLOR_TOKENS.border, drawBorder: false },
          ticks: { stepSize: 2, font: { size: 11 } },
          beginAtZero: true,
        },
      },
    },
  });
}

function renderDeadlineChart(d) {
  const ctx = document.getElementById("chartDeadline");
  if (!ctx) return;
  const total = d.d1 + d.d3 + d.d7 + d.d14;
  if (deadlineChart) deadlineChart.destroy();
  if (total === 0) {
    ctx.parentElement.innerHTML = `<div class="empty">14일 이내 마감 과제가 없습니다.</div>`;
    return;
  }
  deadlineChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["D-1 이내", "D-3 이내", "D-7 이내", "D-14 이내"],
      datasets: [{
        data: [d.d1, d.d3, d.d7, d.d14],
        backgroundColor: [COLOR_TOKENS.danger, COLOR_TOKENS.warning, COLOR_TOKENS.success, COLOR_TOKENS.info],
        borderWidth: 0, hoverOffset: 6,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: "70%",
      layout: { padding: 14 },
      radius: "90%",
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            boxWidth: 8, boxHeight: 8,
            usePointStyle: true, pointStyle: "circle",
            padding: 12, font: { size: 11.5, weight: "500" },
            color: COLOR_TOKENS.text,
          },
        },
        tooltip: { backgroundColor: "#0F172A", padding: 10, cornerRadius: 8 },
      },
    },
  });
}

function renderAssignments(list) {
  const tbody = $('[data-bind="assignments.rows"]');
  const empty = $('[data-bind="assignments.empty"]');
  if (!tbody) return;
  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-row">임박 과제가 없습니다.</td></tr>`;
    if (empty) { empty.textContent = ""; empty.hidden = true; }
    return;
  }
  if (empty) { empty.textContent = `${list.length}건`; empty.hidden = false; }
  tbody.innerHTML = list.map(a => {
    const b = dayBadge(a.days_left);
    const status = a.submitted
      ? '<span class="badge badge--success">제출 완료</span>'
      : '<span class="badge badge--soft">제출 안 함</span>';
    const url = a.html_url ? `<a href="${escapeHTML(a.html_url)}" target="_blank" rel="noopener">${escapeHTML(a.title)}</a>` : escapeHTML(a.title);
    return `
      <tr>
        <td><a class="course-link" href="/course/${a.subject.id}">
              <span class="dot dot--${a.subject.color}"></span> ${escapeHTML(a.subject.name)}
            </a></td>
        <td>${url}</td>
        <td><span class="mono">${fmtDateTime(a.due_at)}</span></td>
        <td><span class="badge ${b.cls}">${b.text}</span></td>
        <td>${status}</td>
      </tr>`;
  }).join("");
}

function renderFeed(files) {
  const ul = $('[data-bind="feed.rows"]');
  if (!ul) return;
  if (!files.length) {
    ul.innerHTML = `<li class="feed__item"><div class="feed__body">
      <div class="feed__sub">아직 다운로드된 자료가 없습니다. 동기화를 실행하세요.</div>
    </div></li>`;
    return;
  }
  ul.innerHTML = files.map(f => `
    <li class="feed__item is-clickable" data-file-id="${f.id}" title="탐색기에서 열기">
      <span class="feed__icon feed__icon--${f.subject.color || 'blue'}">
        <i data-lucide="${iconForFile(f.file_name, f.content_type)}"></i>
      </span>
      <div class="feed__body">
        <div class="feed__title">${escapeHTML(f.title || f.file_name)}</div>
        <div class="feed__sub">
          <span class="dot dot--${f.subject.color}"></span>
          <span>${escapeHTML(f.subject.name)}</span>
          <span class="dot-sep"></span>
          <span class="mono">${escapeHTML(f.file_name)}</span>
          <span class="dot-sep"></span>
          <span>${fmtRel(f.downloaded_at)}</span>
        </div>
      </div>
      <i class="feed__chev" data-lucide="folder-open"></i>
    </li>
  `).join("");
  if (window.lucide) lucide.createIcons();

  $$('.feed__item.is-clickable', ul).forEach(li =>
    li.addEventListener("click", async () => {
      const id = li.dataset.fileId;
      try {
        await jpost(`/files/${id}/open`);
        toast({ title: "탐색기 열림", message: li.querySelector(".feed__title").textContent });
      } catch (e) {
        toast({ title: "열기 실패", message: String(e), kind: "fail" });
      }
    }));
}

function renderAnnouncements(items) {
  const ul = $('[data-bind="announcements.rows"]');
  if (!ul) return;
  if (!items.length) {
    ul.innerHTML = `<li class="feed__item"><div class="feed__body">
      <div class="feed__sub">최근 공지가 없습니다.</div></div></li>`;
    return;
  }
  ul.innerHTML = items.map(a => `
    <li class="feed__item">
      <span class="feed__icon feed__icon--${a.subject.color}">
        <i data-lucide="megaphone"></i>
      </span>
      <div class="feed__body">
        <div class="feed__title">${escapeHTML(a.title)}</div>
        <div class="feed__sub">
          <span class="dot dot--${a.subject.color}"></span>
          <span>${escapeHTML(a.subject.name)}</span>
          <span class="dot-sep"></span>
          <span>${fmtRel(a.posted_at)}</span>
          ${a.has_attachments ? '<span class="dot-sep"></span><span class="mono">첨부 있음</span>' : ''}
        </div>
      </div>
      ${a.html_url ? `<a class="iconbtn" href="${escapeHTML(a.html_url)}" target="_blank" rel="noopener" title="LMS에서 보기">
                       <i data-lucide="external-link"></i></a>` : ''}
    </li>
  `).join("");
  if (window.lucide) lucide.createIcons();
}

async function renderCalendar() {
  const el = document.getElementById("calendar");
  if (!el) return;
  const list = await jget("/assignments/upcoming?limit=50").catch(() => []);
  const toLocalDate = (iso) => {
    const d = new Date(iso);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const da = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${da}`;
  };
  const addDays = (isoDate, days) => {
    const d = new Date(isoDate);
    d.setDate(d.getDate() + days);
    return toLocalDate(d.toISOString());
  };

  const events = list.map(a => {
    const color = COLOR_TOKENS[a.subject.color] || COLOR_TOKENS.blue;
    const startIso = a.unlock_at || a.due_at;
    const endIso = a.lock_at || a.due_at;
    const startDate = toLocalDate(startIso);
    const endDate = addDays(toLocalDate(endIso), 1);
    return {
      title: `${a.subject.name} — ${a.title}`,
      backgroundColor: color,
      textColor: "#fff",
      url: a.html_url || undefined,
      start: startDate,
      end: endDate,
      allDay: true,
    };
  });
  const cal = new FullCalendar.Calendar(el, {
    initialView: "dayGridMonth",
    locale: "ko",
    height: 560,
    headerToolbar: { left: "prev,next today", center: "title", right: "dayGridMonth,timeGridWeek,listWeek" },
    buttonText: { today: "오늘", month: "월", week: "주", list: "목록" },
    displayEventTime: false,
    dayMaxEventRows: 4,
    moreLinkText: (n) => `+${n}건`,
    events,
  });
  cal.render();
}

// ----- 자동 갱신 -----
let _lastSyncSig = "";

async function pollSyncTick() {
  try {
    const s = await jget("/sync/status");
    const sig = `${s.id}:${s.status}:${s.files_added}:${s.files_skipped}:${s.files_failed}:${s.finished_at || ""}`;
    if (sig !== _lastSyncSig) {
      _lastSyncSig = sig;
      await refreshDashboard();
    } else {
      updateSyncIndicator(s);
    }
  } catch (e) {}
}

window.addEventListener("DOMContentLoaded", () => {
  refreshDashboard().then(() => {
    jget("/sync/status").then(s => {
      _lastSyncSig = `${s.id}:${s.status}:${s.files_added}:${s.files_skipped}:${s.files_failed}:${s.finished_at || ""}`;
    }).catch(() => {});
  });
  $$('[data-action="refresh-feed"]').forEach(b => b.addEventListener("click", refreshDashboard));

  setInterval(pollSyncTick, 3000);
});
