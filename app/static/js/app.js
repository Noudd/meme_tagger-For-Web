/**
 * Meme Tagger 前端主脚本
 * 负责：目录扫描、打标签任务触发、SSE 进度监听、图片列表渲染与分页、
 * 单条/批量删除、数据库导出、Toast 通知、Lightbox 预览等交互逻辑
 */

// ========== 全局状态 ==========
let scannedFiles = [];       // 当前扫描到的文件路径列表
let currentPage = 1;         // 图片列表当前页码
let activeEventSource = null; // 当前活跃的 SSE 连接实例
let selectedMemes = new Set(); // 批量删除选中的 meme ID 集合
let autoRefreshTimer = null;  // 自动刷新定时器 ID

// ========== 通用工具函数 ==========

/**
 * 显示 Toast 通知消息
 * @param {string} message - 提示内容
 * @param {string} type - 类型：success/error/warning/info
 * @param {number} duration - 显示时长（毫秒）
 */
function toast(message, type = "info", duration = 4000) {
    const container = document.getElementById("toast-container");
    const icons = { success: "\u2713", error: "\u2717", warning: "\u26a0", info: "\u2139" };
    const el = document.createElement("div");
    el.className = `toast-custom toast-${type}`;
    el.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span>${escapeHtml(message)}</span>`;
    container.appendChild(el);

    setTimeout(() => {
        el.classList.add("toast-removing");
        el.addEventListener("animationend", () => el.remove());
    }, duration);
}

/** HTML 转义，防止 XSS 注入 */
function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

/** 防抖函数：延迟执行，避免高频触发（如搜索输入） */
function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

/**
 * 显示确认对话框（替代原生 confirm）
 * @returns {Promise<boolean>} 用户确认返回 true，取消返回 false
 */
function showConfirm(title, message) {
    return new Promise((resolve) => {
        const overlay = document.createElement("div");
        overlay.className = "confirm-modal-overlay";
        overlay.innerHTML = `
            <div class="confirm-modal">
                <h6>${escapeHtml(title)}</h6>
                <p>${escapeHtml(message)}</p>
                <div class="modal-actions">
                    <button class="btn btn-secondary btn-sm" data-action="cancel">取消</button>
                    <button class="btn btn-danger btn-sm" data-action="confirm">删除</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);

        overlay.addEventListener("click", (e) => {
            if (e.target === overlay || e.target.dataset.action === "cancel") {
                overlay.remove();
                resolve(false);
            }
            if (e.target.dataset.action === "confirm") {
                overlay.remove();
                resolve(true);
            }
        });

        document.addEventListener("keydown", function escHandler(e) {
            if (e.key === "Escape") {
                overlay.remove();
                document.removeEventListener("keydown", escHandler);
                resolve(false);
            }
        });
    });
}

/**
 * 打开图片 Lightbox 全屏预览
 * @param {string} filePath - 图片文件路径
 */
function openLightbox(filePath) {
    const existing = document.querySelector(".lightbox-overlay");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.className = "lightbox-overlay";
    overlay.innerHTML = `
        <button class="lightbox-close">&times;</button>
        <img src="/api/file_preview?path=${encodeURIComponent(filePath)}" alt="预览">
        <div class="lightbox-info">${escapeHtml(filePath)}</div>`;
    document.body.appendChild(overlay);

    const close = () => overlay.remove();
    overlay.addEventListener("click", (e) => {
        if (e.target === overlay || e.target.classList.contains("lightbox-close")) close();
    });
    document.addEventListener("keydown", function escHandler(e) {
        if (e.key === "Escape") { close(); document.removeEventListener("keydown", escHandler); }
    });
}

// ========== 核心业务功能 ==========

/**
 * 扫描目录：向后端发送目录路径，获取其中的图片文件列表
 */
