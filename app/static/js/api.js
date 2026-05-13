// ─── Base API helper ──────────────────────────────────────────────────────────

const _LAST = new Map();   // outputId -> { method, path, body, headers, status, resp, took }

async function callApi(path, options = {}) {
    const { method = "GET", body, headers = {} } = options;
    const init = {
        method,
        headers: { "Content-Type": "application/json", ...headers },
    };
    if (body !== undefined) {
        init.body = typeof body === "string" ? body : JSON.stringify(body);
    }

    const t0 = performance.now();
    let res;
    try {
        res = await fetch(path, init);
    } catch (err) {
        return { status: 0, ok: false, body: `네트워크 에러: ${err.message}`, took: performance.now() - t0, headers: {} };
    }
    const took = performance.now() - t0;
    const text = await res.text();
    let parsed;
    try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
    const respHeaders = {};
    res.headers.forEach((v, k) => { respHeaders[k] = v; });
    return { status: res.status, ok: res.ok, body: parsed, took, headers: respHeaders };
}

function _statusClass(status) {
    if (status === 0) return "net";
    if (status >= 200 && status < 300) return "ok";
    if (status >= 300 && status < 400) return "warn";
    return "err";
}

function _ensurePanel(outputEl) {
    // outputEl 은 <pre id="out-...">. 처음 호출 시 주변에 <div class="resp-panel"> 래퍼를 만든다.
    if (outputEl._panel) return outputEl._panel;

    const panel = document.createElement("div");
    panel.className = "resp-panel empty";

    const head = document.createElement("div");
    head.className = "resp-head";
    head.innerHTML = `
        <span class="resp-status" data-class="">—</span>
        <span class="resp-time"></span>
        <span class="spacer"></span>
        <button type="button" class="btn-mini" data-act="curl">curl 복사</button>
        <button type="button" class="btn-mini" data-act="json">JSON 복사</button>
        <button type="button" class="btn-mini" data-act="req">요청 보기</button>
    `;

    const tabs = document.createElement("div");
    tabs.className = "resp-tabs";
    tabs.innerHTML = `
        <button type="button" data-pane="body" class="active">Body</button>
        <button type="button" data-pane="headers">Headers</button>
        <button type="button" data-pane="request">Request</button>
    `;

    const reqPre = document.createElement("pre");
    reqPre.dataset.pane = "hidden";
    reqPre.dataset.role = "request";

    const headersPre = document.createElement("pre");
    headersPre.dataset.pane = "hidden";
    headersPre.dataset.role = "headers";

    // wrap: outputEl 자리에 panel 삽입, outputEl 을 panel 안으로 이동
    outputEl.parentNode.insertBefore(panel, outputEl);
    panel.appendChild(head);
    panel.appendChild(tabs);
    panel.appendChild(outputEl);
    panel.appendChild(headersPre);
    panel.appendChild(reqPre);

    // 탭 전환
    tabs.querySelectorAll("button").forEach(btn => {
        btn.addEventListener("click", () => {
            tabs.querySelectorAll("button").forEach(b => b.classList.toggle("active", b === btn));
            const pane = btn.dataset.pane;
            outputEl.dataset.pane    = pane === "body"    ? "show" : "hidden";
            headersPre.dataset.pane  = pane === "headers" ? "show" : "hidden";
            reqPre.dataset.pane      = pane === "request" ? "show" : "hidden";
        });
    });

    // 복사 버튼
    head.querySelector('[data-act="curl"]').addEventListener("click", () => _copyCurl(outputEl.id));
    head.querySelector('[data-act="json"]').addEventListener("click", () => _copyJson(outputEl.id));
    head.querySelector('[data-act="req"]').addEventListener("click", () => {
        // 'Request' 탭으로 전환
        tabs.querySelector('[data-pane="request"]').click();
    });

    outputEl._panel = panel;
    outputEl._head = head;
    outputEl._reqPre = reqPre;
    outputEl._headersPre = headersPre;
    return panel;
}

