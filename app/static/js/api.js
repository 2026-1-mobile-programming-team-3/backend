// ─── Base API helper ──────────────────────────────────────────────────────────

async function callApi(path, options = {}) {
    const { method = "GET", body, headers = {} } = options;
    const init = {
        method,
        headers: { "Content-Type": "application/json", ...headers },
    };
    if (body !== undefined) {
        init.body = typeof body === "string" ? body : JSON.stringify(body);
    }

    const res = await fetch(path, init);
    const text = await res.text();
    let parsed;
    try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
    return { status: res.status, ok: res.ok, body: parsed };
}

function render(outputEl, status, body) {
    const formatted = typeof body === "string" ? body : JSON.stringify(body, null, 2);
    outputEl.textContent = status ? `[${status}]\n${formatted}` : formatted;
    outputEl.dataset.status = status >= 200 && status < 300 ? "ok" : "error";
}

// authHeaders() is called at click time inside the listener, so auth: true always
// picks up the current stored token even if the user logged in after page load.
function bindCall(buttonId, outputId, path, options = {}) {
    const btn = document.getElementById(buttonId);
    const out = document.getElementById(outputId);
    if (!btn || !out) return;

    btn.addEventListener("click", async () => {
        out.textContent = "호출 중...";
        delete out.dataset.status;
        try {
            const headers = options.auth ? authHeaders() : (options.headers || {});
            const { status, body } = await callApi(path, { ...options, headers });
            render(out, status, body);
            if (body && status >= 200 && status < 300 && options.onSuccess) {
                options.onSuccess(body);
            }
        } catch (err) {
            out.textContent = `네트워크 에러: ${err.message}`;
            out.dataset.status = "error";
        }
    });
}

// Reads name-attributed inputs from a form; skips empty strings.
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
        try {
            const body    = readForm(formId);
            const headers = options.auth ? authHeaders() : (options.headers || {});
            const { status, body: resp } = await callApi(path, {
                method: options.method ?? "POST",
                body,
                headers,
            });
            render(out, status, resp);
            if (resp && status >= 200 && status < 300 && options.onSuccess) {
                options.onSuccess(resp);
            }
        } catch (err) {
            out.textContent = `네트워크 에러: ${err.message}`;
            out.dataset.status = "error";
        }
    });
}


// ─── Session / Token management ───────────────────────────────────────────────

const _K_ACCESS  = "sg_access_token";
const _K_REFRESH = "sg_refresh_token";

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

    const badge      = document.getElementById("session-badge");
    const accessEl   = document.getElementById("token-access");
    const refreshEl  = document.getElementById("token-refresh");
    const logoutBtn  = document.getElementById("btn-session-logout");

    if (badge) {
        badge.textContent  = access ? "✓  로그인됨" : "로그아웃 상태";
        badge.dataset.state = access ? "in" : "out";
    }
    if (accessEl)  accessEl.textContent  = access  || "—";
    if (refreshEl) refreshEl.textContent = refresh || "—";
    if (logoutBtn) logoutBtn.style.display = access ? "inline-block" : "none";
}

document.addEventListener("DOMContentLoaded", _renderSession);
