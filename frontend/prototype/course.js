// 과목 상세 페이지

const courseId = parseInt(location.pathname.split("/")[2], 10);

async function loadCourse() {
  if (!courseId) {
    $('[data-bind="course.name"]').textContent = "잘못된 과목 ID";
    return;
  }

  const [tree, anns, assignsAll] = await Promise.all([
    jget(`/courses/${courseId}/tree`).catch(() => ({ subject: null, weeks: [] })),
    jget(`/courses/${courseId}/announcements`).catch(() => []),
    jget("/assignments/upcoming?limit=200").catch(() => []),
  ]);

  if (!tree.subject) {
    $('[data-bind="course.name"]').textContent = "동기화되지 않은 과목";
    $('[data-bind="course.meta"]').textContent = "대시보드에서 동기화 먼저 실행하세요.";
    return;
  }

  const subj = tree.subject;
  document.title = `${subj.name} — 수원대 LMS Sync`;

  const nameEl = $('[data-bind="course.name"]');
  nameEl.innerHTML = `<span class="dot dot--${subj.color || 'blue'}"></span>${escapeHTML(subj.name)}`;

  const allItems = tree.weeks.flatMap(w => w.items || []);
  const weekFileCount = allItems.filter(it => it.file).length;
  const boardFileCount = (tree.boards || []).reduce((s, b) => s + b.files.length, 0);
  const fileCount = weekFileCount + boardFileCount;
  const weeksWithItems = tree.weeks.filter(w => (w.items || []).length > 0).length;
  $('[data-bind="course.files_count"]').textContent = fileCount;
  $('[data-bind="course.weeks_count"]').textContent = weeksWithItems;
  $('[data-bind="course.announcements_count"]').textContent = anns.length;
  const metaParts = [`${fileCount}개 자료`];
  if (boardFileCount > 0) metaParts.push(`(주차 ${weekFileCount} + 게시판 ${boardFileCount})`);
  metaParts.push(`${weeksWithItems}주차`, `공지 ${anns.length}건`);
  $('[data-bind="course.meta"]').textContent = metaParts.join(" · ");

  renderWeeks(tree.weeks);
  renderBoards(tree.boards || []);

  const courseAssigns = assignsAll.filter(a => a.subject.id === courseId);
  renderCourseAssignments(courseAssigns);
  renderCourseAnnouncements(anns);
  bindOpenCanvas(subj.id);
  bindOpenCourseFolder(allItems);
}

function renderBoards(boards) {
  const card = $('[data-bind="course.boards-card"]');
  const ul = $('[data-bind="course.boards"]');
  if (!card || !ul) return;
  const totalFiles = boards.reduce((s, b) => s + b.files.length, 0);
  if (!totalFiles) {
    card.hidden = true;
    return;
  }
  card.hidden = false;
  const html = boards.map(b => `
    <li class="board-group">
      <div class="board-group__head">
        <i data-lucide="layout-list"></i>
        <span class="board-group__title">${escapeHTML(b.title)}</span>
        <span class="board-group__count">${b.files.length}건</span>
      </div>
      <ul class="filelist">
        ${b.files.map(f => `
          <li class="fileitem" data-file-id="${f.id}" title="탐색기에서 위치 열기">
            <span class="fileitem__icon"><i data-lucide="${iconForFile(f.file_name, f.content_type)}"></i></span>
            <div class="fileitem__body">
              <div class="fileitem__title">${escapeHTML(f.title || f.file_name)}</div>
              <div class="fileitem__sub">
                <span class="mono">${escapeHTML(f.file_name)}</span>
                <span class="dot-sep"></span>
                <span>${fmtBytes(f.file_size)}</span>
                <span class="dot-sep"></span>
                <span>${fmtRel(f.downloaded_at)}</span>
              </div>
            </div>
            <button class="iconbtn" data-action="open-file" title="파일 위치 열기">
              <i data-lucide="folder-open"></i>
            </button>
          </li>`).join("")}
      </ul>
    </li>
  `).join("");
  ul.innerHTML = html;
  if (window.lucide) lucide.createIcons();
  $$('.fileitem', ul).forEach(li => {
    const fid = li.dataset.fileId;
    if (fid) li.addEventListener("click", () => openFile(fid));
  });
}

function renderWeeks(weeks) {
  const container = $('[data-bind="weeks.container"]');
  if (!container) return;
  if (!weeks.length || weeks.every(w => !(w.items || []).length)) {
    container.innerHTML = `<div class="empty">자료가 없습니다.</div>`;
    return;
  }
  container.innerHTML = weeks.map(w => {
    const items = w.items || [];
    if (!items.length) return "";
    return `
      <details class="week" data-week-id="${w.id}" ${w.week_position <= 4 ? "open" : ""}>
        <summary class="week__head">
          <span class="week__title">${escapeHTML(w.title)}</span>
          <span class="week__meta">${items.length}개 항목</span>
          <i class="week__chev" data-lucide="chevron-down"></i>
        </summary>
        <ul class="filelist">
          ${items.map(it => renderItem(it)).join("")}
        </ul>
      </details>
    `;
  }).join("");
  if (window.lucide) lucide.createIcons();

  $$('.fileitem', container).forEach(li => {
    const fid = li.dataset.fileId;
    if (fid) li.addEventListener("click", () => openFile(fid));
  });
  $$('.weekitem--toggle', container).forEach(li => {
    li.addEventListener("click", e => {
      if (e.target.closest("a")) return;
      li.classList.toggle("is-open");
    });
  });
}