function scanDirectory() {
    const directory = document.getElementById("directory-input").value.trim();
    if (!directory) {
        toast("请输入目录路径", "warning");
        return;
    }

    const btn = document.getElementById("scan-btn");
    btn.disabled = true;
    btn.textContent = "扫描中...";

    fetch("/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ directory }),
    })
        .then((r) => {
            if (!r.ok) return r.json().then((d) => Promise.reject(d));
            return r.json();
        })
        .then((data) => {
            if (data.error) {
                document.getElementById("scan-result").innerHTML =
                    `<span class="text-danger">${escapeHtml(data.error)}</span>`;
                toast(data.error, "error");
                return;
            }
            scannedFiles = data.files;
            document.getElementById("scan-result").innerHTML =
                `<span class="text-success">在 ${escapeHtml(data.directory)} 中找到 ${data.count} 张图片</span>`;
            document.getElementById("tag-btn").disabled = data.count === 0;
            toast(`找到 ${data.count} 张图片`, "success");
            loadMemes();
            loadStats();
        })
        .catch((err) => {
            const msg = err.error || err.message || "扫描失败";
            document.getElementById("scan-result").innerHTML =
                `<span class="text-danger">${escapeHtml(msg)}</span>`;
            toast(msg, "error");
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = "扫描";
        });
}

/**
 * 启动打标签任务：将扫描到的文件列表提交给后端，触发 AI 分析
 */
function startTagging() {
    if (scannedFiles.length === 0) {
        toast("没有要打标签的文件，请先扫描目录。", "warning");
        return;
    }

    const btn = document.getElementById("tag-btn");
    btn.disabled = true;
    btn.textContent = "打标签中...";

    fetch("/api/tag", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files: scannedFiles }),
    })
        .then((r) => {
            if (!r.ok) return r.json().then((d) => Promise.reject(d));
            return r.json();
        })
        .then((data) => {
            if (data.error) {
                toast(data.error, "error");
                btn.disabled = false;
                btn.textContent = "全部打标签";
                return;
            }
            toast(`已开始为 ${data.total} 个文件打标签`, "info");
            subscribeProgress(data.task_id);
        })
        .catch((err) => {
            toast("启动打标签失败：" + (err.error || err.message), "error");
            btn.disabled = false;
            btn.textContent = "全部打标签";
        });
}

/**
 * 订阅 SSE 进度流：建立 EventSource 连接，实时接收任务进度更新
 * @param {string} taskId - 打标签任务 ID
 */
function subscribeProgress(taskId) {
    if (activeEventSource) {
        activeEventSource.close();
    }

    const section = document.getElementById("progress-section");
    section.classList.remove("d-none");
    document.getElementById("progress-errors").innerHTML = "";

    const evtSource = new EventSource(`/api/progress_stream/${taskId}`);
    activeEventSource = evtSource;

    evtSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "heartbeat") return;

        updateProgressUI(data);

        if (data.errors && data.errors.length > 0) {
            const errDiv = document.getElementById("progress-errors");
            errDiv.innerHTML = data.errors.map(
                (e) => `<div class="small text-danger text-truncate" title="${escapeHtml(e.error)}">${escapeHtml(e.file)}: ${escapeHtml(e.error)}</div>`
            ).join("");
        }

        if (data.status === "completed" || data.status === "error") {
            evtSource.close();
            activeEventSource = null;
            finishTagging(data);
        }
    };

    evtSource.onerror = () => {
        evtSource.close();
        activeEventSource = null;
        finishTagging(null);
    };
}

/** 更新进度条 UI 显示 */
function updateProgressUI(data) {
    const total = data.total || 1;
    const completed = data.completed || 0;
    const pct = Math.round((completed / total) * 100);

    document.getElementById("progress-bar").style.width = pct + "%";
    document.getElementById("progress-text").textContent =
        `${completed} / ${total} 个文件已处理`;
    document.getElementById("progress-pct").textContent = `${pct}%`;
    document.getElementById("current-file").textContent = data.current_file || "";
}

/** 打标签任务完成后的收尾处理：恢复按钮状态、隐藏进度条、刷新列表 */
function finishTagging(data) {
    const btn = document.getElementById("tag-btn");
    btn.disabled = false;
    btn.textContent = "全部打标签";

    if (data) {
        const errors = data.errors || [];
        if (data.status === "completed" && errors.length === 0) {
            toast(`全部 ${data.total} 个文件打标签成功`, "success");
        } else if (errors.length > 0) {
            toast(`完成，但有 ${errors.length} 个错误`, "warning");
        }
    } else {
        toast("打标签连接断开", "error");
    }

    setTimeout(() => {
        document.getElementById("progress-section").classList.add("d-none");
    }, 3000);

    loadMemes();
    loadStats();
}

