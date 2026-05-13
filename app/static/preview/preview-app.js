/* preview-app.js — Branch 2 (모바일 앱 미리보기) 공용 런타임
   v2 design assets 와 함께 동작. 외부 의존 없음 (Vanilla ES2020).
*/
(function () {
  "use strict";

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ─── Auth ──────────────────────────────────────────────────────────────────
  const K_ACCESS = "sg_access_token";
  const K_REFRESH = "sg_refresh_token";
  const K_DEBUG = "sg_preview_debug";

  const Auth = {
    getAccess: () => localStorage.getItem(K_ACCESS) || "",
    getRefresh: () => localStorage.getItem(K_REFRESH) || "",
    headers() {
      const tok = this.getAccess();
      return tok ? { Authorization: `Bearer ${tok}` } : {};
    },
    set(access, refresh) {
      if (access !== undefined) localStorage.setItem(K_ACCESS, access);
      if (refresh !== undefined) localStorage.setItem(K_REFRESH, refresh);
    },
    clear() {
      localStorage.removeItem(K_ACCESS);
      localStorage.removeItem(K_REFRESH);
    },
    requireLogin() {
      if (this.getAccess()) return true;
      Toast.error("로그인이 필요해요. 2초 뒤 콘솔로 이동합니다.");
      setTimeout(() => { window.location.href = "/"; }, 2000);
      return false;
    },
  };

  // ─── API (fetch wrapper) ───────────────────────────────────────────────────
  const API = {
    async call(method, path, body, _retried = false) {
      const init = {
        method,
        headers: { "Content-Type": "application/json", ...Auth.headers() },
      };
      if (body !== undefined) init.body = JSON.stringify(body);

      const t0 = performance.now();
      let res, parsed, text;
      try {
        res = await fetch(path, init);
        text = await res.text();
        try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
      } catch (err) {
        DebugPanel.log({ method, path, status: 0, ms: 0, err: err.message });
        throw err;
      }
      const ms = performance.now() - t0;

      // 401 + refresh token → 1회 자동 갱신 후 재시도
      if (res.status === 401 && !_retried && Auth.getRefresh() && path !== "/api/v1/auth/refresh") {
        const refreshed = await this.tryRefresh();
        if (refreshed) {
          DebugPanel.log({ method, path, status: 401, ms, note: "→ refresh & retry" });
          return this.call(method, path, body, true);
        }
      }

      DebugPanel.log({ method, path, status: res.status, ms, body: parsed });
      if (!res.ok) {
        const detail = parsed?.detail || res.statusText;
        const err = new Error(`${res.status}: ${detail}`);
        err.status = res.status; err.body = parsed;
        throw err;
      }
      return parsed;
    },

    async tryRefresh() {
      const refresh = Auth.getRefresh();
      if (!refresh) return false;
      try {
        const res = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) { Auth.clear(); return false; }
        const data = await res.json();
        Auth.set(data.access_token, data.refresh_token);
        return true;
      } catch { Auth.clear(); return false; }
    },

    get(path) { return this.call("GET", path); },
    post(path, body) { return this.call("POST", path, body); },
    patch(path, body) { return this.call("PATCH", path, body); },
    put(path, body) { return this.call("PUT", path, body); },
    delete(path) { return this.call("DELETE", path); },
  };

  // ─── Bind (data-bind 처리기) ───────────────────────────────────────────────
  function getPath(obj, path) {
    return path.split(".").reduce(
      (acc, key) => (acc == null ? acc : acc[key]),
      obj,
    );
  }

  function fillTemplate(str, ctx) {
    return str.replace(/\{([\w.]+)\}/g, (_m, k) => {
      const v = getPath(ctx, k);
      return v == null ? "" : String(v);
    });
  }

  const Bind = {
    apply(root, data) {
      if (!root || !data) return;
      // data-bind="path.to.value" — textContent
      root.querySelectorAll("[data-bind]").forEach((el) => {
        if (el.tagName === "TEMPLATE") return;
        const path = el.getAttribute("data-bind");
        const val = getPath(data, path);
        if (val == null) return;
        const attrSpec = el.getAttribute("data-bind-attr");
        if (attrSpec) {
          // "src" 또는 "href:/path/{id}/foo"
          const colon = attrSpec.indexOf(":");
          const attr = colon < 0 ? attrSpec : attrSpec.slice(0, colon);
          const tmpl = colon < 0 ? null : attrSpec.slice(colon + 1);
          el.setAttribute(attr, tmpl ? fillTemplate(tmpl, data) : val);
        } else {
          el.textContent = val;
        }
      });
      // data-bind-show="path" — 값이 truthy면 표시, 아니면 hidden
      root.querySelectorAll("[data-bind-show]").forEach((el) => {
        const path = el.getAttribute("data-bind-show");
        el.hidden = !getPath(data, path);
      });
      // data-bind-each="arrayPath" data-template="#tmpl-id"
      root.querySelectorAll("[data-bind-each]").forEach((host) => {
        const arrPath = host.getAttribute("data-bind-each");
        const tmplSel = host.getAttribute("data-template");
        const arr = getPath(data, arrPath);
        if (!Array.isArray(arr) || !tmplSel) return;
        const tmpl = document.querySelector(tmplSel);
        if (!tmpl) return;
        host.innerHTML = "";
        for (const item of arr) {
          const node = tmpl.content.cloneNode(true);
          // 자식 요소에 대해 fragment-scoped bind 적용
          Bind.apply(node, item);
          // host와 item 컨텍스트 둘 다 채울 수 있도록 attr 템플릿도 처리
          node.querySelectorAll("[data-bind-attr]").forEach((el) => {
            const spec = el.getAttribute("data-bind-attr");
            const colon = spec.indexOf(":");
            if (colon < 0) return;
            const attr = spec.slice(0, colon);
            const tpl = spec.slice(colon + 1);
            el.setAttribute(attr, fillTemplate(tpl, item));
          });
          host.appendChild(node);
        }
      });
    },
  };

  // ─── DebugPanel ────────────────────────────────────────────────────────────
  const DebugPanel = {
    el: null, listEl: null, _mounted: false,
    mount() {
      if (this._mounted) return;
      this._mounted = true;
      this.el = document.createElement("aside");
      this.el.id = "preview-debug-panel";
      this.el.innerHTML = `
        <header>
          <strong>API 디버그</strong>
          <button type="button" id="dbg-clear" title="기록 지우기">↻</button>
          <button type="button" id="dbg-toggle" title="패널 토글">×</button>
        </header>
        <div class="dbg-token"></div>
        <div class="dbg-list"></div>
      `;
      document.body.appendChild(this.el);
      this.listEl = this.el.querySelector(".dbg-list");
      this._renderToken();
      this.el.querySelector("#dbg-clear").addEventListener("click", () => { this.listEl.innerHTML = ""; });
      this.el.querySelector("#dbg-toggle").addEventListener("click", () => this.hide());
      // 토글 버튼 (패널 외부) — 닫혀 있을 때 다시 열기
      this._installFloating();
      // 초기 상태 복원
      if (localStorage.getItem(K_DEBUG) === "off") this.hide(true);
    },
    _installFloating() {
      const btn = document.createElement("button");
      btn.id = "preview-debug-fab";
      btn.type = "button";
      btn.title = "API 디버그 열기";
      btn.textContent = "dbg";
      btn.addEventListener("click", () => this.show());
      document.body.appendChild(btn);
    },
    show() {
      this.el.classList.remove("hidden");
      document.getElementById("preview-debug-fab")?.classList.add("hidden");
      localStorage.setItem(K_DEBUG, "on");
    },
    hide(initial) {
      this.el.classList.add("hidden");
      document.getElementById("preview-debug-fab")?.classList.remove("hidden");
      if (!initial) localStorage.setItem(K_DEBUG, "off");
    },
    toggle() { this.el.classList.contains("hidden") ? this.show() : this.hide(); },
    _renderToken() {
      const tok = Auth.getAccess();
      const display = tok ? `••• ${tok.slice(-8)}` : "(none)";
      this.el.querySelector(".dbg-token").textContent = `token: ${display}`;
    },
    log(evt) {
      if (!this._mounted) return;
      const row = document.createElement("div");
      row.className = "dbg-row";
      const cls =
        evt.status === 0 ? "net" :
        evt.status >= 200 && evt.status < 300 ? "ok" :
        evt.status >= 400 ? "err" : "warn";
      const time = new Date().toTimeString().slice(0, 8);
      const ms = evt.ms != null ? `${evt.ms.toFixed(0)}ms` : "";
      row.innerHTML = `
        <div class="dbg-row-head" data-cls="${cls}">
          <span class="status">${escapeHtml(evt.status || "ERR")}</span>
          <span class="method">${escapeHtml(evt.method || "WS")}</span>
          <span class="path">${escapeHtml(evt.path)}</span>
          <span class="time">${escapeHtml(ms)}</span>
        </div>
      `;
      if (evt.body !== undefined || evt.err) {
        const det = document.createElement("details");
        det.innerHTML = `<summary>본문</summary><pre>${
          escapeHtml(evt.err ?? JSON.stringify(evt.body, null, 2))
        }</pre>`;
        row.appendChild(det);
      }
      if (evt.note) {
        const note = document.createElement("div");
        note.className = "dbg-note"; note.textContent = evt.note;
        row.appendChild(note);
      }
      this.listEl.prepend(row);
      this._renderToken();
    },
  };

  // ─── WebSocket ─────────────────────────────────────────────────────────────
  const WS = {
    ws: null, listeners: [],
    connect(applicationId) {
      const tok = Auth.getAccess();
      if (!tok) { Toast.error("WS: 토큰 없음"); return; }
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const url = `${proto}://${location.host}/api/v1/ws/applications/${applicationId}?token=${encodeURIComponent(tok)}`;
      this.ws = new WebSocket(url);
      this.ws.addEventListener("open", () => {
        DebugPanel.log({ method: "WS", path: `/ws/applications/${applicationId}`, status: 101, note: "OPEN" });
      });
      this.ws.addEventListener("message", (e) => {
        let payload; try { payload = JSON.parse(e.data); } catch { payload = e.data; }
        DebugPanel.log({ method: "WS", path: "message", status: 200, body: payload });
        this.listeners.forEach((fn) => { try { fn(payload); } catch (err) { console.error(err); } });
      });
      this.ws.addEventListener("close", (e) => {
        DebugPanel.log({ method: "WS", path: "close", status: e.code, note: `close ${e.code}` });
        this.ws = null;
      });
      this.ws.addEventListener("error", () => {
        DebugPanel.log({ method: "WS", path: "error", status: 0, err: "WebSocket error" });
      });
    },
    onMessage(fn) { this.listeners.push(fn); },
    close() { this.ws?.close(); this.ws = null; this.listeners = []; },
  };

  // ─── Toast ─────────────────────────────────────────────────────────────────
  const Toast = {
    _stack: null,
    _ensure() {
      if (this._stack) return;
      this._stack = document.createElement("div");
      this._stack.id = "preview-toast-stack";
      document.body.appendChild(this._stack);
    },
    _show(text, kind, ms = 2400) {
      this._ensure();
      const t = document.createElement("div");
      t.className = `preview-toast ${kind}`;
      t.textContent = text;
      this._stack.appendChild(t);
      requestAnimationFrame(() => t.classList.add("show"));
      setTimeout(() => { t.classList.remove("show"); setTimeout(() => t.remove(), 220); }, ms);
    },
    ok(text) { this._show(text, "ok"); },
    error(text) { this._show(text, "err"); },
    info(text) { this._show(text, "info"); },
  };

  // ─── PreviewApp (페이지 부트스트랩 placeholder — 페이지별 task에서 추가) ─────
  const PreviewApp = {
    Auth, API, Bind, DebugPanel, WS, Toast,
    bootHome: null,   // Task 4
    bootMy: null,     // Task 5
    bootMatch: null,  // Task 6
    bootMap: null,    // Task 7
    bootChat: null,   // Task 8
  };

  // ─── Page boot: 홈 ─────────────────────────────────────────────────────────
  PreviewApp.bootHome = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    try {
      const data = await API.get("/api/v1/home/dashboard");
      Bind.apply(document, data);
    } catch (err) {
      Toast.error(`홈 로딩 실패: ${err.message}`);
    }
  };

  // ─── Page boot: 내정보 ────────────────────────────────────────────────────
  PreviewApp.bootMy = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    try {
      const [me, stats, author_matches, applicant_matches] = await Promise.all([
        API.get("/api/v1/users/me"),
        API.get("/api/v1/users/me/activity-stats"),
        API.get("/api/v1/users/me/matches?role=author&size=3"),
        API.get("/api/v1/users/me/matches?role=applicant&size=3"),
      ]);
      const combined = { ...me, ...stats, author_matches, applicant_matches };
      Bind.apply(document, combined);
    } catch (err) {
      Toast.error(`내 정보 로딩 실패: ${err.message}`);
    }
  };

  // ─── Page boot: 매칭 리스트 ────────────────────────────────────────────────
  PreviewApp.bootMatch = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    const tabs = document.querySelectorAll(".match-tabs [data-status]");
    let current = "";
    async function load(status) {
      try {
        const qs = status ? `?status=${status}` : "";
        const data = await API.get(`/api/v1/matches${qs}`);
        Bind.apply(document, data);
      } catch (err) {
        Toast.error(`매칭 목록 실패: ${err.message}`);
      }
    }
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        tabs.forEach((t) => t.classList.toggle("active", t === tab));
        current = tab.getAttribute("data-status") || "";
        load(current);
      });
    });
    await load(current);
  };

  // ─── Page boot: 지도 (카드 리스트 fallback) ─────────────────────────────────
  PreviewApp.bootMap = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    // 시흥시 정왕동 기준 좌표 default
    const lat = 37.3451, lng = 126.7322, radius = 5000;
    async function loadNearby() {
      try {
        const data = await API.get(`/api/v1/maps/stores?lat=${lat}&lng=${lng}&radius=${radius}`);
        Bind.apply(document, data);
      } catch (err) {
        Toast.error(`매장 로딩 실패: ${err.message}`);
      }
    }
    async function loadSearch(keyword) {
      try {
        const data = await API.get(`/api/v1/maps/stores/search?keyword=${encodeURIComponent(keyword)}`);
        // search 응답은 { results: [...] } → stores 키로 매핑
        Bind.apply(document, { stores: (data.results || []).map((r) => ({ ...r, distance_m: "—" })) });
      } catch (err) {
        Toast.error(`검색 실패: ${err.message}`);
      }
    }
    const input = document.getElementById("map-search-input");
    if (input) {
      let timer = null;
      input.addEventListener("input", () => {
        clearTimeout(timer);
        const v = input.value.trim();
        timer = setTimeout(() => v ? loadSearch(v) : loadNearby(), 300);
      });
    }
    await loadNearby();
  };

  // ─── Page boot: 채팅 ──────────────────────────────────────────────────────
  PreviewApp.bootChat = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    const params = new URLSearchParams(location.search);
    let appId = parseInt(params.get("application_id"), 10);
    let matchId = parseInt(params.get("match_id"), 10);
    let me = null;
    try {
      me = await API.get("/api/v1/users/me");
    } catch (err) { Toast.error(`내 정보 실패: ${err.message}`); return; }

    if (!appId || !matchId) {
      // fallback: 최근 본인 application
      try {
        const mine = await API.get("/api/v1/users/me/matches?role=applicant&size=1");
        const first = mine.items?.[0];
        if (first && first.my_application_status !== "REJECTED") {
          matchId = first.match_id;
          const list = await API.get(`/api/v1/matches/${matchId}/applications`);
          const own = list.items?.find((a) => a.applicant?.applicant_id === me.id);
          appId = own?.application_id;
        }
      } catch { /* fallback 실패는 무시 */ }
    }
    if (!appId || !matchId) {
      Toast.error("채팅방을 결정할 수 없습니다. ?match_id=&application_id= 쿼리를 붙여 주세요.");
      return;
    }

    const listEl = document.getElementById("chat-messages");
    function escapeHtmlLocal(s) {
      return String(s).replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));
    }
    function renderMsg(msg) {
      const row = document.createElement("div");
      row.className = "ch-msg " + (msg.sender_id === me.id ? "mine" : "other");
      row.innerHTML = `<div class="ch-bubble">${escapeHtmlLocal(msg.content)}</div>`;
      listEl.appendChild(row);
      listEl.scrollTop = listEl.scrollHeight;
    }

    try {
      const initial = await API.get(`/api/v1/matches/${matchId}/applications/${appId}/messages?size=30`);
      // created_at DESC → 화면은 오래된→최신 → reverse
      [...(initial.items || [])].reverse().forEach(renderMsg);
    } catch (err) {
      Toast.error(`메시지 로딩 실패: ${err.message}`);
    }

    const seen = new Set();
    WS.onMessage((evt) => {
      if (evt?.type === "message.created" && !seen.has(evt.id)) {
        seen.add(evt.id);
        renderMsg(evt);
      }
    });
    WS.connect(appId);

    document.getElementById("chat-input-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = document.getElementById("chat-input");
      const content = input.value.trim();
      if (!content) return;
      input.value = "";
      try {
        const sent = await API.post(
          `/api/v1/matches/${matchId}/applications/${appId}/messages`,
          { content },
        );
        if (!seen.has(sent.id)) {
          seen.add(sent.id);
          renderMsg(sent);
        }
      } catch (err) {
        Toast.error(`전송 실패: ${err.message}`);
      }
    });
  };

  // 전역 노출
  window.PreviewApp = PreviewApp;
  window.Auth = Auth;
  window.api = API;
  window.Bind = Bind;
  window.DebugPanel = DebugPanel;
  window.Toast = Toast;
  window.WS = WS;
})();