function render(outputEl, status, body, meta = {}) {
    const panel = _ensurePanel(outputEl);
    panel.classList.remove("empty");

    const formatted = typeof body === "string" ? body : JSON.stringify(body, null, 2);
    outputEl.textContent = formatted || "(빈 응답)";
    outputEl.dataset.status = (status >= 200 && status < 300) ? "ok" : "error";

    const head = outputEl._head;
    head.querySelector(".resp-status").textContent = status || "ERR";
    head.querySelector(".resp-status").dataset.class = _statusClass(status);
    head.querySelector(".resp-time").textContent = meta.took != null ? `${meta.took.toFixed(0)} ms` : "";

    // headers / request 탭 채우기
    outputEl._headersPre.textContent = meta.headers ? JSON.stringify(meta.headers, null, 2) : "(헤더 없음)";
    if (meta.req) {
        const lines = [`${meta.req.method} ${meta.req.path}`];
        if (meta.req.headers && Object.keys(meta.req.headers).length) {
            for (const [k, v] of Object.entries(meta.req.headers)) lines.push(`${k}: ${v}`);
        }
        if (meta.req.body !== undefined) {
            lines.push("");
            lines.push(typeof meta.req.body === "string" ? meta.req.body : JSON.stringify(meta.req.body, null, 2));
        }
        outputEl._reqPre.textContent = lines.join("\n");
    } else {
        outputEl._reqPre.textContent = "(요청 정보 없음)";
    }

    _LAST.set(outputEl.id, { ...meta.req, status, resp: body, took: meta.took, headers: meta.headers });
}

function _copyCurl(outputId) {
    const last = _LAST.get(outputId);
    if (!last) { toast("호출 기록이 없습니다."); return; }
    const parts = [`curl -X ${last.method || "GET"}`];
    parts.push(`'${location.origin}${last.path}'`);
    for (const [k, v] of Object.entries(last.headers || {})) {
        if (k.toLowerCase() === "content-type" && last.body === undefined) continue;
        parts.push(`-H '${k}: ${v}'`);
    }
    if (last.body !== undefined) {
        const b = typeof last.body === "string" ? last.body : JSON.stringify(last.body);
        parts.push(`-d '${b.replace(/'/g, "'\\''")}'`);
    }
    navigator.clipboard.writeText(parts.join(" \\\n  ")).then(() => toast("curl 명령 복사됨"));
}

function _copyJson(outputId) {
    const last = _LAST.get(outputId);
    if (!last) { toast("호출 기록이 없습니다."); return; }
    const text = typeof last.resp === "string" ? last.resp : JSON.stringify(last.resp, null, 2);
    navigator.clipboard.writeText(text).then(() => toast("응답 JSON 복사됨"));
}

// ─── bindCall / bindForm ──────────────────────────────────────────────────────
function bindCall(buttonId, outputId, path, options = {}) {
    const btn = document.getElementById(buttonId);
    const out = document.getElementById(outputId);
    if (!btn || !out) return;

    btn.addEventListener("click", async () => {
        out.textContent = "호출 중...";
        delete out.dataset.status;
        const headers = options.auth ? authHeaders() : (options.headers || {});
        const method  = options.method || "GET";
        const { status, body, took, headers: respHeaders } = await callApi(path, { ...options, method, headers });
        render(out, status, body, { took, headers: respHeaders, req: { method, path, headers, body: options.body } });
        if (body && status >= 200 && status < 300 && options.onSuccess) options.onSuccess(body);
    });
}

function readForm(formId) {
    const out = {};
    document.getElementById(formId)
        ?.querySelectorAll("[name]")
        .forEach(el => { if (el.value !== "") out[el.name] = el.value; });
    return out;
}

function bindForm(formId, outputId, path, options = {}) {
    const form = document.getElementById(formId);
    const out  = document.getElementById(outputId);
    if (!form || !out) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        out.textContent = "호출 중...";
        delete out.dataset.status;
        let body = readForm(formId);
        if (typeof options.transform === "function") body = options.transform(body);
        const headers = options.auth ? authHeaders() : (options.headers || {});
        const method  = options.method ?? "POST";
        const { status, body: resp, took, headers: respHeaders } = await callApi(path, { method, body, headers });
        render(out, status, resp, { took, headers: respHeaders, req: { method, path, headers, body } });
        if (resp && status >= 200 && status < 300 && options.onSuccess) options.onSuccess(resp);
    });
}

// ─── Session / Token management ───────────────────────────────────────────────
const _K_ACCESS  = "sg_access_token";
const _K_REFRESH = "sg_refresh_token";
const _K_THEME   = "sg_theme";