function renderItem(it) {
  // ExternalTool 자료
  if (it.type === "ExternalTool" && it.file) {
    const f = it.file;
    return `
      <li class="fileitem" data-file-id="${f.id}" title="탐색기에서 위치 열기">
        <span class="fileitem__icon"><i data-lucide="${iconForFile(f.file_name, f.content_type)}"></i></span>
        <div class="fileitem__body">
          <div class="fileitem__title">${escapeHTML(it.title)}</div>
          <div class="fileitem__sub">
            <span class="mono">${escapeHTML(f.file_name)}</span>
            <span class="dot-sep"></span>
            <span>${fmtBytes(f.file_size)}</span>
            <span class="dot-sep"></span>
            <span>${fmtRel(f.downloaded_at)}</span>
          </div>
        </div>
        <button class="iconbtn" data-action="open-file" title="파일 위치 열기">
          <i data-lucide="folder-open"></i>
        </button>
      </li>`;
  }

  const meta = itemMeta(it);
  const hasBody = it.description && it.description.trim();
  const cls = `fileitem weekitem ${hasBody ? "weekitem--toggle" : ""}`;
  return `
    <li class="${cls}">
      <span class="fileitem__icon weekitem__icon--${itemKind(it.type)}">
        <i data-lucide="${itemIcon(it.type)}"></i>
      </span>
      <div class="fileitem__body">
        <div class="fileitem__title">
          <span class="weekitem__type-label">${itemTypeLabel(it.type)}</span>
          ${escapeHTML(it.title)}
        </div>
        <div class="fileitem__sub">${meta}</div>
        ${hasBody ? `<div class="weekitem__desc">${it.description}</div>` : ""}
      </div>
      ${it.html_url ? `<a class="iconbtn" href="${escapeHTML(it.html_url)}" target="_blank" rel="noopener" title="LMS에서 보기" onclick="event.stopPropagation()">
        <i data-lucide="external-link"></i></a>` : ""}
    </li>`;
}

function itemKind(type) {
  return ({
    Assignment: "amber",
    Quiz: "purple",
    Discussion: "teal",
    Page: "blue",
    ExternalTool: "blue",
    ExternalUrl: "emerald",
  })[type] || "blue";
}
function itemIcon(type) {
  return ({
    Assignment: "clipboard-list",
    Quiz: "help-circle",
    Discussion: "message-square",
    Page: "file",
    ExternalTool: "puzzle",
    ExternalUrl: "link",
  })[type] || "circle";
}
function itemTypeLabel(type) {
  return ({
    Assignment: "과제",
    Quiz: "퀴즈",
    Discussion: "토론",
    Page: "페이지",
    ExternalTool: "자료",
    ExternalUrl: "링크",
  })[type] || type;
}
function itemMeta(it) {
  const parts = [];
  if (it.due_at) parts.push(`마감 <span class="mono">${fmtDateTime(it.due_at)}</span>`);
  if (it.points_possible != null) parts.push(`${it.points_possible}점`);
  if (!parts.length && it.type === "ExternalTool") parts.push("LMS에서 열기");
  if (!parts.length && it.type === "Page") parts.push("페이지");
  return parts.join(" <span class=\"dot-sep\"></span> ") || "";
}

async function openFile(id) {
  try {
    await jpost(`/files/${id}/open`);
    toast({ title: "탐색기 열림", message: "" });
  } catch (e) {
    toast({ title: "열기 실패", message: String(e), kind: "fail" });
  }
}

function renderCourseAssignments(list) {
  const tbody = $('[data-bind="course.assignments"]');
  if (!tbody) return;
  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-row">과제가 없습니다.</td></tr>`;
    return;
  }
  tbody.innerHTML = list.map(a => {
    const b = dayBadge(a.days_left);
    const status = a.submitted
      ? '<span class="badge badge--success">제출 완료</span>'
      : '<span class="badge badge--soft">제출 안 함</span>';
    const link = a.html_url
      ? `<a href="${escapeHTML(a.html_url)}" target="_blank" rel="noopener">${escapeHTML(a.title)}</a>`
      : escapeHTML(a.title);
    return `
      <tr>
        <td>${link}</td>
        <td><span class="mono">${fmtDateTime(a.due_at)}</span></td>
        <td><span class="badge ${b.cls}">${b.text}</span></td>
        <td>${status}</td>
      </tr>`;
  }).join("");
}