/** 导出数据库：下载当前 SQLite 数据库文件 */
function exportDatabase() {
    const btn = document.getElementById("export-btn");
    btn.disabled = true;
    btn.textContent = "导出中...";

    fetch("/api/export")
        .then((r) => {
            if (!r.ok) throw new Error("导出失败");
            return r.blob();
        })
        .then((blob) => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "meme_tagger_export.db";
            a.click();
            URL.revokeObjectURL(url);
            toast("数据库已导出", "success");
        })
        .catch((err) => {
            toast("导出失败：" + err.message, "error");
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = "导出数据库";
        });
}

/** 显示骨架屏加载占位符 */
function showSkeleton(count = 8) {
    const container = document.getElementById("memes-container");
    let html = "";
    for (let i = 0; i < count; i++) {
        html += `
            <div class="col-md-4 col-lg-3">
                <div class="card bg-secondary text-light h-100">
                    <div class="skeleton" style="height:180px;"></div>
                    <div class="card-body p-2">
                        <div class="skeleton mb-2" style="height:14px;width:70%;"></div>
                        <div class="skeleton mb-2" style="height:20px;width:40%;"></div>
                        <div class="skeleton mb-2" style="height:18px;width:90%;"></div>
                        <div class="skeleton" style="height:32px;"></div>
                    </div>
                </div>
            </div>`;
    }
    container.innerHTML = html;
}

// ========== 图片列表渲染与分页 ==========

/**
 * 加载图片列表：请求后端分页数据并渲染
 * @param {number} page - 页码
 */
function loadMemes(page = 1) {
    currentPage = page;

    const status = document.getElementById("status-filter").value;
    const search = document.getElementById("search-input").value;

    showSkeleton();

    const params = new URLSearchParams({ page, per_page: 20 });
    if (status) params.set("status", status);
    if (search) params.set("search", search);

    fetch(`/api/memes?${params}`)
        .then((r) => {
            if (!r.ok) throw new Error("加载图片列表失败");
            return r.json();
        })
        .then((data) => {
            renderMemes(data.memes);
            renderPagination(data);
        })
        .catch(() => {
            document.getElementById("memes-container").innerHTML =
                '<div class="col-12"><div class="empty-state"><div class="empty-icon">&#9888;</div><div class="empty-title">加载图片列表失败</div><div class="empty-hint">请检查服务器连接后重试</div></div></div>';
        });
}

/**
 * 渲染图片卡片列表：将 meme 数据生成 HTML 卡片并插入 DOM
 * @param {Array} memes - meme 对象数组
 */