function getToken(type = "access") {
    return localStorage.getItem(type === "refresh" ? _K_REFRESH : _K_ACCESS) || "";
}
function authHeaders() {
    const tok = getToken("access");
    return tok ? { Authorization: `Bearer ${tok}` } : {};
}
function setSession(access, refresh) {
    localStorage.setItem(_K_ACCESS, access);
    if (refresh !== undefined) localStorage.setItem(_K_REFRESH, refresh);
    _renderSession();
}
function clearSession() {
    localStorage.removeItem(_K_ACCESS);
    localStorage.removeItem(_K_REFRESH);
    _renderSession();
}
function copyToken(type) {
    const text = getToken(type);
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector(`[data-copy="${type}"]`);
        if (!btn) return;
        const orig = btn.textContent;
        btn.textContent = "✓ 복사됨";
        setTimeout(() => { btn.textContent = orig; }, 1500);
    });
}
function _renderSession() {
    const access  = getToken("access");
    const refresh = getToken("refresh");
    const card      = document.querySelector(".session-card");
    const badge     = document.getElementById("session-badge");
    const accessEl  = document.getElementById("token-access");
    const refreshEl = document.getElementById("token-refresh");
    const logoutBtn = document.getElementById("btn-session-logout");
    if (card) card.style.display = access ? "" : "none";
    if (badge) { badge.textContent = access ? "✓  로그인됨" : "로그아웃 상태"; badge.dataset.state = access ? "in" : "out"; }
    if (accessEl)  accessEl.textContent  = access  || "—";
    if (refreshEl) refreshEl.textContent = refresh || "—";
    if (logoutBtn) logoutBtn.style.display = access ? "inline-block" : "none";
}

// ─── 폼 입력 영속화 ───────────────────────────────────────────────────────────
function _formKey(form) { return `sg_form:${form.id || form.dataset.persist}`; }
function _saveForm(form) {
    const data = {};
    form.querySelectorAll("[name],[id]").forEach(el => {
        const key = el.name || el.id;
        if (!key) return;
        if (el.type === "checkbox") data[key] = el.checked;
        else if (el.type === "password") return;   // 비밀번호는 저장 안 함
        else data[key] = el.value;
    });
    localStorage.setItem(_formKey(form), JSON.stringify(data));
}
function _restoreForm(form) {
    try {
        const raw = localStorage.getItem(_formKey(form));
        if (!raw) return;
        const data = JSON.parse(raw);
        form.querySelectorAll("[name],[id]").forEach(el => {
            const key = el.name || el.id;
            if (key in data) {
                if (el.type === "checkbox") el.checked = !!data[key];
                else if (el.type !== "password") el.value = data[key] ?? "";
            }
        });
    } catch { /* ignore */ }
}
function _initFormPersistence() {
    document.querySelectorAll("form[id], [data-persist]").forEach(scope => {
        _restoreForm(scope);
        scope.addEventListener("input",  () => _saveForm(scope));
        scope.addEventListener("change", () => _saveForm(scope));
    });
}
function clearAllForms() {
    if (!confirm("저장된 모든 입력값을 지웁니다. 계속할까요?")) return;
    Object.keys(localStorage)
        .filter(k => k.startsWith("sg_form:"))
        .forEach(k => localStorage.removeItem(k));
    document.querySelectorAll("form").forEach(f => f.reset());
    document.querySelectorAll("input.auto-filled").forEach(el => el.classList.remove("auto-filled"));
    toast("입력 기록이 초기화되었습니다.");
}

// ─── 자동 채움 시각 표시 ──────────────────────────────────────────────────────
function setAutoFill(selectorOrEl, value) {
    const els = typeof selectorOrEl === "string"
        ? document.querySelectorAll(selectorOrEl)
        : [selectorOrEl];
    els.forEach(el => {
        if (!el) return;
        el.value = value;
        el.classList.add("auto-filled");
        // 사용자가 직접 수정하면 강조 제거
        const off = () => { el.classList.remove("auto-filled"); el.removeEventListener("input", off); };
        el.addEventListener("input", off);
    });
}