function renderCourseAnnouncements(items) {
  const ul = $('[data-bind="course.announcements"]');
  if (!ul) return;
  if (!items.length) {
    ul.innerHTML = `<li class="feed__item"><div class="feed__body">
      <div class="feed__sub">공지가 없습니다.</div></div></li>`;
    return;
  }
  ul.innerHTML = items.map(a => `
    <li class="feed__item">
      <span class="feed__icon feed__icon--blue"><i data-lucide="megaphone"></i></span>
      <div class="feed__body">
        <div class="feed__title">${escapeHTML(a.title)}</div>
        <div class="feed__sub">
          <span>${fmtDateTime(a.posted_at)}</span>
          ${a.has_attachments ? '<span class="dot-sep"></span><span class="mono">첨부 있음 — _공지사항/ 폴더에 저장</span>' : ''}
        </div>
      </div>
      ${a.html_url ? `<a class="iconbtn" href="${escapeHTML(a.html_url)}" target="_blank" rel="noopener" title="LMS에서 보기">
                       <i data-lucide="external-link"></i></a>` : ''}
    </li>
  `).join("");
  if (window.lucide) lucide.createIcons();
}

function bindOpenCanvas(subjectId) {
  const btn = $('[data-action="open-canvas"]');
  if (btn) btn.addEventListener("click", () => {
    window.open(`https://lms.suwon.ac.kr/courses/${subjectId}`, "_blank");
  });
}

function bindOpenCourseFolder(items) {
  const btn = $('[data-action="open-course-folder"]');
  if (!btn) return;
  const anyFile = (items || [])
    .map(it => it.file).find(f => f && f.local_path);
  if (!anyFile) {
    btn.disabled = true;
    return;
  }
  const parts = anyFile.local_path.split(/[\\/]/);
  const folderPath = parts.slice(0, -2).join("\\");
  btn.addEventListener("click", async () => {
    try {
      await jpost("/files/open-folder", { path: folderPath });
    } catch (e) {
      toast({ title: "열기 실패", message: String(e), kind: "fail" });
    }
  });
}

// ---------- 드래그·드롭 업로드 ----------

function bindDragDrop() {
  const main = document.querySelector(".main");
  if (!main) return;

  let dragCounter = 0;
  let overlay = document.querySelector(".drop-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "drop-overlay";
    overlay.innerHTML = `<div class="drop-overlay__inner">
      <i data-lucide="upload-cloud"></i>
      <div class="drop-overlay__title">놓으면 업로드</div>
      <div class="drop-overlay__sub">주차 위에 놓으면 그 주차로, 빈 공간이면 <code>_수동자료/</code></div>
    </div>`;
    document.body.appendChild(overlay);
    if (window.lucide) lucide.createIcons();
  }

  function setHighlight(el, on) {
    if (!el) return;
    el.classList.toggle("is-droptarget", on);
  }

  let currentTarget = null;

  window.addEventListener("dragenter", (e) => {
    if (!e.dataTransfer || !e.dataTransfer.types.includes("Files")) return;
    e.preventDefault();
    dragCounter++;
    overlay.classList.add("is-active");
  });

  window.addEventListener("dragover", (e) => {
    if (!e.dataTransfer || !e.dataTransfer.types.includes("Files")) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";

    const wk = e.target.closest("details.week");
    if (currentTarget && currentTarget !== wk) setHighlight(currentTarget, false);
    currentTarget = wk;
    if (wk) setHighlight(wk, true);
  });

  window.addEventListener("dragleave", (e) => {
    if (!e.dataTransfer) return;
    dragCounter = Math.max(0, dragCounter - 1);
    if (dragCounter === 0) {
      overlay.classList.remove("is-active");
      setHighlight(currentTarget, false);
      currentTarget = null;
    }
  });

  window.addEventListener("drop", async (e) => {
    if (!e.dataTransfer || !e.dataTransfer.files.length) return;
    e.preventDefault();
    dragCounter = 0;
    overlay.classList.remove("is-active");
    setHighlight(currentTarget, false);

    const target = currentTarget;
    currentTarget = null;

    const weekId = target ? target.dataset.weekId : null;
    const files = [...e.dataTransfer.files];

    for (const f of files) {
      await uploadOne(f, weekId);
    }
    await loadCourse();
  });
}

async function uploadOne(file, weekId) {
  const fd = new FormData();
  fd.append("upload", file);
  if (weekId) fd.append("week_id", weekId);
  try {
    const r = await fetch(`${API}/courses/${courseId}/upload`, {
      method: "POST", body: fd,
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    toast({
      title: "업로드 완료",
      message: data.week ? `${data.week.title} — ${file.name}` : `_수동자료/ — ${file.name}`,
    });
  } catch (err) {
    toast({ title: "업로드 실패", message: `${file.name}: ${err}`, kind: "fail" });
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  await loadCourse();
  bindDragDrop();
});