function renderMemes(memes) {
    const container = document.getElementById("memes-container");

    if (memes.length === 0) {
        const filter = document.getElementById("status-filter").value;
        const search = document.getElementById("search-input").value;

        if (!filter && !search) {
            container.innerHTML =
                '<div class="col-12"><div class="empty-state"><div class="empty-icon">&#128444;</div><div class="empty-title">暂无图片</div><div class="empty-hint">扫描目录后点击"全部打标签"开始使用</div></div></div>';
        } else {
            container.innerHTML =
                '<div class="col-12"><div class="empty-state"><div class="empty-icon">&#128269;</div><div class="empty-title">未找到匹配的图片</div><div class="empty-hint">请调整筛选条件或搜索词</div></div></div>';
        }
        return;
    }

    container.innerHTML = memes
        .map((m) => {
            const statusBadge = {
                pending: "secondary",
                processing: "warning",
                completed: "success",
                error: "danger",
            }[m.status] || "secondary";

            const tagsHtml = m.tags.length
                ? m.tags.map(
                    (t) =>
                        `<span class="badge bg-info me-1 mb-1 tag-badge">${escapeHtml(t.name)} <small class="opacity-75">${(t.confidence * 100).toFixed(0)}%</small></span>`
                ).join("")
                : '<span class="text-muted small">无标签</span>';

            const filePath = m.file_path.replace(/\\/g, "/");
            const escapedPath = filePath.replace(/'/g, "\\'");
            const checked = selectedMemes.has(m.id) ? "checked" : "";
            const errorMsg = m.error_message
                ? `<div class="small text-danger mb-1 text-truncate" title="${escapeHtml(m.error_message)}">${escapeHtml(m.error_message)}</div>`
                : "";

            return `
                <div class="col-md-4 col-lg-3">
                    <div class="card text-light h-100">
                        <div style="position:relative;">
                            <img src="/api/file_preview?path=${encodeURIComponent(filePath)}"
                                 class="card-img-top" style="height:180px;width:100%;object-fit:cover;"
                                 loading="lazy"
                                 onclick="openLightbox('${escapedPath}')"
                                 onerror="this.style.display='none';this.nextElementSibling.style.display='flex';"
                                 alt="${escapeHtml(m.file_name)}">
                            <div class="skeleton" style="height:180px;display:none;align-items:center;justify-content:center;color:var(--text-muted);font-size:0.85rem;">
                                无预览
                            </div>
                            <div style="position:absolute;top:6px;left:6px;">
                                <input type="checkbox" class="form-check-input meme-checkbox"
                                       data-id="${m.id}" ${checked}
                                       style="background-color:var(--surface-1);border-color:var(--border);">
                            </div>
                        </div>
                        <div class="card-body p-2">
                            <div class="small text-truncate mb-1 fw-medium" title="${escapeHtml(filePath)}">${escapeHtml(m.file_name)}</div>
                            <span class="badge bg-${statusBadge} mb-2">${m.status}</span>
                            ${errorMsg}
                            <div class="mb-2" style="max-height:68px;overflow-y:auto;">${tagsHtml}</div>
                            <div class="d-flex gap-1">
                                <button class="btn btn-outline-info btn-sm flex-shrink-0" style="width:32px;padding:4px;"
                                        onclick="openLightbox('${escapedPath}')" title="预览">
                                    &#9744;
                                </button>
                                <button class="btn btn-outline-danger btn-sm flex-grow-1"
                                        onclick="deleteMeme(${m.id})">删除</button>
                            </div>
                        </div>
                    </div>
                </div>`;
        })
        .join("");

    document.querySelectorAll(".meme-checkbox").forEach((cb) => {
        cb.addEventListener("change", (e) => {
            const id = parseInt(e.target.dataset.id);
            if (e.target.checked) selectedMemes.add(id);
            else selectedMemes.delete(id);
            updateBatchDeleteBtn();
        });
    });
}

/** 更新批量删除按钮的显示状态和文案 */
function updateBatchDeleteBtn() {
    const btn = document.getElementById("batch-delete-btn");
    if (selectedMemes.size > 0) {
        btn.classList.remove("d-none");
        btn.textContent = `删除选中 (${selectedMemes.size})`;
    } else {
        btn.classList.add("d-none");
    }
}

/** 批量删除选中的图片记录 */
async function batchDelete() {
    if (selectedMemes.size === 0) return;
    const confirmed = await showConfirm(
        "批量删除",
        `确定要删除 ${selectedMemes.size} 张图片吗？此操作不可撤销。`
    );
    if (!confirmed) return;

    const ids = [...selectedMemes];
    let deleted = 0;
    let failed = 0;

    for (const id of ids) {
        try {
            const r = await fetch(`/api/memes/${id}`, { method: "DELETE" });
            if (r.ok) deleted++;
            else failed++;
        } catch {
            failed++;
        }
    }

    selectedMemes.clear();
    updateBatchDeleteBtn();

    if (failed === 0) {
        toast(`已删除 ${deleted} 张图片`, "success");
    } else {
        toast(`已删除 ${deleted} 张，${failed} 张失败`, "warning");
    }

    loadMemes(currentPage);
    loadStats();
}

/** 渲染分页导航组件 */
function renderPagination(data) {
    const ul = document.getElementById("pagination");
    if (data.pages <= 1) {
        ul.innerHTML = "";
        return;
    }

    let html = "";
    const start = Math.max(1, data.page - 2);
    const end = Math.min(data.pages, data.page + 2);

    if (start > 1) {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="loadMemes(1);return false;">1</a></li>`;
        if (start > 2) html += `<li class="page-item disabled"><span class="page-link">&hellip;</span></li>`;
    }

    for (let i = start; i <= end; i++) {
        html +=
            `<li class="page-item ${i === data.page ? "active" : ""}">` +
            `<a class="page-link" href="#" onclick="loadMemes(${i});return false;">${i}</a></li>`;
    }

    if (end < data.pages) {
        if (end < data.pages - 1) html += `<li class="page-item disabled"><span class="page-link">&hellip;</span></li>`;
        html += `<li class="page-item"><a class="page-link" href="#" onclick="loadMemes(${data.pages});return false;">${data.pages}</a></li>`;
    }

    ul.innerHTML = html;
}

/** 删除单条图片记录（带确认弹窗） */
async function deleteMeme(id) {
    const confirmed = await showConfirm("删除图片", "确定要删除这张图片吗？");
    if (!confirmed) return;

    try {
        const r = await fetch(`/api/memes/${id}`, { method: "DELETE" });
        const data = await r.json();
        if (!r.ok) throw new Error(data.error || "删除失败");
        selectedMemes.delete(id);
        updateBatchDeleteBtn();
        toast("图片已删除", "success");
        loadMemes(currentPage);
        loadStats();
    } catch (err) {
        toast(err.message, "error");
    }
}

// ========== 统计与自动刷新 ==========

/** 加载各状态的统计数据并更新统计栏和导航栏 */
function loadStats() {
    fetch("/api/stats")
        .then((r) => r.json())
        .then((counts) => {
            renderStatsBar(counts);
            renderNavStats(counts);
        })
        .catch(() => {});
}

/** 渲染统计栏：显示总计、已完成、处理中、待处理、错误数量 */
function renderStatsBar(counts) {
    const bar = document.getElementById("stats-bar");
    const items = [
        { label: "总计", count: sumCounts(counts), color: "var(--accent)" },
        { label: "已完成", count: counts.completed || 0, color: "var(--success)" },
        { label: "处理中", count: counts.processing || 0, color: "var(--warning)" },
        { label: "待处理", count: counts.pending || 0, color: "var(--text-muted)" },
        { label: "错误", count: counts.error || 0, color: "var(--danger)" },
    ];

    bar.innerHTML = items
        .map(
            (item) =>
                `<div class="stat-chip">
                    <span class="stat-dot" style="background:${item.color};"></span>
                    ${item.label}
                    <span class="stat-count">${item.count}</span>
                </div>`
        )
        .join("");
}

/** 渲染导航栏统计摘要 */
function renderNavStats(counts) {
    const nav = document.getElementById("navbar-stats");
    const total = sumCounts(counts);
    const completed = counts.completed || 0;
    const processing = counts.processing || 0;
    nav.innerHTML = `
        <span class="small text-secondary">${completed} / ${total} 已完成</span>
        ${processing > 0 ? `<span class="badge bg-warning text-dark">${processing} 处理中</span>` : ""}`;
}

/** 求和辅助函数 */
function sumCounts(counts) {
    return Object.values(counts).reduce((a, b) => a + b, 0);
}

/** 启动自动刷新：当有处理中的任务时，每 5 秒轮询更新列表和统计 */
function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshTimer = setInterval(() => {
        const hasProcessing = [...document.querySelectorAll(".badge.bg-warning")].some(
            (b) => b.textContent.trim() === "processing"
        );
        if (hasProcessing || activeEventSource) {
            loadMemes(currentPage);
            loadStats();
        }
    }, 5000);
}

/** 停止自动刷新定时器 */
function stopAutoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
    }
}

// ========== 滚动与初始化 ==========

/** 监听滚动事件，控制"回到顶部"按钮的显示/隐藏 */
function handleScroll() {
    const btn = document.getElementById("scroll-top-btn");
    if (window.scrollY > 400) {
        btn.classList.add("visible");
    } else {
        btn.classList.remove("visible");
    }
}

/** 搜索防抖包装：输入 300ms 后才触发搜索请求 */
const debouncedSearch = debounce(() => loadMemes(), 300);

/** 页面加载完成后初始化：加载数据、启动自动刷新、绑定事件监听 */
document.addEventListener("DOMContentLoaded", () => {
    loadMemes();
    loadStats();
    startAutoRefresh();

    document.getElementById("search-input").addEventListener("input", debouncedSearch);

    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("beforeunload", () => {
        stopAutoRefresh();
        if (activeEventSource) activeEventSource.close();
    });
});