// ─── 다크 모드 ────────────────────────────────────────────────────────────────
function toggleTheme() {
    const cur  = document.documentElement.dataset.theme || "light";
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem(_K_THEME, next);
    const btn = document.getElementById("btn-theme");
    if (btn) btn.textContent = next === "dark" ? "☀️" : "🌙";
}
function _initTheme() {
    const saved = localStorage.getItem(_K_THEME)
        || (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.dataset.theme = saved;
    const btn = document.getElementById("btn-theme");
    if (btn) btn.textContent = saved === "dark" ? "☀️" : "🌙";
}

// ─── 검색 (전체 카드 필터) ────────────────────────────────────────────────────
function _initSearch() {
    const input = document.getElementById("input-search");
    if (!input) return;
    input.addEventListener("input", () => {
        const q = input.value.trim().toLowerCase();
        document.querySelectorAll(".card").forEach(card => {
            if (!q) { card.classList.remove("hidden-by-search", "search-hit"); return; }
            const text = card.textContent.toLowerCase();
            const hit  = text.includes(q);
            card.classList.toggle("hidden-by-search", !hit);
            card.classList.toggle("search-hit", hit);
        });
        // 검색 시 모든 탭에 결과 보이도록 전체 탭 표시
        if (q) {
            document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("active"));
        } else {
            // 검색 비우면 해시 탭으로 복귀
            const id = location.hash.slice(1) || "tab-basic";
            document.querySelectorAll(".tab-panel").forEach(p => p.classList.toggle("active", p.id === id));
        }
    });
    input.addEventListener("keydown", e => { if (e.key === "Escape") { input.value = ""; input.dispatchEvent(new Event("input")); } });
    // 키보드 단축키: / 키
    document.addEventListener("keydown", e => {
        if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
            e.preventDefault();
            input.focus();
        }
    });
}

// ─── 카드 접기/펼치기 ────────────────────────────────────────────────────────
function _initCollapsibles() {
    document.querySelectorAll(".card > h3").forEach(h => {
        // caret 추가
        if (!h.querySelector(".caret")) {
            const c = document.createElement("span");
            c.className = "caret";
            c.textContent = "▼";
            h.appendChild(c);
        }
        h.addEventListener("click", e => {
            // 헤더 안의 링크나 코드 클릭은 통과
            if (e.target.tagName === "A" || e.target.tagName === "CODE") return;
            h.parentElement.classList.toggle("collapsed");
        });
    });
}

// ─── 메서드 배지 자동 부착 ────────────────────────────────────────────────────
function _initMethodBadges() {
    document.querySelectorAll(".card > h3 code").forEach(code => {
        const txt = code.textContent.trim();
        const m = txt.match(/^(GET|POST|PUT|PATCH|DELETE|WS)\s+/i);
        if (!m) return;
        const method = m[1].toUpperCase();
        const badge = document.createElement("span");
        badge.className = "method-badge";
        badge.dataset.method = method;
        badge.textContent = method;
        // h3 의 첫 자식 텍스트 노드 뒤에 삽입 (즉, 제목 텍스트 다음, code 앞)
        code.parentNode.insertBefore(badge, code);
    });
}

// ─── 탭 카운트 ────────────────────────────────────────────────────────────────
function _initTabCounts() {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        const id = btn.dataset.tab;
        const panel = document.getElementById(id);
        if (!panel) return;
        const n = panel.querySelectorAll(".card").length;
        if (!n) return;
        const cnt = document.createElement("span");
        cnt.className = "tab-count";
        cnt.textContent = n;
        btn.appendChild(cnt);
    });
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function toast(message, ms = 2200) {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
        stack = document.createElement("div");
        stack.className = "toast-stack";
        document.body.appendChild(stack);
    }
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = message;
    stack.appendChild(t);
    requestAnimationFrame(() => t.classList.add("show"));
    setTimeout(() => { t.classList.remove("show"); setTimeout(() => t.remove(), 250); }, ms);
}

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    _initTheme();
    _initMethodBadges();
    _initCollapsibles();
    _initTabCounts();
    _initSearch();
    _initFormPersistence();
    _renderSession();

    // 모든 out- 요소를 응답 패널 래퍼로 한 번씩 감싸 둔다 (호출 전에도 탭 UI 동작)
    document.querySelectorAll('pre[id^="out-"]').forEach(_ensurePanel);

    // 테마 토글 / 모두 지우기 버튼 핸들러
    document.getElementById("btn-theme")?.addEventListener("click", toggleTheme);
    document.getElementById("btn-clear-forms")?.addEventListener("click", clearAllForms);
});
