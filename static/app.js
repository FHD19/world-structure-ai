/**
 * 世界结构认知AI — 前端交互逻辑 v3
 * 适配精简版JSON schema，防止8192 token截断
 */

// ===== 初始化 =====
document.addEventListener("DOMContentLoaded", () => {
    setToday();
    initTabs();
    initDailyTab();
    initManualTab();
    initHistoryTab();
    initGlobalChat();
});

let currentReport = null;
let activeCategory = "全部";

// ===== 日期 =====
function setToday() {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    document.getElementById("headerDate").textContent = `${y}年${m}月${d}日`;
}

// ===== 主标签切换 =====
function initTabs() {
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.tab;
            document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            tab.classList.add("active");
            document.getElementById(`tab-${target}`).classList.add("active");
            if (target === "history") loadHistory();
        });
    });
}

// ===== 今日分析 =====
function initDailyTab() {
    document.getElementById("btnAnalyze").addEventListener("click", runDailyAnalysis);
}

async function runDailyAnalysis() {
    const btn = document.getElementById("btnAnalyze");
    const status = document.getElementById("statusDaily");
    const content = document.getElementById("dailyContent");

    btn.disabled = true;
    btn.textContent = "分析中...";
    status.textContent = "";
    content.innerHTML = '<div class="loading">正在从多国新闻源抓取并分析今日要闻，预计需要30-60秒</div>';

    try {
        const resp = await fetch("/api/analyze", { method: "POST" });
        const data = await resp.json();
        if (!data.success) {
            content.innerHTML = `<p class="placeholder">出错了: ${esc(data.error)}</p>`;
            return;
        }

        const report = data.report;
        currentReport = report;
        activeCategory = "全部";

        status.textContent = data.cached
            ? `(缓存) ${report.news_count}条新闻 | 已分析`
            : `(实时) ${report.news_count}条新闻 | 已完成分析`;

        renderDailyReport(report);

    } catch (err) {
        content.innerHTML = `<p class="placeholder">请求失败: ${esc(err.message)}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = "刷新分析";
    }
}

// ===== 核心渲染 =====
function renderDailyReport(report) {
    const container = document.getElementById("dailyContent");
    const analysis = report.analysis;

    if (analysis.parse_error || analysis.raw_response) {
        container.innerHTML = `
            <div class="analysis-block">
                <h3>分析结果（原始格式）</h3>
                <div class="raw-block">${esc(analysis.raw_response || JSON.stringify(analysis, null, 2))}</div>
            </div>`;
        return;
    }

    let html = "";

    // ---- 概览 ----
    if (analysis.overview) {
        html += `<div class="analysis-block">
            <h3>今日概览</h3>
            <div class="overview-text">${esc(analysis.overview)}</div>
        </div>`;
    }

    // ---- 分类导航 + 新闻列表 ----
    if (analysis.facts && analysis.facts.length) {
        const categories = collectCategories(analysis.facts);
        html += `<nav class="category-nav" id="categoryFilters">
            <div class="cat-tabs">`;
        categories.forEach(cat => {
            const active = cat === "全部" ? " cat-tab-active" : "";
            html += `<button class="cat-tab${active}" data-cat="${esc(cat)}">${esc(cat)}</button>`;
        });
        html += `</div></nav>`;

        html += `<div class="analysis-block"><h3>新闻事实与多方视角</h3><div id="factsContainer">`;
        analysis.facts.forEach((fact, idx) => {
            html += renderFactItem(fact, idx);
        });
        html += `</div></div>`;
    }

    // ---- 叙事总结 ----
    if (analysis.narrative_summary) {
        const ns = analysis.narrative_summary;
        html += `<div class="analysis-block"><h3>叙事规律总结</h3>`;
        html += `<div class="narrative-grid">`;
        html += renderNarrativeCard("中国媒体强调", ns.cn_focus);
        html += renderNarrativeCard("美国媒体强调", ns.us_focus);
        html += `</div>`;
        if (ns.divergence) {
            html += `<div class="struct-section" style="margin-top:8px"><h4>最主要叙事分歧</h4><p style="font-size:14px;color:var(--text)">${esc(ns.divergence)}</p></div>`;
        }
        html += `</div>`;
    }

    // ---- 深层结构分析 ----
    if (analysis.structural_analysis) {
        const sa = analysis.structural_analysis;
        html += `<div class="analysis-block"><h3>深层结构分析</h3>`;
        html += renderStructSection("核心结构因素", sa.key_factors);
        if (sa.who_benefits) {
            html += `<div class="risk-card"><h4>谁在获益</h4><p>${esc(sa.who_benefits)}</p></div>`;
        }
        if (sa.who_loses) {
            html += `<div class="risk-card"><h4>谁在受损</h4><p>${esc(sa.who_loses)}</p></div>`;
        }
        html += `</div>`;
    }

    // ---- 风险评估 ----
    if (analysis.risk_assessment) {
        const ra = analysis.risk_assessment;
        html += `<div class="analysis-block"><h3>风险评估</h3>`;
        html += `<div class="risk-card"><h4>升级可能性</h4><p>${esc(ra.escalation || "--")}</p></div>`;
        html += `<div class="risk-card"><h4>经济/市场影响</h4><p>${esc(ra.economic || "--")}</p></div>`;
        html += `<div class="risk-card"><h4>对普通人生活的影响</h4><p>${esc(ra.public || "--")}</p></div>`;
        if (ra.watch && ra.watch.length) {
            html += `<div class="struct-section"><h4>持续关注点</h4><ul>${ra.watch.map(p => `<li>${esc(p)}</li>`).join("")}</ul></div>`;
        }
        html += `</div>`;
    }

    // ---- AI/科技 ----
    if (analysis.ai_tech && analysis.ai_tech.length) {
        html += `<div class="analysis-block"><h3>AI与科技动态</h3>`;
        analysis.ai_tech.forEach(item => {
            html += `<div class="news-item tech-item">
                <div class="news-title">${esc(item.item || "")}</div>
                ${item.impact ? `<div class="news-summary">影响: ${esc(item.impact)}</div>` : ""}
            </div>`;
        });
        html += `</div>`;
    }

    // ---- 媒体偏向 ----
    if (analysis.media_bias && analysis.media_bias.length) {
        html += `<div class="analysis-block"><h3>媒体偏向检测</h3>`;
        analysis.media_bias.forEach(item => {
            const levelClass = item.level === "高" ? "bias-level-high"
                : item.level === "中" ? "bias-level-med" : "bias-level-low";
            html += `<div class="bias-item ${levelClass}">
                <div class="bias-source">${esc(item.source || "")} — 偏向等级: ${esc(item.level || "--")}</div>
                <div class="bias-detail">${esc(item.issue || "")}</div>
            </div>`;
        });
        html += `</div>`;
    }

    // ---- 推荐阅读 ----
    if (analysis.reading && analysis.reading.length) {
        html += `<div class="analysis-block"><h3>建议深入了解的方向</h3><ul class="reading-list">`;
        analysis.reading.forEach(r => {
            html += `<li>${esc(r)}</li>`;
        });
        html += `</ul></div>`;
    }

    container.innerHTML = html;

    initCategoryFilters();
}

// ===== 单条新闻渲染 =====
function renderFactItem(fact, idx) {
    const catClass = getCategoryClass(fact.category);

    let html = `
    <div class="news-item fact-card" data-category="${esc(fact.category || '')}" id="news-${idx}">
        <div class="news-header">
            <span class="cat-badge ${catClass}">${esc(fact.category || "未分类")}</span>
            <span class="news-title">${esc(fact.title)}</span>
        </div>

        <div class="fact-body">
            <div class="fact-section">
                <p>${esc(fact.detail || "")}</p>
            </div>`;

    // 多方视角
    html += `<div class="perspectives-block">
        <h5>多方视角对比</h5>
        <div class="perspective-grid">`;

    if (fact.cn_view) {
        html += `<div class="perspective-card china">
            <div class="perspective-label">中国视角</div>
            <p>${esc(fact.cn_view)}</p>
        </div>`;
    }
    if (fact.us_view) {
        html += `<div class="perspective-card us">
            <div class="perspective-label">美国视角</div>
            <p>${esc(fact.us_view)}</p>
        </div>`;
    }
    if (fact.local_view) {
        html += `<div class="perspective-card local">
            <div class="perspective-label">当事方视角</div>
            <p>${esc(fact.local_view)}</p>
        </div>`;
    }

    html += `</div></div></div>`;

    // AI追问
    html += renderNewsChat(idx, fact);
    html += `</div>`;

    return html;
}

// ===== 分类筛选 =====
function collectCategories(facts) {
    const seen = new Set();
    const cats = ["全部"];
    facts.forEach(f => {
        const c = f.category || "其他";
        if (!seen.has(c)) {
            seen.add(c);
            cats.push(c);
        }
    });
    return cats;
}

function getCategoryClass(cat) {
    const map = {
        "国际局势": "cat-politics",
        "军事安全": "cat-military",
        "经济财经": "cat-economy",
        "AI科技": "cat-tech",
        "娱乐文化": "cat-social",
        "社会民生": "cat-other",
    };
    return map[cat] || "cat-other";
}

function initCategoryFilters() {
    document.querySelectorAll(".cat-tab").forEach(btn => {
        btn.addEventListener("click", () => {
            activeCategory = btn.dataset.cat;
            document.querySelectorAll(".cat-tab").forEach(b => b.classList.remove("cat-tab-active"));
            btn.classList.add("cat-tab-active");
            filterFacts();
        });
    });
}

function filterFacts() {
    document.querySelectorAll(".fact-card").forEach(card => {
        if (activeCategory === "全部" || card.dataset.category === activeCategory) {
            card.style.display = "";
        } else {
            card.style.display = "none";
        }
    });
}

// ===== 新闻下AI追问对话框 =====
function renderNewsChat(idx, fact) {
    const context = JSON.stringify({
        title: fact.title || "",
        detail: fact.detail || "",
        cn_view: fact.cn_view || "",
        us_view: fact.us_view || "",
        local_view: fact.local_view || "",
        category: fact.category || "",
    });
    return `
    <div class="news-chat-toggle" data-idx="${idx}">追问AI - 对这条新闻有疑问？</div>
    <div class="news-chat-body" id="newsChatBody${idx}">
        <div class="news-chat-messages" id="newsChatMsgs${idx}"></div>
        <div class="news-chat-row">
            <input class="news-chat-input" id="newsChatInput${idx}" placeholder="输入你的问题...">
            <button class="news-chat-send" data-idx="${idx}" data-context='${escAttr(context)}'>发送</button>
        </div>
    </div>`;
}

function initNewsChatListeners() {
    document.querySelectorAll(".news-chat-toggle").forEach(toggle => {
        if (toggle.dataset.bound) return;
        toggle.dataset.bound = "1";
        toggle.addEventListener("click", () => {
            const idx = toggle.dataset.idx;
            const body = document.getElementById(`newsChatBody${idx}`);
            body.classList.toggle("open");
        });
    });

    document.querySelectorAll(".news-chat-send").forEach(btn => {
        if (btn.dataset.bound) return;
        btn.dataset.bound = "1";
        btn.addEventListener("click", async () => {
            const idx = btn.dataset.idx;
            const context = btn.dataset.context;
            const input = document.getElementById(`newsChatInput${idx}`);
            const question = input.value.trim();
            if (!question) return;

            const msgs = document.getElementById(`newsChatMsgs${idx}`);
            appendChatMsg(msgs, "user", question);
            input.value = "";
            appendChatMsg(msgs, "assistant", '<span class="loading" style="padding:0"></span>');

            try {
                const resp = await fetch("/api/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question, context }),
                });
                const data = await resp.json();
                msgs.lastElementChild.remove();
                if (data.success) {
                    appendChatMsg(msgs, "assistant", data.reply);
                } else {
                    appendChatMsg(msgs, "assistant", "抱歉，出错了: " + data.error);
                }
            } catch (err) {
                msgs.lastElementChild.remove();
                appendChatMsg(msgs, "assistant", "请求失败: " + err.message);
            }
        });
    });
}

// ===== 手动分析 =====
function initManualTab() {
    const btn = document.getElementById("btnAnalyzeSingle");
    btn.addEventListener("click", async () => {
        const title = document.getElementById("inputTitle").value.trim();
        const content = document.getElementById("inputContent").value.trim();
        const status = document.getElementById("statusManual");
        const result = document.getElementById("manualResult");

        if (!title) { status.textContent = "请输入新闻标题"; return; }

        btn.disabled = true;
        status.textContent = "分析中...";
        result.innerHTML = '<div class="loading">正在深度分析这条新闻</div>';

        try {
            const resp = await fetch("/api/analyze_single", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title, content }),
            });
            const data = await resp.json();
            if (!data.success) {
                result.innerHTML = `<p class="placeholder">出错了: ${esc(data.error)}</p>`;
                return;
            }
            status.textContent = "分析完成";
            renderManualResult(data.analysis);
        } catch (err) {
            result.innerHTML = `<p class="placeholder">请求失败: ${esc(err.message)}</p>`;
        } finally {
            btn.disabled = false;
        }
    });
}

function renderManualResult(analysis) {
    const container = document.getElementById("manualResult");
    if (analysis.parse_error || analysis.raw_response) {
        container.innerHTML = `<div class="analysis-block"><h3>分析结果</h3><div class="raw-block">${esc(analysis.raw_response || JSON.stringify(analysis, null, 2))}</div></div>`;
        return;
    }

    let html = "";
    if (analysis.fact_layer) {
        const fl = analysis.fact_layer;
        html += `<div class="analysis-block"><h3>事实层</h3>
            <div class="overview-text">${esc(fl.what_happened || "")}</div>`;
        if (fl.verified_facts && fl.verified_facts.length) {
            html += `<div class="struct-section"><h4>已确认事实</h4><ul>${fl.verified_facts.map(f => `<li>${esc(f)}</li>`).join("")}</ul></div>`;
        }
        if (fl.unclear_points && fl.unclear_points.length) {
            html += `<div class="struct-section"><h4>尚不明确</h4><ul>${fl.unclear_points.map(p => `<li>${esc(p)}</li>`).join("")}</ul></div>`;
        }
        html += `</div>`;
    }
    if (analysis.narrative_comparison) {
        const nc = analysis.narrative_comparison;
        html += `<div class="analysis-block"><h3>叙事对比</h3>
            <div class="risk-card"><h4>不同立场如何叙述</h4><p>${esc(nc.how_different_sides_would_frame || "")}</p></div>
            <div class="risk-card"><h4>叙事差异原因</h4><p>${esc(nc.why_they_narrate_differently || "")}</p></div>
        </div>`;
    }
    if (analysis.structural_factors) {
        const sf = analysis.structural_factors;
        html += `<div class="analysis-block"><h3>结构因素</h3>`;
        html += renderStructSection("深层利益", sf.underlying_interests);
        html += `<div class="struct-section"><h4>历史背景</h4><p style="font-size:14px;color:var(--text)">${esc(sf.historical_context || "")}</p></div>`;
        html += `<div class="struct-section"><h4>权力/利益格局</h4><p style="font-size:14px;color:var(--text)">${esc(sf.power_dynamics || "")}</p></div>`;
        html += `</div>`;
    }
    if (analysis.media_bias_check) {
        const mb = analysis.media_bias_check;
        html += `<div class="analysis-block"><h3>媒体偏向检测</h3>
            <div class="bias-item bias-level-med">
                <div class="bias-source">情绪引导词: ${(mb.emotional_trigger_words || []).join(", ") || "未检测到"}</div>
                <div class="bias-detail">叙事框架: ${esc(mb.framing_analysis || "")}</div>
                <div class="bias-detail">建议角度: ${esc(mb.suggested_reading_angle || "")}</div>
            </div>
        </div>`;
    }
    if (analysis.impact_assessment) {
        const ia = analysis.impact_assessment;
        html += `<div class="analysis-block"><h3>影响评估</h3>
            <div class="risk-card"><h4>直接影响</h4><p>${esc(ia.immediate_impact || "")}</p></div>
            <div class="risk-card"><h4>长期意义</h4><p>${esc(ia.long_term_significance || "")}</p></div>
            <div class="risk-card"><h4>谁获益</h4><p>${esc(ia.who_benefits || "")}</p></div>
            <div class="risk-card"><h4>谁受损</h4><p>${esc(ia.who_loses || "")}</p></div>
        </div>`;
    }
    container.innerHTML = html;
}

// ===== 全局AI对话 =====
function initGlobalChat() {
    const toggle = document.getElementById("chatToggle");
    const body = document.getElementById("chatBody");
    toggle.addEventListener("click", () => body.classList.toggle("collapsed"));

    document.getElementById("btnChatSend").addEventListener("click", () => sendGlobalChat());
    document.getElementById("chatInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendGlobalChat();
    });
}

let globalChatHistory = [];

async function sendGlobalChat() {
    const input = document.getElementById("chatInput");
    const question = input.value.trim();
    if (!question) return;

    const msgs = document.getElementById("chatMessages");
    appendChatMsg(msgs, "user", question);
    input.value = "";

    const dailyContent = document.getElementById("dailyContent");
    let context = dailyContent.textContent || "";
    context = context.substring(0, 8000);

    appendChatMsg(msgs, "assistant", '<span class="loading" style="padding:0"></span>');

    const history = globalChatHistory.slice(-10);

    try {
        const resp = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, context, history }),
        });
        const data = await resp.json();
        msgs.lastElementChild.remove();
        if (data.success) {
            appendChatMsg(msgs, "assistant", data.reply);
            globalChatHistory.push({ role: "user", content: question });
            globalChatHistory.push({ role: "assistant", content: data.reply });
        } else {
            appendChatMsg(msgs, "assistant", "抱歉，出错了: " + data.error);
        }
    } catch (err) {
        msgs.lastElementChild.remove();
        appendChatMsg(msgs, "assistant", "请求失败: " + err.message);
    }
}

// ===== 历史 =====
function initHistoryTab() {}

async function loadHistory() {
    const container = document.getElementById("historyList");
    try {
        const resp = await fetch("/api/history");
        const data = await resp.json();
        if (!data.success || !data.reports.length) {
            container.innerHTML = '<p class="placeholder">暂无历史报告</p>';
            return;
        }
        container.innerHTML = data.reports.map(r => `
            <div class="history-item" onclick="loadHistoryReport('${r.date}')">
                <div class="history-date">${r.date}</div>
                <div class="history-count">${r.news_count}条新闻</div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<p class="placeholder">加载失败: ${esc(err.message)}</p>`;
    }
}

async function loadHistoryReport(dateStr) {
    const container = document.getElementById("dailyContent");
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    document.querySelector('[data-tab="daily"]').classList.add("active");
    document.getElementById("tab-daily").classList.add("active");

    container.innerHTML = '<div class="loading">加载历史报告...</div>';

    try {
        const resp = await fetch(`/api/report/${dateStr}`);
        const data = await resp.json();
        if (data.success) {
            currentReport = data.report;
            activeCategory = "全部";
            document.getElementById("statusDaily").textContent = `历史报告: ${dateStr}`;
            document.getElementById("btnAnalyze").textContent = "返回今日分析";
            renderDailyReport(data.report);
        } else {
            container.innerHTML = `<p class="placeholder">${data.error}</p>`;
        }
    } catch (err) {
        container.innerHTML = `<p class="placeholder">加载失败: ${esc(err.message)}</p>`;
    }
}

// ===== 工具函数 =====
function renderNarrativeCard(title, items) {
    if (!items || !items.length) return "";
    return `<div class="narrative-card">
        <h4>${title}</h4>
        <ul>${items.map(i => `<li>${esc(i)}</li>`).join("")}</ul>
    </div>`;
}

function renderStructSection(title, items) {
    if (!items || !items.length) return "";
    return `<div class="struct-section"><h4>${title}</h4><ul>${items.map(i => `<li>${esc(i)}</li>`).join("")}</ul></div>`;
}

function appendChatMsg(container, role, text) {
    const div = document.createElement("div");
    div.className = `chat-msg ${role}`;
    const label = role === "user" ? "你" : "AI";
    div.innerHTML = `<span class="chat-label">${label}</span><p>${text}</p>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

function escAttr(s) {
    return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// 监听动态渲染
const observer = new MutationObserver(() => { initNewsChatListeners(); });
observer.observe(document.getElementById("dailyContent"), { childList: true, subtree: false });
observer.observe(document.getElementById("manualResult"), { childList: true, subtree: false });
