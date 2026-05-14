/* preview-app.js — 시흥가개 모바일 앱 미리보기 공용 런타임
   v3 design assets 와 함께 동작. 외부 의존 없음 (Vanilla ES2020).
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
    getAccess: () => sessionStorage.getItem(K_ACCESS) || "",
    getRefresh: () => sessionStorage.getItem(K_REFRESH) || "",
    headers() {
      const tok = this.getAccess();
      return tok ? { Authorization: `Bearer ${tok}` } : {};
    },
    set(access, refresh) {
      if (access !== undefined) sessionStorage.setItem(K_ACCESS, access);
      if (refresh !== undefined) sessionStorage.setItem(K_REFRESH, refresh);
    },
    clear() {
      sessionStorage.removeItem(K_ACCESS);
      sessionStorage.removeItem(K_REFRESH);
      localStorage.removeItem(K_ACCESS);
      localStorage.removeItem(K_REFRESH);
    },
    async login(email, password) {
      const data = await API.post('/api/v1/auth/login', { email, password });
      this.set(data.access_token, data.refresh_token);
      return data;
    },
    async signup(payload) {
      // payload: { email, password, nickname, phone?, region_si?, region_dong? }
      const data = await API.post('/api/v1/auth/signup', payload);
      // 회원가입은 토큰을 발급하지 않는 스펙(201 user object). 자동 로그인이 필요.
      if (data?.access_token) {
        this.set(data.access_token, data.refresh_token);
      } else if (payload.email && payload.password) {
        try { await this.login(payload.email, payload.password); } catch (e) {}
      }
      return data;
    },
    async logout() {
      const refresh = this.getRefresh();
      if (refresh) {
        try {
          await API.post('/api/v1/auth/logout', { refresh_token: refresh });
        } catch (e) {}
      }
      this.clear();
      window.location.href = 'login.html';
    },
    requireLogin() {
      if (this.getAccess()) return true;
      Toast.error("로그인이 필요해요. 로그인 화면으로 이동합니다.");
      setTimeout(() => { window.location.href = "login.html"; }, 1500);
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
        const err = new Error(`${res.status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`);
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
      root.querySelectorAll("[data-bind]").forEach((el) => {
        if (el.tagName === "TEMPLATE") return;
        const path = el.getAttribute("data-bind");
        const val = getPath(data, path);
        if (val == null) return;
        const attrSpec = el.getAttribute("data-bind-attr");
        if (attrSpec) {
          const colon = attrSpec.indexOf(":");
          const attr = colon < 0 ? attrSpec : attrSpec.slice(0, colon);
          const tmpl = colon < 0 ? null : attrSpec.slice(colon + 1);
          el.setAttribute(attr, tmpl ? fillTemplate(tmpl, data) : val);
        } else {
          el.textContent = val;
        }
      });
      root.querySelectorAll("[data-bind-show]").forEach((el) => {
        const path = el.getAttribute("data-bind-show");
        el.hidden = !getPath(data, path);
      });
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
          Bind.apply(node, item);
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
          <button type="button" id="dbg-relogin" title="다른 계정으로 로그인 (이 탭)">⇄</button>
          <button type="button" id="dbg-clear" title="기록 지우기">↻</button>
          <button type="button" id="dbg-toggle" title="패널 토글">×</button>
        </header>
        <div class="dbg-token"></div>
        <div class="dbg-list"></div>
      `;
      document.body.appendChild(this.el);
      this.listEl = this.el.querySelector(".dbg-list");
      this._renderToken();
      this.el.querySelector("#dbg-relogin").addEventListener("click", () => {
        Auth.clear();
        window.location.href = "login.html";
      });
      this.el.querySelector("#dbg-clear").addEventListener("click", () => { this.listEl.innerHTML = ""; });
      this.el.querySelector("#dbg-toggle").addEventListener("click", () => this.hide());
      this._installFloating();
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

  // ─── Loading ───────────────────────────────────────────────────────────────
  // 스피너/스켈레톤 헬퍼. API 응답 대기 동안 명시적인 로딩 UI를 노출한다.
  const Loading = {
    spinnerHTML(label) {
      const safe = label ? escapeHtml(label) : '';
      return `<div class="sg-loading"><span class="sg-spinner" aria-hidden="true"></span>${safe ? `<span>${safe}</span>` : ''}</div>`;
    },
    /** 카드 목록 자리에 들어가는 스켈레톤 (제목/메타/배지 한 줄씩) */
    skeletonCards(count = 3) {
      const card = `
        <div class="sk-card" aria-hidden="true">
          <div class="sk-card-row">
            <div class="sk-box sk-circle sm"></div>
            <div class="sk-card-body">
              <div class="sk-box sk-line lg sk-w-70"></div>
              <div class="sk-box sk-line sm sk-w-40"></div>
            </div>
          </div>
          <div class="sk-box sk-line sm sk-w-90"></div>
          <div class="sk-box sk-line sm sk-w-50"></div>
        </div>`;
      return Array.from({ length: count }, () => card).join('');
    },
    /** 한 줄짜리 리스트(알림/채팅 스레드 등) 스켈레톤 */
    skeletonRows(count = 4) {
      const row = `
        <div class="sk-card" style="padding:12px 16px;" aria-hidden="true">
          <div class="sk-card-row">
            <div class="sk-box sk-circle md"></div>
            <div class="sk-card-body">
              <div class="sk-box sk-line lg sk-w-60"></div>
              <div class="sk-box sk-line sm sk-w-90"></div>
            </div>
          </div>
        </div>`;
      return Array.from({ length: count }, () => row).join('');
    },
    /** 상세 페이지 본문 자리 스켈레톤 */
    skeletonDetail() {
      return `
        <div class="sk-card" style="margin:0 24px 14px;" aria-hidden="true">
          <div class="sk-box sk-line xl sk-w-80"></div>
          <div class="sk-box sk-line sm sk-w-50"></div>
          <div class="sk-box sk-line sm sk-w-100"></div>
          <div class="sk-box sk-line sm sk-w-90"></div>
          <div class="sk-box sk-line sm sk-w-70"></div>
        </div>`;
    },
    /** 대상 컨테이너에 로딩 내용을 채워 넣는다. 컨테이너 자체는 보이게 둠. */
    fill(target, html) {
      const el = (typeof target === 'string') ? document.querySelector(target) : target;
      if (!el) return null;
      el.dataset.sgLoading = '1';
      el.innerHTML = html;
      return el;
    },
    /** 로딩으로 채워둔 컨테이너를 비운다. (실제 데이터 렌더 직전에 호출) */
    clear(target) {
      const el = (typeof target === 'string') ? document.querySelector(target) : target;
      if (!el) return;
      if (el.dataset.sgLoading === '1') {
        delete el.dataset.sgLoading;
        el.innerHTML = '';
      }
    },
    /** 전체 페이지 오버레이 (form 제출 등 차단형 작업에 사용). 핸들을 반환. */
    overlay(label = '처리 중...') {
      const node = document.createElement('div');
      node.className = 'sg-loading-overlay';
      node.setAttribute('role', 'status');
      node.setAttribute('aria-live', 'polite');
      node.innerHTML = `<span class="sg-spinner" aria-hidden="true"></span><span>${escapeHtml(label)}</span>`;
      document.body.appendChild(node);
      return {
        close() { node.remove(); },
        setLabel(newLabel) { node.querySelector('span:last-child').textContent = newLabel; },
      };
    },
    /** 버튼에 인라인 스피너를 끼우고 disabled. 반환된 restore()로 원복. */
    bindButton(btn, busyLabel) {
      if (!btn) return () => {};
      const prevHTML = btn.innerHTML;
      const prevDisabled = btn.disabled;
      btn.disabled = true;
      btn.innerHTML = `<span class="sg-spinner sm" aria-hidden="true"></span>${busyLabel ? `<span style="margin-left:8px">${escapeHtml(busyLabel)}</span>` : ''}`;
      return function restore() {
        btn.innerHTML = prevHTML;
        btn.disabled = prevDisabled;
      };
    },
  };

  // ─── Util ──────────────────────────────────────────────────────────────────
  const Util = {
    /** YYYY-MM-DD 기준 D-day 문자열. 음수면 D+N (지남). 오늘이면 D-DAY */
    dday(dateStr) {
      if (!dateStr) return '';
      const target = new Date(dateStr + 'T00:00:00');
      const now = new Date(); now.setHours(0,0,0,0);
      const diff = Math.round((target - now) / 86400000);
      if (Number.isNaN(diff)) return '';
      if (diff === 0) return 'D-DAY';
      if (diff > 0) return `D-${diff}`;
      return `D+${-diff}`;
    },
    /** 'HH:MM' 또는 'HH:MM:SS' → '오전 9:30' / '오후 2:00' */
    formatTimeKo(t) {
      if (!t) return '';
      const [hh, mm] = t.split(':').map(Number);
      if (Number.isNaN(hh)) return t;
      const ampm = hh < 12 ? '오전' : '오후';
      const h12 = ((hh % 12) || 12);
      const mmStr = String(mm || 0).padStart(2, '0');
      return `${ampm} ${h12}:${mmStr}`;
    },
    /** YYYY-MM-DD → 5월 10일(일) */
    formatDateKo(dateStr) {
      if (!dateStr) return '';
      const d = new Date(dateStr + 'T00:00:00');
      if (Number.isNaN(d.getTime())) return dateStr;
      const days = ['일','월','화','수','목','금','토'];
      return `${d.getMonth()+1}월 ${d.getDate()}일(${days[d.getDay()]})`;
    },
    /** 두 좌표 사이 거리 (km, 소수 1자리) — Haversine */
    distanceKm(lat1, lng1, lat2, lng2) {
      if ([lat1, lng1, lat2, lng2].some(v => v == null || Number.isNaN(v))) return null;
      const R = 6371;
      const toRad = d => d * Math.PI / 180;
      const dLat = toRad(lat2 - lat1);
      const dLng = toRad(lng2 - lng1);
      const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLng/2)**2;
      return Math.round(2 * R * Math.asin(Math.sqrt(a)) * 10) / 10;
    },
    petSpeciesLabel(species) {
      return ({ DOG:'강아지', CAT:'고양이', OTHER:'기타' })[species] || species || '';
    },
    /** 시·동 라벨 */
    regionLabel(user) {
      if (!user) return '시흥시';
      return user.region_dong || user.region_si || '시흥시';
    },
  };

  // ─── PreviewApp ────────────────────────────────────────────────────────────
  const PreviewApp = {
    Auth, API, Bind, DebugPanel, WS, Toast, Util,
  };

  // ─── Page boot: 홈 ─────────────────────────────────────────────────────────
  PreviewApp.bootHome = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    // 초기 데이터 로딩 동안 정적 placeholder를 스켈레톤으로 대체
    const newsFeatTitle = document.querySelector('.news-feat .nf-title');
    const newsFeatMeta = document.querySelector('.news-feat .nf-meta');
    const newsFeatCat = document.querySelector('.news-feat .nf-cat');
    if (newsFeatTitle) newsFeatTitle.innerHTML = '<span class="sk-box sk-line lg sk-w-90" style="display:block;margin-bottom:6px"></span><span class="sk-box sk-line lg sk-w-60" style="display:block"></span>';
    if (newsFeatMeta) newsFeatMeta.innerHTML = '<span class="sk-box sk-line sm sk-w-50" style="display:inline-block;min-width:90px"></span>';
    if (newsFeatCat) newsFeatCat.innerHTML = '<span class="sk-box sk-line sm" style="display:inline-block;width:32px;height:11px"></span>';
    document.querySelectorAll('.news-rows .news-row').forEach((row) => {
      const titleEl = row.querySelector('.nr-title');
      const dateEl = row.querySelector('.nr-date');
      const catEl = row.querySelector('.nr-cat');
      if (titleEl) titleEl.innerHTML = '<span class="sk-box sk-line sm sk-w-90" style="display:inline-block;min-width:140px"></span>';
      if (dateEl) dateEl.innerHTML = '<span class="sk-box sk-line sm" style="display:inline-block;width:28px;height:11px"></span>';
      if (catEl) catEl.innerHTML = '<span class="sk-box sk-line sm" style="display:inline-block;width:28px;height:11px"></span>';
    });
    document.querySelectorAll('[data-fill="weather-temp"], [data-fill="weather-cond"], [data-fill="weather-dust"], [data-fill="nearby-store-count"]').forEach((el) => {
      el.innerHTML = '<span class="sk-box sk-line sm" style="display:inline-block;min-width:30px;height:11px"></span>';
    });

    try {
      const [dash, newsData] = await Promise.all([
        API.get('/api/v1/home/dashboard'),
        API.get('/api/v1/news'),
      ]);

      // 기본 바인딩
      Bind.apply(document, dash);

      // role 분기
      const root = document.getElementById('appRoot');
      if (root) {
        const role = (dash.user?.role || 'USER').toLowerCase();
        root.setAttribute('data-role', role === 'volunteer' || role === 'admin' ? 'volunteer' : 'user');
      }

      // eyebrow / region pill — 시·동 라벨
      const regionLabel = Util.regionLabel(dash.user);
      document.querySelectorAll('[data-fill="region"]').forEach(el => el.textContent = regionLabel);
      const eyebrow = document.querySelector('.hero-eyebrow');
      if (eyebrow) eyebrow.textContent = `시흥가개 · ${regionLabel}`;

      // 날씨/산책지수
      const w = dash.weather;
      if (w) {
        const tempEl = document.querySelector('[data-fill="weather-temp"]');
        if (tempEl) tempEl.textContent = (w.temp_c != null) ? `${Math.round(w.temp_c)}°` : '—';
        const condMap = { CLEAR:'맑음', CLOUDY:'흐림', RAIN:'비', SNOW:'눈' };
        const condEl = document.querySelector('[data-fill="weather-cond"]');
        if (condEl) condEl.textContent = condMap[w.condition] || w.condition || '';
        const dustMap = { GOOD:'미세먼지 좋음', NORMAL:'미세먼지 보통', BAD:'미세먼지 나쁨', VERY_BAD:'미세먼지 매우나쁨' };
        const dustEl = document.querySelector('[data-fill="weather-dust"]');
        if (dustEl) dustEl.textContent = dustMap[w.dust_grade] || '';
      }

      // 주변 매장 수
      const storeCountEl = document.querySelector('[data-fill="nearby-store-count"]');
      if (storeCountEl && dash.nearby_store_count != null) {
        storeCountEl.textContent = `${dash.nearby_store_count}곳`;
      }

      // 알림 dot
      const dot = document.querySelector('.tb-bell .dot');
      if (dot) dot.hidden = !dash.unread_notification_count;

      // 매칭 pill — D-day 계산
      const matchSrc = dash.my_match_summary?.as_author || dash.my_match_summary?.as_applicant;
      const pill = document.querySelector('.match-pill');
      if (pill) {
        if (matchSrc) {
          pill.hidden = false;
          pill.href = `match-detail.html?id=${matchSrc.match_id}`;
          const pillText = pill.querySelector('.match-pill-text');
          if (pillText) {
            const apCnt = matchSrc.applications_count;
            pillText.textContent = apCnt ? `${matchSrc.title} · 신청 ${apCnt}건` : matchSrc.title;
          }
          const dday = pill.querySelector('.match-pill-dday');
          if (dday) dday.textContent = Util.dday(matchSrc.desired_date) || '';
        } else {
          pill.hidden = true;
        }
      }

      // 봉사자 배너 (role=volunteer 일 때)
      if (dash.volunteer_stats) {
        const vs = dash.volunteer_stats;
        const totalEl = document.querySelector('[data-fill="vol-total"]');
        if (totalEl) totalEl.textContent = `${vs.total_count}건`;
        const ratingEl = document.querySelector('[data-fill="vol-rating"]');
        if (ratingEl) ratingEl.textContent = vs.avg_rating != null ? vs.avg_rating.toFixed(1) : '—';
      }

      // 홈 뉴스 프리뷰
      const CAT_LABEL = { POLICY:'정책', EVENT:'행사', VOLUNTEER:'봉사', SUPPORT:'지원', BADGE:'인증' };
      const news = newsData.news || [];
      const featEl = document.querySelector('.news-feat');
      if (featEl && news[0]) {
        const n = news[0];
        featEl.href = `news-detail.html?id=${n.news_id}`;
        const img = featEl.querySelector('.nf-img');
        if (img) {
          if (n.image_url) { img.src = n.image_url; img.style.display = ''; }
          else img.style.display = 'none';
        }
        const catEl = featEl.querySelector('.nf-cat');
        if (catEl) catEl.textContent = CAT_LABEL[n.category] || n.category;
        const titleEl = featEl.querySelector('.nf-title');
        if (titleEl) titleEl.textContent = n.title;
        const metaEl = featEl.querySelector('.nf-meta');
        if (metaEl) metaEl.textContent = `${n.published_date} · ${n.publisher || ''}`;
      }
      const newsRows = document.querySelectorAll('.news-rows .news-row');
      news.slice(1, 4).forEach((item, i) => {
        const row = newsRows[i];
        if (!row) return;
        row.href = `news-detail.html?id=${item.news_id}`;
        const catEl = row.querySelector('.nr-cat');
        if (catEl) {
          const cls = { POLICY:'policy', EVENT:'event', VOLUNTEER:'volunteer', SUPPORT:'support', BADGE:'policy' };
          catEl.className = `nr-cat ${cls[item.category] || ''}`;
          catEl.textContent = CAT_LABEL[item.category] || item.category;
        }
        const titleEl = row.querySelector('.nr-title');
        if (titleEl) titleEl.textContent = item.title;
        const dateEl = row.querySelector('.nr-date');
        if (dateEl) dateEl.textContent = item.published_date ? item.published_date.slice(5) : '';
      });
    } catch (err) {
      Toast.error(`홈 로딩 실패: ${err.message}`);
    }

    // GPS 위치 기반 region pill 덮어쓰기
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const { latitude, longitude } = pos.coords;
          const geo = await API.get(
            `/api/v1/geo/reverse?lat=${latitude}&lng=${longitude}`,
          );
          document.querySelectorAll('[data-fill="region"]').forEach(el => el.textContent = geo.label);
        } catch (err) {
          DebugPanel.log({ method: "GEO", path: "/geo/reverse", status: 0, err: err.message });
        }
      },
      (err) => {
        DebugPanel.log({ method: "GEO", path: "navigator.geolocation", status: 0, err: err.message });
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 5 * 60 * 1000 },
    );
  };

  // ─── Page boot: 내 정보 ────────────────────────────────────────────────────
  PreviewApp.bootMy = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    // 프로필/통계 스켈레톤
    const profileName = document.querySelector('.profile-name');
    if (profileName) profileName.innerHTML = '<span class="sk-box sk-line lg sk-w-60" style="display:inline-block;min-width:90px"></span>';
    const profileRegion = document.querySelector('.profile-region span[data-bind="region_dong"]');
    if (profileRegion) profileRegion.innerHTML = '<span class="sk-box sk-line sm sk-w-50" style="display:inline-block;min-width:50px"></span>';
    document.querySelectorAll('.stat-num').forEach((el) => {
      el.innerHTML = '<span class="sk-box sk-line lg sk-w-50" style="display:inline-block;min-width:28px;height:18px"></span>';
    });
    // 매칭 리스트 영역 (author / applicant) 스켈레톤
    document.querySelectorAll('.my-requests').forEach((el) => {
      el.innerHTML = Loading.skeletonRows(2);
    });
    // 펫 스크롤 스피너
    const petsScroll = document.getElementById('pets-scroll') || document.querySelector('.pets-scroll');
    if (petsScroll) {
      const placeholder = document.createElement('div');
      placeholder.className = 'pets-loading-placeholder';
      placeholder.innerHTML = '<span class="sg-spinner sm" aria-hidden="true"></span>';
      placeholder.style.cssText = 'flex:1;display:flex;align-items:center;justify-content:flex-start;padding:0 12px;gap:8px;color:var(--ink-mute);font-size:12px';
      petsScroll.insertBefore(placeholder, petsScroll.firstChild);
    }

    function renderPets(pets) {
      const scroll = document.getElementById('pets-scroll') || document.querySelector('.pets-scroll');
      if (!scroll) return;
      scroll.querySelectorAll('.pet-v-card').forEach((c) => c.remove());
      scroll.querySelector('.pets-loading-placeholder')?.remove();
      const addBtn = scroll.querySelector('.pet-v-add');

      (pets || []).forEach((p) => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'pet-v-card';
        const speciesCls = p.species === 'CAT' ? 'cat' : (p.species === 'OTHER' ? 'other' : 'dog');
        const speciesIcon = p.species === 'CAT' ? 'cat' : (p.species === 'OTHER' ? 'paw-print' : 'dog');
        const speciesLabel = Util.petSpeciesLabel(p.species);
        card.innerHTML = `
          <div class="pet-v-icon ${speciesCls}"><i class="ph ph-${speciesIcon}"></i></div>
          <div class="pet-v-name"></div>
          <div class="pet-v-info"></div>`;
        card.querySelector('.pet-v-name').textContent = p.name || '—';
        const ageStr = p.age != null ? `${p.age}살` : '';
        card.querySelector('.pet-v-info').textContent = [speciesLabel, p.breed, ageStr].filter(Boolean).join(' · ');
        card.addEventListener('click', () => {
          location.href = `pet-form.html?pet_id=${p.id}`;
        });
        if (addBtn) scroll.insertBefore(card, addBtn);
        else scroll.appendChild(card);
      });

      // 펫 0건이면 빈 상태 메시지 (추가 버튼은 유지)
      if (!pets || pets.length === 0) {
        const empty = scroll.querySelector('.pets-empty');
        if (!empty) {
          const div = document.createElement('div');
          div.className = 'pets-empty';
          div.textContent = '아직 등록한 반려동물이 없어요';
          div.style.cssText = 'flex:1;display:flex;align-items:center;color:var(--ink-mute);font-size:12.5px;font-weight:600;padding:0 8px';
          scroll.insertBefore(div, addBtn);
        }
      }
    }

    try {
      const [me, stats, author_matches, applicant_matches] = await Promise.all([
        API.get("/api/v1/users/me"),
        API.get("/api/v1/users/me/activity-stats"),
        API.get("/api/v1/users/me/matches?role=author&size=3"),
        API.get("/api/v1/users/me/matches?role=applicant&size=3"),
      ]);

      renderPets(me.pets);
      const combined = { ...me, pets: undefined, ...stats, author_matches, applicant_matches };
      Bind.apply(document, combined);

      // 봉사자 권한 가시성 (등급 신청 메뉴 vs 봉사 이력 메뉴)
      const root = document.getElementById('appRoot');
      if (root) root.setAttribute('data-role', (me.role || 'USER').toLowerCase());
    } catch (err) {
      // 실패 시에도 스켈레톤은 제거 (대시 표시 폴백)
      if (profileName) profileName.textContent = '—';
      if (profileRegion) profileRegion.textContent = '—';
      document.querySelectorAll('.stat-num').forEach((el) => { el.textContent = '—'; });
      document.querySelectorAll('.my-requests').forEach((el) => { el.innerHTML = ''; });
      petsScroll?.querySelector('.pets-loading-placeholder')?.remove();
      Toast.error(`내 정보 로딩 실패: ${err.message}`);
    }
  };

  // ─── Page boot: 매칭 리스트 ────────────────────────────────────────────────
  PreviewApp.bootMatch = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const STATUS_LABEL = { WAITING:'모집중', MATCHING:'검토중', PROGRESS:'진행중', DONE:'완료' };

    function postProcess() {
      document.querySelectorAll('#match-list .mc').forEach((card) => {
        const badge = card.querySelector('.mc-badge');
        if (!badge) return;
        const raw = badge.textContent.trim();
        badge.textContent = STATUS_LABEL[raw] || raw;
        badge.dataset.s = raw;
        card.dataset.s = raw;
      });
      document.querySelectorAll('#match-list a.mc[href^="#match-"]').forEach((a) => {
        const id = a.getAttribute('href').replace('#match-', '');
        if (id) a.href = `match-detail.html?id=${id}`;
      });
    }

    const tabs = document.querySelectorAll('.match-tabs .match-tab');
    let currentStatus = '';

    // 탭별 카운트 (전체 / 모집중 / 검토중 / 진행중)를 별도 호출로 채움
    async function updateTabCounts() {
      try {
        const [all, waiting, matching, progress, done] = await Promise.all([
          API.get('/api/v1/matches?size=1'),
          API.get('/api/v1/matches?status=WAITING&size=1'),
          API.get('/api/v1/matches?status=MATCHING&size=1'),
          API.get('/api/v1/matches?status=PROGRESS&size=1'),
          API.get('/api/v1/matches?status=DONE&size=1'),
        ]);
        const setCnt = (status, total) => {
          const tab = document.querySelector(`.match-tab[data-status="${status}"] .tab-cnt`);
          if (tab) tab.textContent = total;
        };
        setCnt('', all.total);
        setCnt('WAITING', waiting.total);
        setCnt('MATCHING', matching.total);
        setCnt('PROGRESS', progress.total);
        setCnt('DONE', done.total);
      } catch { /* 카운트 실패는 무시 */ }
    }

    async function load(status) {
      const qs = status ? `?status=${status}` : '';
      const listEl = document.getElementById('match-list');
      const emptyEl = document.getElementById('match-empty');
      if (listEl) listEl.innerHTML = Loading.skeletonCards(4);
      if (emptyEl) emptyEl.hidden = true;
      try {
        const data = await API.get(`/api/v1/matches${qs}`);
        Bind.apply(document, data); // 스켈레톤은 data-bind-each가 innerHTML을 비우며 자동 대체
        postProcess();
        if (emptyEl) emptyEl.hidden = (data.items || []).length > 0;
      } catch (err) {
        if (listEl) listEl.innerHTML = '';
        Toast.error(`매칭 목록 실패: ${err.message}`);
      }
    }

    // 활동 요약 카드
    const reqEl = document.querySelector('.mac-side:first-child .mac-val');
    const volEl = document.querySelector('.mac-side:last-child .mac-val');
    if (reqEl) reqEl.innerHTML = '<span class="sk-box sk-line lg sk-w-50" style="display:inline-block;min-width:42px;height:16px"></span>';
    if (volEl) volEl.innerHTML = '<span class="sk-box sk-line lg sk-w-50" style="display:inline-block;min-width:42px;height:16px"></span>';
    try {
      const [author, applicant] = await Promise.all([
        API.get('/api/v1/users/me/matches?role=author&status=WAITING&size=1'),
        API.get('/api/v1/users/me/matches?role=applicant&status=PROGRESS&size=1'),
      ]);
      if (reqEl) reqEl.innerHTML = `${author.total}건<span>검토 중</span>`;
      if (volEl) volEl.innerHTML = `${applicant.total}건<span>진행 중</span>`;
    } catch {
      if (reqEl) reqEl.innerHTML = '—<span>검토 중</span>';
      if (volEl) volEl.innerHTML = '—<span>진행 중</span>';
    }

    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        currentStatus = tab.dataset.status || '';
        load(currentStatus);
      });
    });

    document.querySelector('.match-fab')?.addEventListener('click', (e) => {
      e.preventDefault();
      location.href = 'match-new.html';
    });

    await load(currentStatus);
    updateTabCounts();
  };

  // ─── Page boot: 지도 ─────────────────────────────────────────────────────
  PreviewApp.bootMap = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    // map.html에서 iframe과 canvas 충돌 — canvas만 사용
    const mapCanvas = document.getElementById('kakao-map-canvas');
    const mapIframe = document.getElementById('mapIframe');
    if (mapIframe) mapIframe.style.display = 'none';
    if (mapCanvas) {
      mapCanvas.innerHTML = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#B8D9D9,#D4E8C4);font-size:13px;font-weight:700;color:rgba(30,18,10,0.45);">📍 지도 (카카오 SDK 연동 예정)</div>';
    }

    let userLat = 37.3451, userLng = 126.7322;
    const radius = 3000;
    let currentCat = '';

    function attachStoreHrefs() {
      document.querySelectorAll('#store-list a.place-row').forEach((a) => {
        const id = a.dataset.storeId;
        if (id && a.getAttribute('href') !== `store-detail.html?id=${id}`) {
          a.href = `store-detail.html?id=${id}`;
        }
      });
    }

    async function loadNearby(cat) {
      const catQs = cat ? `&category=${cat}` : '';
      try {
        const data = await API.get(`/api/v1/maps/stores?lat=${userLat}&lng=${userLng}&radius=${radius}${catQs}`);
        // distance_m → m 단위 정수로 변환 후 바인딩
        const stores = (data.stores || []).map(s => ({
          ...s,
          distance_label: s.distance_m != null ? (s.distance_m < 1000 ? `${Math.round(s.distance_m)}m` : `${(s.distance_m/1000).toFixed(1)}km`) : '—',
          category_label: ({CAFE:'카페',PARK:'공원',VET:'병원',RESTAURANT:'식당',GROOMING:'미용'}[s.category] || s.category),
        }));
        Bind.apply(document, { stores });
        attachStoreHrefs();
        const empty = document.getElementById('store-empty');
        if (empty) empty.hidden = stores.length > 0;
      } catch (err) {
        Toast.error(`매장 로딩 실패: ${err.message}`);
      }
    }

    async function loadSearch(keyword) {
      try {
        const data = await API.get(`/api/v1/maps/stores/search?keyword=${encodeURIComponent(keyword)}`);
        const stores = (data.results || []).map(r => ({
          ...r,
          distance_label: '—',
          category_label: ({CAFE:'카페',PARK:'공원',VET:'병원',RESTAURANT:'식당',GROOMING:'미용'}[r.category] || r.category),
        }));
        Bind.apply(document, { stores });
        attachStoreHrefs();
      } catch (err) {
        Toast.error(`검색 실패: ${err.message}`);
      }
    }

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => { userLat = pos.coords.latitude; userLng = pos.coords.longitude; loadNearby(currentCat); },
        () => {},
        { enableHighAccuracy: false, timeout: 6000, maximumAge: 300000 }
      );
    }

    const searchInput = document.getElementById('map-search-input');
    if (searchInput) {
      let timer = null;
      searchInput.addEventListener('input', () => {
        clearTimeout(timer);
        const v = searchInput.value.trim();
        timer = setTimeout(() => v ? loadSearch(v) : loadNearby(currentCat), 300);
      });
    }

    document.querySelectorAll('.chips-row .chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.chips-row .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        // data-cat 속성 우선 사용 (텍스트 매핑 의존성 제거)
        const cat = (chip.dataset.cat || '').toUpperCase();
        currentCat = (cat === 'ALL' || !cat) ? '' : cat;
        loadNearby(currentCat);
      });
    });

    // FAB: 신규 매장 등록
    document.querySelector('.map-fab')?.addEventListener('click', (e) => {
      e.preventDefault();
      location.href = 'store-add.html';
    });

    await loadNearby(currentCat);
  };

  // ─── Page boot: 매칭 생성/수정 ────────────────────────────────────────────
  PreviewApp.bootMatchNew = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const params = new URLSearchParams(location.search);
    const editId = params.get('edit') ? parseInt(params.get('edit'), 10) : null;
    const isEdit = !!editId;

    const state = {
      petId: null,
      date: null,
      time: null,
      title: '',
      address: '',
      content: '',
      latitude: 37.3451,
      longitude: 126.7322,
    };
    let myPets = [];

    if (isEdit) {
      const titleEl = document.querySelector('.wiz-title');
      if (titleEl) titleEl.textContent = '요청 수정';
    }

    const steps = document.querySelectorAll('.wizard-step');
    function showStep(n) {
      steps.forEach((s, i) => s.hidden = i !== n);
      const indicator = document.getElementById('step-indicator');
      if (indicator) indicator.textContent = `${n+1}/3`;
    }

    function fillCalendar(year, month) {
      const cal = document.getElementById('calendar-grid');
      if (!cal) return;
      const firstDay = new Date(year, month, 1).getDay();
      const daysInMonth = new Date(year, month + 1, 0).getDate();
      const today = new Date(); today.setHours(0,0,0,0);
      const lbl = document.getElementById('cal-month-label');
      if (lbl) lbl.textContent = `${year}년 ${month+1}월`;
      cal.innerHTML = '';
      for (let i = 0; i < firstDay; i++) cal.insertAdjacentHTML('beforeend', '<span></span>');
      for (let d = 1; d <= daysInMonth; d++) {
        const btn = document.createElement('button');
        btn.type = 'button'; btn.textContent = d; btn.className = 'cal-day';
        const cellDate = new Date(year, month, d);
        if (cellDate < today) { btn.disabled = true; btn.className += ' past'; }
        const iso = `${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
        if (state.date === iso) btn.classList.add('selected');
        btn.addEventListener('click', () => {
          cal.querySelectorAll('.cal-day').forEach(b => b.classList.remove('selected'));
          btn.classList.add('selected');
          state.date = iso;
        });
        cal.appendChild(btn);
      }
    }

    let calYear = new Date().getFullYear(), calMonth = new Date().getMonth();

    // 펫 그리드 로딩 자리표시자
    const petGridEl = document.getElementById('pet-select-grid');
    if (petGridEl) {
      petGridEl.innerHTML = '<div class="sk-box" style="height:96px;width:120px;border-radius:14px"></div><div class="sk-box" style="height:96px;width:120px;border-radius:14px"></div>';
    }

    try {
      const me = await API.get('/api/v1/users/me');
      myPets = me.pets || [];
      const petGrid = document.getElementById('pet-select-grid');
      if (petGrid) {
        petGrid.innerHTML = '';
        myPets.forEach((p) => {
          const card = document.createElement('button');
          card.type = 'button';
          card.className = 'pet-v-card';
          card.dataset.petId = p.id;
          const speciesCls = p.species === 'CAT' ? 'cat' : (p.species === 'OTHER' ? 'other' : 'dog');
          const speciesIcon = p.species === 'CAT' ? 'cat' : (p.species === 'OTHER' ? 'paw-print' : 'dog');
          card.innerHTML = `
            <div class="pet-v-icon ${speciesCls}"><i class="ph ph-${speciesIcon}"></i></div>
            <div class="pet-v-name"></div>
            <div class="pet-v-info">${Util.petSpeciesLabel(p.species)}${p.breed ? ' · ' + p.breed : ''}</div>`;
          card.querySelector('.pet-v-name').textContent = p.name;
          card.addEventListener('click', () => {
            petGrid.querySelectorAll('.pet-v-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            state.petId = p.id;
          });
          petGrid.appendChild(card);
        });
        // 펫 없으면 추가 카드
        if (myPets.length === 0) {
          const addCard = document.createElement('a');
          addCard.href = 'pet-form.html';
          addCard.className = 'pet-v-add';
          addCard.style.textDecoration = 'none';
          addCard.innerHTML = '<i class="ph ph-plus"></i>반려동물 추가';
          petGrid.appendChild(addCard);
        }
      }

      // 편집 모드: 기존 매칭 데이터 prefill
      if (isEdit) {
        const detail = await API.get(`/api/v1/matches/${editId}`);
        // 소유자/상태 가드 — URL 직접 접근으로 남의 매칭 편집 폼이 열리는 것을 막는다.
        if (detail.author?.user_id !== me.id) {
          Toast.error('본인이 작성한 요청만 수정할 수 있습니다.');
          setTimeout(() => location.replace(`match-detail.html?id=${editId}`), 600);
          return;
        }
        if (detail.status !== 'WAITING' && detail.status !== 'MATCHING') {
          Toast.error('이미 진행 중이거나 완료된 매칭은 수정할 수 없습니다.');
          setTimeout(() => location.replace(`match-detail.html?id=${editId}`), 600);
          return;
        }
        state.title = detail.title || '';
        state.address = detail.address || '';
        state.content = detail.content || '';
        state.date = detail.desired_date || null;
        state.time = detail.desired_time ? detail.desired_time.slice(0,5) : null;
        state.latitude = detail.latitude;
        state.longitude = detail.longitude;
        state.petId = detail.pet?.pet_id ?? null;
        if (state.petId) {
          const card = document.querySelector(`.pet-v-card[data-pet-id="${state.petId}"]`);
          if (card) card.classList.add('selected');
        }
        const t = document.getElementById('match-title'); if (t) t.value = state.title;
        const a = document.getElementById('match-address'); if (a) a.value = state.address;
        const c = document.getElementById('match-content'); if (c) c.value = state.content;
        // 시간 chip
        if (state.time) {
          document.querySelectorAll('.time-chip').forEach(ch => {
            if (ch.dataset.time === state.time) ch.classList.add('active');
          });
        }
      }
    } catch (err) {
      Toast.error(`로딩 실패: ${err.message}`);
    }

    document.getElementById('btn-step1-next')?.addEventListener('click', () => {
      if (!state.petId) { Toast.error('반려동물을 선택해 주세요.'); return; }
      showStep(1);
      fillCalendar(calYear, calMonth);
    });
    document.getElementById('btn-step0-back')?.addEventListener('click', () => history.back());
    document.getElementById('btn-step2-back')?.addEventListener('click', () => showStep(0));
    document.getElementById('btn-step3-back')?.addEventListener('click', () => showStep(1));

    document.getElementById('cal-prev')?.addEventListener('click', () => {
      calMonth--; if (calMonth < 0) { calMonth = 11; calYear--; }
      fillCalendar(calYear, calMonth);
    });
    document.getElementById('cal-next')?.addEventListener('click', () => {
      calMonth++; if (calMonth > 11) { calMonth = 0; calYear++; }
      fillCalendar(calYear, calMonth);
    });

    document.querySelectorAll('.time-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.time-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        state.time = chip.dataset.time;
      });
    });

    document.getElementById('btn-step2-next')?.addEventListener('click', () => {
      if (!state.date) { Toast.error('날짜를 선택해 주세요.'); return; }
      showStep(2);
    });

    // 주소 입력 시 GPS 위치를 사용하지 않고 카카오 geocoding 호출 시도.
    // /geo/reverse는 좌표→주소 변환이라 정방향(주소→좌표)이 없으므로
    // 폴백: 현재 GPS 좌표 사용. (안드로이드에선 카카오 Local API 정방향 호출 필요.)
    async function resolveCoords() {
      // 1) GPS가 가능하면 사용자 위치 사용
      if (navigator.geolocation) {
        try {
          const pos = await new Promise((res, rej) =>
            navigator.geolocation.getCurrentPosition(res, rej, { timeout: 4000, maximumAge: 5*60*1000 })
          );
          return { lat: pos.coords.latitude, lng: pos.coords.longitude };
        } catch (_) {}
      }
      // 2) 폴백: 정왕동 좌표
      return { lat: state.latitude, lng: state.longitude };
    }

    document.getElementById('match-new-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      state.title = document.getElementById('match-title').value.trim();
      state.address = document.getElementById('match-address').value.trim();
      state.content = document.getElementById('match-content').value.trim();
      if (!state.title) { Toast.error('제목을 입력해 주세요.'); return; }
      if (!state.content) { Toast.error('요청 내용을 입력해 주세요.'); return; }
      const btn = e.submitter || e.target.querySelector('[type=submit]');
      const restoreBtn = Loading.bindButton(btn, isEdit ? '수정 중...' : '등록 중...');
      try {
        if (isEdit) {
          const body = {
            pet_id: state.petId,
            title: state.title,
            address: state.address || null,
            content: state.content,
            desired_date: state.date,
            desired_time: state.time,
          };
          await API.patch(`/api/v1/matches/${editId}`, body);
          Toast.ok('요청이 수정되었습니다.');
          setTimeout(() => location.href = `match-detail.html?id=${editId}`, 600);
        } else {
          const { lat, lng } = await resolveCoords();
          const body = {
            pet_id: state.petId,
            title: state.title,
            address: state.address || null,
            content: state.content,
            desired_date: state.date,
            desired_time: state.time,
            latitude: lat,
            longitude: lng,
          };
          const created = await API.post('/api/v1/matches', body);
          location.href = `match-detail.html?id=${created.match_id}`;
        }
      } catch (err) {
        Toast.error(`요청 처리 실패: ${err.message}`);
        restoreBtn();
      }
    });

    showStep(0);
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

    if (!appId) {
      try {
        if (!matchId) {
          const mine = await API.get("/api/v1/users/me/matches?role=applicant&size=1");
          const first = mine.items?.[0];
          if (first && first.my_application_status !== "REJECTED") {
            matchId = first.match_id;
          }
        }
        if (matchId) {
          const savedAppId = localStorage.getItem(`sg_app_${matchId}`);
          if (savedAppId) {
            appId = parseInt(savedAppId, 10);
          } else {
            const list = await API.get(`/api/v1/matches/${matchId}/applications`);
            const own = list.items?.find((a) => a.applicant?.applicant_id === me.id);
            appId = own?.application_id;
          }
        }
      } catch { /* fallback 실패는 무시 */ }
    }
    if (!appId || !matchId) {
      Toast.error("채팅방을 결정할 수 없습니다. ?match_id=&application_id= 쿼리를 붙여 주세요.");
      return;
    }

    // 채팅 상대 정보 가져와서 헤더에 표시
    try {
      const detail = await API.get(`/api/v1/matches/${matchId}`);
      const titleEl = document.querySelector('.chat-room-title');
      if (titleEl) titleEl.textContent = detail.title || '이동 지원 채팅';
      const subtitleEl = document.querySelector('.chat-room-subtitle');
      if (subtitleEl && detail.desired_date) {
        subtitleEl.textContent = `${Util.formatDateKo(detail.desired_date)}${detail.desired_time ? ' · ' + Util.formatTimeKo(detail.desired_time) : ''}`;
      }
    } catch {}

    const listEl = document.getElementById("chat-messages");
    // 메시지 초기 로딩 스피너
    if (listEl) {
      listEl.innerHTML = Loading.spinnerHTML('메시지를 불러오는 중...');
    }
    function escapeHtmlLocal(s) {
      return String(s).replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));
    }
    function fmtTime(iso) {
      const d = new Date(iso);
      const h = d.getHours(), m = d.getMinutes();
      const ampm = h < 12 ? '오전' : '오후';
      return `${ampm} ${(h%12)||12}:${String(m).padStart(2,'0')}`;
    }
    function renderMsg(msg) {
      const row = document.createElement("div");
      row.className = "ch-msg " + (msg.sender_id === me.id ? "mine" : "other");
      row.innerHTML = `
        <div class="ch-bubble">${escapeHtmlLocal(msg.content)}</div>
        <div class="ch-time">${escapeHtmlLocal(fmtTime(msg.created_at || new Date().toISOString()))}</div>
      `;
      listEl.appendChild(row);
      listEl.scrollTop = listEl.scrollHeight;
    }

    const seen = new Set();
    try {
      const initial = await API.get(`/api/v1/matches/${matchId}/applications/${appId}/messages?size=30`);
      if (listEl) listEl.innerHTML = '';
      const items = initial.items || [];
      items.forEach((m) => seen.add(m.id));
      [...items].reverse().forEach(renderMsg);
    } catch (err) {
      if (listEl) listEl.innerHTML = '';
      Toast.error(`메시지 로딩 실패: ${err.message}`);
    }

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

    // 신고 버튼
    document.getElementById('btn-chat-report')?.addEventListener('click', () => {
      location.href = `reports.html?type=chat&match_id=${matchId}&application_id=${appId}`;
    });
  };

  // ─── Page boot: 소식 ──────────────────────────────────────────────────────
  PreviewApp.bootNews = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const CAT_LABEL = { POLICY:'정책', EVENT:'행사', VOLUNTEER:'봉사', SUPPORT:'지원', BADGE:'인증' };
    let allNews = [];

    function renderNews(list) {
      const feat = document.getElementById('news-feat');
      const rows = document.getElementById('news-rows');
      const empty = document.getElementById('news-empty');
      if (empty) empty.hidden = list.length > 0;
      if (!list.length) {
        if (feat) feat.hidden = true;
        if (rows) rows.innerHTML = '';
        return;
      }

      const first = list[0];
      if (feat) {
        feat.href = `news-detail.html?id=${first.news_id}`;
        feat.hidden = false;
        const img = feat.querySelector('.nf-img');
        if (img) {
          if (first.image_url) { img.src = first.image_url; img.style.display = ''; }
          else img.style.display = 'none';
        }
        const catEl = feat.querySelector('.nf-cat');
        if (catEl) catEl.textContent = CAT_LABEL[first.category] || first.category;
        const titleEl = feat.querySelector('.nf-title');
        if (titleEl) titleEl.textContent = first.title;
        const metaEl = feat.querySelector('.nf-meta');
        if (metaEl) metaEl.textContent = `${first.published_date} · ${first.publisher || '네이버 뉴스'}`;
      }

      if (rows) {
        const tmpl = document.getElementById('tmpl-news-row');
        rows.innerHTML = '';
        list.slice(1).forEach((item) => {
          const node = tmpl.content.cloneNode(true);
          const a = node.querySelector('a');
          if (a) a.href = `news-detail.html?id=${item.news_id}`;
          const catEl = node.querySelector('.nr-cat');
          if (catEl) {
            catEl.textContent = CAT_LABEL[item.category] || item.category;
            const catClass = { POLICY:'policy', EVENT:'event', VOLUNTEER:'volunteer', SUPPORT:'support', BADGE:'policy' };
            catEl.className = `nr-cat ${catClass[item.category] || ''}`;
          }
          const titleEl = node.querySelector('.nr-title');
          if (titleEl) titleEl.textContent = item.title;
          const dateEl = node.querySelector('.nr-date');
          if (dateEl) dateEl.textContent = item.published_date ? item.published_date.slice(5) : '';
          rows.appendChild(node);
        });
      }
    }

    const rowsEl = document.getElementById('news-rows');
    const featEl = document.getElementById('news-feat');
    const newsEmptyEl = document.getElementById('news-empty');
    if (rowsEl) rowsEl.innerHTML = Loading.skeletonRows(3);
    if (featEl) featEl.hidden = true;
    if (newsEmptyEl) newsEmptyEl.hidden = true;
    try {
      const data = await API.get('/api/v1/news');
      allNews = data.news || [];
      renderNews(allNews);
    } catch (err) {
      if (rowsEl) rowsEl.innerHTML = '';
      Toast.error(`뉴스 로딩 실패: ${err.message}`);
    }

    // chip은 data-cat 속성 기준으로 분류 (POLICY/EVENT/VOLUNTEER/SUPPORT/BADGE)
    document.querySelectorAll('.chips-row .chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.chips-row .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        const cat = (chip.dataset.cat || '').toUpperCase();
        const filtered = (cat === 'ALL' || !cat) ? allNews : allNews.filter(n => n.category === cat);
        renderNews(filtered);
      });
    });
  };

  // ─── Page boot: 알림 ──────────────────────────────────────────────────────
  PreviewApp.bootNotifications = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    let currentCat = '';

    async function load(cat) {
      const qs = cat ? `?category=${cat}` : '';
      const listEl = document.getElementById('notif-list');
      const tmpl = document.getElementById('tmpl-notif');
      const empty = document.getElementById('notif-empty');
      if (listEl) listEl.innerHTML = Loading.skeletonRows(4);
      if (empty) empty.hidden = true;
      try {
        const data = await API.get(`/api/v1/notifications${qs}`);
        if (!listEl || !tmpl) return;
        listEl.innerHTML = '';
        const items = data.items || [];
        if (empty) empty.hidden = items.length > 0;

        const ICON_CLASS = {
          MATCH: 'type-match', VOLUNTEER: 'type-vol',
          NEWS: 'type-news', POLICY: 'type-news',
          REVIEW: 'type-review', SYSTEM: 'type-sys',
        };
        const ICON_PH = {
          MATCH: 'handshake', VOLUNTEER: 'hand-heart',
          NEWS: 'newspaper', POLICY: 'scroll',
          REVIEW: 'star', SYSTEM: 'gear',
        };

        items.forEach((item) => {
          const node = tmpl.content.cloneNode(true);
          const row = node.querySelector('.notif-item');
          if (!item.is_read) row.classList.add('unread');
          row.addEventListener('click', async (e) => {
            e.preventDefault();
            if (!item.is_read) {
              try {
                await API.patch(`/api/v1/notifications/${item.id}/read`, {});
                row.classList.remove('unread');
              } catch (err) { /* 실패해도 이동은 진행 */ }
            }
            if (item.link) location.href = item.link.startsWith('/') ? item.link.replace(/^\/matches\//, 'match-detail.html?id=').replace(/\/applications$/, '') : item.link;
          });

          const iconEl = node.querySelector('.notif-icon-wrap');
          if (iconEl) {
            iconEl.classList.add(ICON_CLASS[item.category] || 'type-sys');
            const iEl = iconEl.querySelector('i');
            if (iEl) iEl.className = `ph ph-${ICON_PH[item.category] || 'bell'}`;
          }
          const titleEl = node.querySelector('.notif-item-title');
          if (titleEl) titleEl.textContent = item.title;
          const bodyEl = node.querySelector('.notif-body');
          if (bodyEl) bodyEl.textContent = item.body;
          const timeEl = node.querySelector('.notif-time');
          if (timeEl) {
            const d = new Date(item.created_at);
            const now = new Date();
            const diffH = (now - d) / 3600000;
            if (diffH < 1) timeEl.textContent = '방금 전';
            else if (diffH < 24) timeEl.textContent = `${Math.floor(diffH)}시간 전`;
            else timeEl.textContent = `${d.getMonth()+1}.${d.getDate()}`;
          }
          listEl.appendChild(node);
        });
      } catch (err) {
        if (listEl) listEl.innerHTML = '';
        Toast.error(`알림 로딩 실패: ${err.message}`);
      }
    }

    await load(currentCat);

    document.querySelectorAll('.chips-row .chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.chips-row .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        // data-cat 속성 사용 — 6개 카테고리 전부 매핑
        const v = (chip.dataset.cat || '').toUpperCase();
        currentCat = (v === 'ALL' || !v) ? '' : v;
        load(currentCat);
      });
    });

    document.getElementById('btn-read-all')?.addEventListener('click', async () => {
      try {
        await API.patch('/api/v1/notifications/read-all', {});
        document.querySelectorAll('.notif-item.unread').forEach(el => el.classList.remove('unread'));
        Toast.ok('모두 읽음 처리되었습니다.');
      } catch (err) {
        Toast.error(err.message);
      }
    });
  };

  // ─── Page boot: 매칭 상세 ─────────────────────────────────────────────────
  PreviewApp.bootMatchDetail = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const params = new URLSearchParams(location.search);
    const matchId = parseInt(params.get('id'), 10);
    if (!matchId) { Toast.error('잘못된 접근입니다.'); return; }

    // 본문/필드를 스켈레톤으로 채워두기
    const titleEl = document.querySelector('.md-title');
    if (titleEl) titleEl.innerHTML = '<span class="sk-box sk-line xl sk-w-80" style="display:inline-block;min-width:200px;height:22px"></span>';
    document.querySelectorAll('.md-info-value').forEach((el) => {
      el.innerHTML = '<span class="sk-box sk-line sm sk-w-60" style="display:inline-block;min-width:120px"></span>';
    });
    const statusRow = document.querySelector('.md-status-row');
    if (statusRow) {
      statusRow.querySelectorAll('span').forEach((s) => {
        s.innerHTML = '<span class="sk-box sk-line sm" style="display:inline-block;width:54px;height:11px"></span>';
      });
    }

    let me, detail;
    try {
      [me, detail] = await Promise.all([
        API.get('/api/v1/users/me'),
        API.get(`/api/v1/matches/${matchId}`),
      ]);
    } catch (err) { Toast.error(err.message); return; }

    const STATUS_LABEL = { WAITING:'모집중', MATCHING:'검토중', PROGRESS:'진행중', DONE:'완료' };
    const isOwner = detail.author?.user_id === me.id;

    // 풍부 바인딩
    const dday = Util.dday(detail.desired_date);
    Bind.apply(document, {
      ...detail,
      status_label: STATUS_LABEL[detail.status] || detail.status,
      dday_label: dday,
      pet_name: detail.pet?.name || '—',
      pet_species: Util.petSpeciesLabel(detail.pet?.species),
      pet_neutered_label: detail.pet ? (detail.pet.is_neutered ? '중성화 ○' : '중성화 ×') : '',
      author_nickname: detail.author?.nickname || '—',
      desired_date_label: Util.formatDateKo(detail.desired_date),
      desired_time_label: detail.desired_time ? `${Util.formatTimeKo(detail.desired_time)} 출발 예정` : '시간 미정',
      address_label: detail.address || '주소 미입력',
      applications_count_label: detail.applications_count != null ? `봉사자 모집 중 · 신청 ${detail.applications_count}건` : '봉사자 모집 중',
    });

    // 상태에 따른 배지 스타일
    const badge = document.querySelector('.md-status-badge');
    if (badge) badge.dataset.s = detail.status;
    document.documentElement.dataset.matchStatus = detail.status;

    // 작성자 전용 액션 (수정/삭제/상태변경)
    const ownerActions = document.getElementById('owner-actions');
    if (ownerActions) ownerActions.hidden = !isOwner;
    document.getElementById('btn-edit-match')?.addEventListener('click', () => {
      location.href = `match-new.html?edit=${matchId}`;
    });
    document.getElementById('btn-delete-match')?.addEventListener('click', async () => {
      if (!confirm('정말 이 요청을 삭제할까요? 되돌릴 수 없습니다.')) return;
      try {
        await API.delete(`/api/v1/matches/${matchId}`);
        Toast.ok('삭제되었습니다.');
        setTimeout(() => location.href = 'match.html', 600);
      } catch (err) { Toast.error(err.message); }
    });
    document.getElementById('btn-finish-match')?.addEventListener('click', async () => {
      if (!confirm('이 봉사를 완료 처리할까요? 이후 후기를 작성할 수 있어요.')) return;
      try {
        await API.patch(`/api/v1/matches/${matchId}/status`, { status: 'DONE' });
        Toast.ok('완료 처리되었습니다.');
        setTimeout(() => location.reload(), 500);
      } catch (err) { Toast.error(err.message); }
    });

    // PROGRESS → DONE 버튼은 작성자에게 PROGRESS 상태일 때만 노출
    const finishBtn = document.getElementById('btn-finish-match');
    if (finishBtn) finishBtn.hidden = !(isOwner && detail.status === 'PROGRESS');
    const editBtn = document.getElementById('btn-edit-match');
    if (editBtn) editBtn.hidden = !(isOwner && (detail.status === 'WAITING' || detail.status === 'MATCHING'));
    const deleteBtn = document.getElementById('btn-delete-match');
    if (deleteBtn) deleteBtn.hidden = !(isOwner && (detail.status === 'WAITING' || detail.status === 'MATCHING'));

    // 후기 작성 (DONE 일 때 양쪽 모두)
    const reviewBtn = document.getElementById('btn-review-match');
    if (reviewBtn) {
      reviewBtn.hidden = detail.status !== 'DONE';
      reviewBtn.addEventListener('click', () => {
        location.href = `match-review.html?match_id=${matchId}`;
      });
    }

    // 신청자 목록 (작성자만)
    const appsSection = document.getElementById('apps-section');
    if (appsSection) appsSection.hidden = !isOwner;

    if (isOwner && (detail.status === 'WAITING' || detail.status === 'MATCHING')) {
      const listEl = document.getElementById('apps-list');
      if (listEl) listEl.innerHTML = Loading.skeletonRows(2);
      try {
        const apps = await API.get(`/api/v1/matches/${matchId}/applications`);
        const tmpl = document.getElementById('tmpl-applicant');
        const countEl = document.getElementById('apps-count');
        if (listEl) listEl.innerHTML = '';
        if (countEl) countEl.textContent = apps.total || apps.items?.length || 0;
        (apps.items || []).forEach((app) => {
          const node = tmpl.content.cloneNode(true);
          const row = node.querySelector('.applicant-row');
          if (row) row.dataset.appStatus = app.status;
          node.querySelector('.app-nickname').textContent = app.applicant?.nickname || '—';
          const statusLabel = { PENDING:'대기 중', ACCEPTED:'수락됨', REJECTED:'거절됨' };
          node.querySelector('.app-status').textContent = statusLabel[app.status] || app.status;
          const msgEl = node.querySelector('.app-message');
          if (msgEl) msgEl.textContent = app.message?.trim() || '메모 없음';
          const acceptBtn = node.querySelector('.btn-accept');
          const rejectBtn = node.querySelector('.btn-reject');
          const chatBtn = node.querySelector('.btn-chat');
          chatBtn?.addEventListener('click', () => {
            location.href = `chat.html?match_id=${matchId}&application_id=${app.application_id}`;
          });
          if (app.status !== 'PENDING') {
            if (acceptBtn) acceptBtn.hidden = true;
            if (rejectBtn) rejectBtn.hidden = true;
          }
          acceptBtn?.addEventListener('click', async () => {
            try {
              await API.patch(`/api/v1/matches/${matchId}/applications/${app.application_id}`, { action: 'ACCEPT' });
              Toast.ok('신청을 수락했습니다.');
              location.href = `chat.html?match_id=${matchId}&application_id=${app.application_id}`;
            } catch (err) { Toast.error(err.message); }
          });
          rejectBtn?.addEventListener('click', async () => {
            try {
              await API.patch(`/api/v1/matches/${matchId}/applications/${app.application_id}`, { action: 'REJECT' });
              Toast.ok('거절했습니다.');
              if (rejectBtn) { rejectBtn.disabled = true; rejectBtn.textContent = '거절됨'; }
            } catch (err) { Toast.error(err.message); }
          });
          listEl.appendChild(node);
        });

        // 비어있을 때 안내
        if ((apps.items || []).length === 0) {
          const empty = document.createElement('div');
          empty.style.cssText = 'padding:20px 0;text-align:center;color:var(--ink-mute);font-size:13px;font-weight:600;';
          empty.textContent = '아직 신청한 봉사자가 없어요';
          listEl.appendChild(empty);
        }
      } catch (err) {
        if (listEl) listEl.innerHTML = '';
        Toast.error(err.message);
      }
    }

    // 신청자(나) 액션
    const applyBtn = document.getElementById('btn-apply');
    const chatBtn = document.getElementById('btn-chat');
    if (applyBtn && !isOwner) {
      let myAppStatus = null;
      let myAppId = null;
      try {
        const myMatches = await API.get('/api/v1/users/me/matches?role=applicant&size=50');
        const found = myMatches.items?.find(m => m.match_id === matchId);
        if (found) myAppStatus = found.my_application_status;
        const savedAppId = localStorage.getItem(`sg_app_${matchId}`);
        if (savedAppId) myAppId = parseInt(savedAppId, 10);
      } catch (e) {}

      if (myAppStatus) {
        applyBtn.hidden = false;
        if (myAppStatus === 'REJECTED') {
          applyBtn.textContent = '거절됨';
          applyBtn.disabled = true;
        } else {
          applyBtn.textContent = myAppStatus === 'ACCEPTED' ? '매칭 수락됨' : '신청 완료';
          applyBtn.disabled = true;
          if (chatBtn) {
            chatBtn.hidden = false;
            chatBtn.addEventListener('click', () => {
              const qs = myAppId ? `?match_id=${matchId}&application_id=${myAppId}` : `?match_id=${matchId}`;
              location.href = `chat.html${qs}`;
            });
          }
        }
      } else if (detail.status === 'WAITING') {
        applyBtn.hidden = false;
        applyBtn.addEventListener('click', async () => {
          const message = prompt('신청 메시지를 입력해 주세요 (선택, 최대 2000자)') || '';
          applyBtn.disabled = true;
          try {
            const res = await API.post(`/api/v1/matches/${matchId}/applications`, { message });
            if (res.application_id) {
              localStorage.setItem(`sg_app_${matchId}`, res.application_id);
            }
            Toast.ok('봉사 신청이 완료되었습니다.');
            applyBtn.textContent = '신청 완료';
            if (chatBtn) {
              chatBtn.hidden = false;
              chatBtn.addEventListener('click', () => {
                location.href = `chat.html?match_id=${matchId}&application_id=${res.application_id}`;
              });
            }
          } catch (err) {
            Toast.error(err.message);
            applyBtn.disabled = false;
          }
        });
      } else {
        applyBtn.hidden = true;
      }
    } else if (applyBtn) {
      applyBtn.hidden = true;
    }

    // 신고/차단 (작성자 아닌 사람만)
    const reportBtn = document.getElementById('btn-report-match');
    if (reportBtn) {
      reportBtn.hidden = isOwner;
      reportBtn.addEventListener('click', () => {
        location.href = `reports.html?type=user&target_user_id=${detail.author?.user_id}`;
      });
    }
  };

  // ─── Page boot: 내 요청 목록 ──────────────────────────────────────────────
  PreviewApp.bootMyMatches = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const STATUS_LABEL = { WAITING:'모집중', MATCHING:'검토중', PROGRESS:'진행중', DONE:'완료' };
    const tabs = document.querySelectorAll('.status-tab');
    let currentStatus = '';
    const roleParam = new URLSearchParams(location.search).get('role') || 'author';

    async function load(status) {
      const qs = status ? `&status=${status}` : '';
      const listEl = document.getElementById('my-match-list');
      const empty = document.getElementById('my-match-empty');
      if (listEl) listEl.innerHTML = Loading.skeletonCards(3);
      if (empty) empty.hidden = true;
      try {
        const data = await API.get(`/api/v1/users/me/matches?role=${roleParam}${qs}`);
        const tmpl = document.getElementById('tmpl-my-match');
        if (listEl) listEl.innerHTML = '';
        const items = data.items || [];
        if (empty) empty.hidden = items.length > 0;
        items.forEach((item) => {
          const node = tmpl.content.cloneNode(true);
          const a = node.querySelector('a');
          if (a) {
            a.href = `match-detail.html?id=${item.match_id}`;
            a.dataset.s = item.status;
          }
          const badge = node.querySelector('.mc-badge');
          if (badge) {
            badge.textContent = STATUS_LABEL[item.status] || item.status;
            badge.dataset.s = item.status;
          }
          const titleEl = node.querySelector('.mc-title');
          if (titleEl) titleEl.textContent = item.title;
          const dateEl = node.querySelector('[data-field="desired_date"]');
          if (dateEl) {
            const datePart = item.desired_date ? Util.formatDateKo(item.desired_date) : '날짜 미정';
            const timePart = item.desired_time ? ` · ${Util.formatTimeKo(item.desired_time)}` : '';
            dateEl.textContent = datePart + timePart;
          }
          const addrEl = node.querySelector('[data-field="address"]');
          if (addrEl) addrEl.textContent = item.address || '주소 미입력';
          const ddayEl = node.querySelector('.mc-dday');
          if (ddayEl) ddayEl.textContent = Util.dday(item.desired_date) || '';
          listEl.appendChild(node);
        });
      } catch (err) {
        if (listEl) listEl.innerHTML = '';
        Toast.error(err.message);
      }
    }

    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentStatus = tab.dataset.status || '';
        load(currentStatus);
      });
    });

    await load(currentStatus);
  };

  // ─── Page boot: 매장 상세 ─────────────────────────────────────────────────
  PreviewApp.bootStoreDetail = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const params = new URLSearchParams(location.search);
    const storeId = parseInt(params.get('id'), 10);
    if (!storeId) { Toast.error('잘못된 접근입니다.'); return; }

    // 상세 본문 + 리뷰 영역 스켈레톤
    document.querySelectorAll('[data-bind]').forEach((el) => {
      if (!el.textContent.trim() || el.textContent.trim() === '—') {
        el.innerHTML = '<span class="sk-box sk-line sm sk-w-50" style="display:inline-block;min-width:60px"></span>';
      }
    });
    const reviewListEl = document.getElementById('review-list');
    if (reviewListEl) reviewListEl.innerHTML = Loading.skeletonRows(2);
    const reviewEmpty = document.getElementById('review-empty');
    if (reviewEmpty) reviewEmpty.hidden = true;

    try {
      const [detail, reviews] = await Promise.all([
        API.get(`/api/v1/maps/stores/${storeId}`),
        API.get(`/api/v1/maps/stores/${storeId}/reviews`),
      ]);
      if (reviewListEl) reviewListEl.innerHTML = '';
      const reviewItems = reviews.reviews || reviews.items || [];
      Bind.apply(document, {
        ...detail,
        avg_rating: detail.rating_avg != null ? detail.rating_avg.toFixed(1) : '—',
        review_count: reviewItems.length,
        category_label: ({CAFE:'카페',PARK:'공원',VET:'병원',RESTAURANT:'식당',GROOMING:'미용'}[detail.category] || detail.category || ''),
      });

      const favBtn = document.getElementById('btn-favorite');
      if (favBtn) {
        favBtn.dataset.favorited = detail.is_favorited ? '1' : '0';
        favBtn.querySelector('i').className = detail.is_favorited ? 'ph-fill ph-heart' : 'ph ph-heart';
        favBtn.addEventListener('click', async () => {
          const on = favBtn.dataset.favorited === '1';
          try {
            if (on) {
              // 즐겨찾기 해제 — 올바른 경로: /users/me/favorites/stores/{id}
              await API.delete(`/api/v1/users/me/favorites/stores/${storeId}`);
            } else {
              await API.post('/api/v1/users/me/favorites/stores', { store_id: storeId });
            }
            favBtn.dataset.favorited = on ? '0' : '1';
            favBtn.querySelector('i').className = on ? 'ph ph-heart' : 'ph-fill ph-heart';
            Toast.ok(on ? '즐겨찾기에서 제거했어요' : '즐겨찾기에 추가했어요');
          } catch (err) { Toast.error(err.message); }
        });
      }

      const reviewList = document.getElementById('review-list');
      const tmpl = document.getElementById('tmpl-review');
      if (reviewList && tmpl) {
        reviewItems.forEach((r) => {
          const node = tmpl.content.cloneNode(true);
          node.querySelector('.rv-nick').textContent = r.nickname || '익명';
          node.querySelector('.rv-rating').textContent = '★'.repeat(Math.max(0, Math.min(5, r.rating)));
          node.querySelector('.rv-body').textContent = r.content;
          const dateEl = node.querySelector('.rv-date');
          if (dateEl && r.created_at) {
            const d = new Date(r.created_at);
            dateEl.textContent = `${d.getMonth()+1}.${d.getDate()}`;
          }
          reviewList.appendChild(node);
        });
        const empty = document.getElementById('review-empty');
        if (empty) empty.hidden = reviewItems.length > 0;
      }
    } catch (err) { Toast.error(err.message); }

    const mapEl = document.getElementById('store-mini-map');
    if (mapEl) mapEl.innerHTML = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#B8D9D9,#D4E8C4);font-size:12px;color:rgba(30,18,10,0.45);font-weight:700;">📍 지도 (카카오 SDK 연동 예정)</div>';

    document.getElementById('review-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const rating = parseInt(document.getElementById('rv-stars').value, 10);
      const content = document.getElementById('rv-content').value.trim();
      const petAllowed = document.getElementById('rv-pet-allowed')?.checked ?? true;
      if (!content || !rating) { Toast.error('별점과 리뷰 내용을 입력해 주세요.'); return; }
      const btn = e.submitter || e.target.querySelector('[type=submit]');
      const restoreBtn = Loading.bindButton(btn, '등록 중...');
      try {
        await API.post(`/api/v1/maps/stores/${storeId}/reviews`, {
          rating, content, is_pet_allowed: petAllowed,
        });
        Toast.ok('리뷰가 등록되었습니다.');
        setTimeout(() => location.reload(), 800);
      } catch (err) { Toast.error(err.message); restoreBtn(); }
    });
  };

  // ─── Page boot: 뉴스 상세 ─────────────────────────────────────────────────
  PreviewApp.bootNewsDetail = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const params = new URLSearchParams(location.search);
    const newsId = params.get('id');
    if (!newsId) { Toast.error('잘못된 접근입니다.'); return; }

    const CAT_LABEL = { POLICY:'정책', EVENT:'행사', VOLUNTEER:'봉사', SUPPORT:'지원', BADGE:'인증' };

    // 본문 영역 스켈레톤
    const bodyEl = document.getElementById('news-body');
    if (bodyEl) {
      bodyEl.innerHTML = `
        <p><span class="sk-box sk-line sm sk-w-100" style="display:block;height:12px;margin-bottom:8px"></span>
        <span class="sk-box sk-line sm sk-w-90" style="display:block;height:12px;margin-bottom:8px"></span>
        <span class="sk-box sk-line sm sk-w-80" style="display:block;height:12px"></span></p>
        <p><span class="sk-box sk-line sm sk-w-100" style="display:block;height:12px;margin-bottom:8px"></span>
        <span class="sk-box sk-line sm sk-w-70" style="display:block;height:12px"></span></p>`;
    }
    document.querySelectorAll('[data-bind="title"], [data-bind="category_label"], [data-bind="published_date_ko"]').forEach((el) => {
      el.innerHTML = '<span class="sk-box sk-line sm sk-w-60" style="display:inline-block;min-width:80px"></span>';
    });

    try {
      const data = await API.get(`/api/v1/news/${newsId}`);
      document.title = `시흥가개 — ${data.title}`;
      // 날짜 한글화
      const dateKo = data.published_date ? `${data.published_date.slice(5,7)}월 ${data.published_date.slice(8,10)}일` : '';
      Bind.apply(document, {
        ...data,
        category_label: CAT_LABEL[data.category] || data.category,
        published_date_ko: dateKo,
      });

      const img = document.getElementById('news-hero-img');
      if (img) {
        if (data.image_url) { img.src = data.image_url; img.hidden = false; }
        else img.hidden = true;
      }

      const bodyEl = document.getElementById('news-body');
      if (bodyEl && data.content) {
        bodyEl.innerHTML = data.content
          .split(/\n\n+/)
          .map(p => `<p>${escapeHtml(p).replace(/\n/g, '<br>')}</p>`)
          .join('');
      }

      const linkBtn = document.getElementById('btn-official-link');
      if (linkBtn && data.official_link) {
        linkBtn.href = data.official_link;
        linkBtn.hidden = false;
      }
    } catch (err) { Toast.error(err.message); }
  };

  // ─── Page boot: 프로필 편집 ───────────────────────────────────────────────
  PreviewApp.bootProfileEdit = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    // 폼 위에 인라인 로딩 표시
    const formEl = document.getElementById('profile-edit-form');
    const loadingNode = document.createElement('div');
    loadingNode.className = 'sg-loading';
    loadingNode.innerHTML = '<span class="sg-spinner" aria-hidden="true"></span><span>프로필을 불러오는 중...</span>';
    if (formEl) formEl.prepend(loadingNode);
    ['nickname','phone','region-si','region-dong','profile-image-url'].forEach((id) => {
      const el = document.getElementById(`edit-${id}`);
      if (el) el.disabled = true;
    });

    let me;
    try {
      me = await API.get('/api/v1/users/me');
      const fields = ['nickname', 'phone', 'region_si', 'region_dong', 'profile_image_url'];
      fields.forEach(f => {
        const el = document.getElementById(`edit-${f.replace('_','-')}`);
        if (el) { el.value = me[f] || ''; el.disabled = false; }
      });
      loadingNode.remove();
    } catch (err) {
      loadingNode.remove();
      Toast.error(err.message);
      return;
    }

    // GPS 버튼 — 위치 자동 채우기
    document.getElementById('btn-region-gps')?.addEventListener('click', async () => {
      if (!navigator.geolocation) { Toast.error('GPS를 사용할 수 없어요'); return; }
      try {
        const pos = await new Promise((res, rej) =>
          navigator.geolocation.getCurrentPosition(res, rej, { timeout: 6000 })
        );
        const geo = await API.get(`/api/v1/geo/reverse?lat=${pos.coords.latitude}&lng=${pos.coords.longitude}`);
        const siEl = document.getElementById('edit-region-si');
        const dongEl = document.getElementById('edit-region-dong');
        if (siEl) siEl.value = geo.si || '';
        if (dongEl) dongEl.value = geo.dong || '';
        Toast.ok(`현재 위치: ${geo.label}`);
      } catch (err) { Toast.error('위치 조회 실패'); }
    });

    document.getElementById('profile-edit-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const body = {};
      ['nickname','phone','region_si','region_dong','profile_image_url'].forEach(k => {
        const el = document.getElementById(`edit-${k.replace('_','-')}`);
        if (!el) return;
        const v = el.value.trim();
        if (v !== (me[k] || '')) body[k] = v || null;
      });
      if (Object.keys(body).length === 0) { Toast.info('변경 사항이 없어요'); return; }
      const btn = e.submitter || e.target.querySelector('[type=submit]');
      const restoreBtn = Loading.bindButton(btn, '저장 중...');
      try {
        await API.patch('/api/v1/users/me', body);
        Toast.ok('프로필이 저장되었습니다.');
        setTimeout(() => { location.href = 'my.html'; }, 800);
      } catch (err) {
        Toast.error(err.message);
        restoreBtn();
      }
    });
  };

  // ─── Page boot: 반려동물 추가/수정 (풍부판) ────────────────────────────────
  PreviewApp.bootPetForm = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const params = new URLSearchParams(location.search);
    const petId = parseInt(params.get('pet_id'), 10) || null;
    const isEdit = !!petId;

    const state = {
      species: 'DOG',
      gender: 'UNKNOWN',
      age: 1,
      ageUnit: 'years', // 'years' | 'months'
      isNeutered: false,
    };

    function updatePreview() {
      const previewName = document.getElementById('preview-name');
      const previewMeta = document.getElementById('preview-meta');
      const previewIcon = document.getElementById('preview-icon');
      const nameInput = document.getElementById('pet-name');
      if (previewName) previewName.textContent = nameInput?.value.trim() || '이름을 입력하세요';
      if (previewMeta) {
        const speciesLabel = Util.petSpeciesLabel(state.species);
        const ageLabel = state.ageUnit === 'years' ? `${state.age}살` : `${state.age}개월`;
        const genderLabel = { MALE:'수컷', FEMALE:'암컷', UNKNOWN:'' }[state.gender];
        previewMeta.textContent = [speciesLabel, ageLabel, genderLabel].filter(Boolean).join(' · ');
      }
      if (previewIcon) {
        const ic = state.species === 'CAT' ? 'cat' : (state.species === 'OTHER' ? 'paw-print' : 'dog');
        previewIcon.className = `ph ph-${ic}`;
        const wrap = previewIcon.closest('.preview-icon-wrap');
        if (wrap) {
          wrap.classList.remove('cat','dog','other');
          wrap.classList.add(state.species === 'CAT' ? 'cat' : (state.species === 'OTHER' ? 'other' : 'dog'));
        }
      }
    }

    // 종류 chip
    document.querySelectorAll('[data-species]').forEach(chip => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('[data-species]').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        state.species = chip.dataset.species;
        updatePreview();
      });
    });
    // 성별 chip
    document.querySelectorAll('[data-gender]').forEach(chip => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('[data-gender]').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        state.gender = chip.dataset.gender;
        updatePreview();
      });
    });
    // 나이 stepper
    document.getElementById('age-minus')?.addEventListener('click', () => {
      state.age = Math.max(0, state.age - 1);
      document.getElementById('age-value').textContent = state.age;
      updatePreview();
    });
    document.getElementById('age-plus')?.addEventListener('click', () => {
      state.age = Math.min(50, state.age + 1);
      document.getElementById('age-value').textContent = state.age;
      updatePreview();
    });
    document.querySelectorAll('[data-age-unit]').forEach(chip => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('[data-age-unit]').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        state.ageUnit = chip.dataset.ageUnit;
        updatePreview();
      });
    });
    // 중성화 토글
    document.getElementById('pet-neutered')?.addEventListener('change', (e) => {
      state.isNeutered = e.target.checked;
    });
    // 이름·메모 입력 변경 시 미리보기
    document.getElementById('pet-name')?.addEventListener('input', updatePreview);
    document.getElementById('pet-memo')?.addEventListener('input', (e) => {
      const cnt = document.getElementById('memo-count');
      if (cnt) cnt.textContent = `${e.target.value.length} / 300`;
    });

    if (isEdit) {
      const titleEl = document.getElementById('form-title');
      if (titleEl) titleEl.textContent = '반려동물 수정';
      const deleteBtn = document.getElementById('btn-delete');
      if (deleteBtn) deleteBtn.hidden = false;
      try {
        const me = await API.get('/api/v1/users/me');
        const pet = (me.pets || []).find(p => p.id === petId);
        if (pet) {
          document.getElementById('pet-name').value = pet.name || '';
          document.getElementById('pet-breed').value = pet.breed || '';
          document.getElementById('pet-weight').value = pet.weight_kg ?? '';
          document.getElementById('pet-memo').value = pet.memo || '';
          document.getElementById('pet-neutered').checked = !!pet.is_neutered;
          state.species = pet.species || 'DOG';
          state.gender = pet.gender || 'UNKNOWN';
          state.age = pet.age ?? 1;
          state.isNeutered = !!pet.is_neutered;
          document.getElementById('age-value').textContent = state.age;
          document.querySelectorAll('[data-species]').forEach(c => c.classList.toggle('active', c.dataset.species === state.species));
          document.querySelectorAll('[data-gender]').forEach(c => c.classList.toggle('active', c.dataset.gender === state.gender));
          updatePreview();
        }
      } catch (err) { Toast.error(err.message); }
    } else {
      updatePreview();
    }

    document.getElementById('pet-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('pet-name').value.trim();
      if (!name) { Toast.error('이름을 입력해 주세요.'); return; }
      const breed = document.getElementById('pet-breed').value.trim() || null;
      const weightStr = document.getElementById('pet-weight').value.trim();
      const weight_kg = weightStr ? parseFloat(weightStr) : null;
      // age는 백엔드가 정수로 받음 — 개월 단위면 소수점 0.1 단위로 환산해야 하나, 스펙상 integer라 그대로 전송
      const body = {
        name,
        species: state.species,
        breed,
        age: state.age,
        weight_kg,
        gender: state.gender,
        is_neutered: state.isNeutered,
      };
      const btn = e.submitter || e.target.querySelector('[type=submit]');
      const restoreBtn = Loading.bindButton(btn, isEdit ? '수정 중...' : '저장 중...');
      try {
        if (isEdit) {
          await API.patch(`/api/v1/users/me/pets/${petId}`, body);
        } else {
          await API.post('/api/v1/users/me/pets', body);
        }
        Toast.ok(isEdit ? '수정되었습니다.' : '반려동물이 추가되었습니다.');
        setTimeout(() => { location.href = 'my.html'; }, 700);
      } catch (err) { Toast.error(err.message); restoreBtn(); }
    });

    document.getElementById('btn-delete')?.addEventListener('click', async () => {
      if (!confirm('반려동물을 삭제할까요?')) return;
      const overlay = Loading.overlay('삭제 중...');
      try {
        await API.delete(`/api/v1/users/me/pets/${petId}`);
        Toast.ok('삭제되었습니다.');
        setTimeout(() => { location.href = 'my.html'; }, 600);
      } catch (err) {
        overlay.close();
        Toast.error(err.message);
      }
    });
  };

  // ─── Page boot: 즐겨찾기 매장 목록 ────────────────────────────────────────
  PreviewApp.bootFavorites = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    const listEl = document.getElementById('fav-list');
    const tmpl = document.getElementById('tmpl-fav');
    const empty = document.getElementById('fav-empty');
    if (listEl) listEl.innerHTML = Loading.skeletonRows(3);
    if (empty) empty.hidden = true;
    try {
      const data = await API.get('/api/v1/users/me/favorites/stores');
      const items = data.items || [];
      if (listEl) listEl.innerHTML = '';
      if (empty) empty.hidden = items.length > 0;
      items.forEach(it => {
        const node = tmpl.content.cloneNode(true);
        const a = node.querySelector('a');
        if (a) a.href = `store-detail.html?id=${it.store_id}`;
        node.querySelector('.fav-name').textContent = it.name;
        node.querySelector('.fav-cat').textContent = ({CAFE:'카페',PARK:'공원',VET:'병원',RESTAURANT:'식당',GROOMING:'미용'}[it.category] || it.category || '');
        const ratingEl = node.querySelector('.fav-rating');
        if (ratingEl) ratingEl.textContent = it.rating_avg != null ? it.rating_avg.toFixed(1) : '—';
        const imgEl = node.querySelector('.fav-thumb');
        if (imgEl) {
          if (it.thumbnail_url) imgEl.src = it.thumbnail_url;
          else imgEl.style.background = 'linear-gradient(135deg,var(--sand-soft),var(--accent-soft))';
        }
        const removeBtn = node.querySelector('.fav-remove');
        if (removeBtn) removeBtn.addEventListener('click', async (e) => {
          e.preventDefault();
          if (!confirm('즐겨찾기에서 제거할까요?')) return;
          try {
            await API.delete(`/api/v1/users/me/favorites/stores/${it.store_id}`);
            Toast.ok('제거되었습니다.');
            setTimeout(() => location.reload(), 400);
          } catch (err) { Toast.error(err.message); }
        });
        listEl.appendChild(node);
      });
    } catch (err) {
      if (listEl) listEl.innerHTML = '';
      Toast.error(err.message);
    }
  };

  // ─── Page boot: 설정 ─────────────────────────────────────────────────────
  PreviewApp.bootSettings = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    try {
      const me = await API.get('/api/v1/users/me');
      document.querySelectorAll('[data-fill="region-dong"]').forEach(el => el.textContent = me.region_dong || '미설정');
      // 알림 설정 토글 (있으면)
      try {
        const ns = await API.get('/api/v1/users/me/notification-settings');
        Object.entries(ns.settings || {}).forEach(([cat, on]) => {
          const cb = document.querySelector(`[data-notif-cat="${cat}"]`);
          if (cb) cb.checked = !!on;
        });
        document.querySelectorAll('[data-notif-cat]').forEach(cb => {
          cb.addEventListener('change', async () => {
            const cat = cb.dataset.notifCat;
            try {
              await API.put('/api/v1/users/me/notification-settings', { settings: { [cat]: cb.checked } });
              Toast.ok('저장되었습니다');
            } catch (err) { Toast.error(err.message); cb.checked = !cb.checked; }
          });
        });
      } catch {}
    } catch (err) { Toast.error(err.message); }

    document.getElementById('btn-logout')?.addEventListener('click', () => {
      if (confirm('로그아웃 하시겠습니까?')) Auth.logout();
    });
  };

  // ─── Page boot: 봉사자 자격 신청 ──────────────────────────────────────────
  PreviewApp.bootVolunteerRequest = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    const form = document.getElementById('vol-request-form');
    if (!form) return;
    const msgEl = document.getElementById('vol-message');
    const cntEl = document.getElementById('vol-message-count');
    msgEl?.addEventListener('input', () => {
      if (cntEl) cntEl.textContent = `${msgEl.value.length} / 500`;
    });
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('vol-title')?.value.trim();
      const message = msgEl.value.trim();
      if (!message) { Toast.error('신청서를 입력해 주세요.'); return; }
      const fullMessage = title ? `[${title}] ${message}` : message;
      const btn = e.submitter || e.target.querySelector('[type=submit]');
      const restoreBtn = Loading.bindButton(btn, '신청 중...');
      try {
        await API.post('/api/v1/users/me/volunteer-request', { message: fullMessage });
        Toast.ok('신청이 접수되었습니다. 관리자 승인을 기다려 주세요.');
        setTimeout(() => location.href = 'my.html', 1200);
      } catch (err) { Toast.error(err.message); restoreBtn(); }
    });
  };

  // ─── Page boot: 매칭 후기 작성 ────────────────────────────────────────────
  PreviewApp.bootMatchReview = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    const params = new URLSearchParams(location.search);
    const matchId = parseInt(params.get('match_id'), 10);
    if (!matchId) { Toast.error('잘못된 접근입니다.'); return; }

    let selectedRating = 0;
    const stars = document.querySelectorAll('.review-star');
    function paintStars(n) {
      stars.forEach((s, i) => {
        s.classList.toggle('active', i < n);
        const ic = s.querySelector('i');
        if (ic) ic.className = i < n ? 'ph-fill ph-star' : 'ph ph-star';
      });
      const lbl = document.getElementById('rating-label');
      if (lbl) lbl.textContent = ['선택해 주세요','매우 별로','별로','보통','좋아요','아주 좋아요'][n] || '';
    }
    stars.forEach((s, i) => {
      s.addEventListener('click', () => {
        selectedRating = i + 1;
        paintStars(selectedRating);
      });
    });
    paintStars(0);

    const contentEl = document.getElementById('review-content');
    contentEl?.addEventListener('input', () => {
      const cnt = document.getElementById('review-content-count');
      if (cnt) cnt.textContent = `${contentEl.value.length} / 2000`;
    });

    document.getElementById('match-review-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (selectedRating === 0) { Toast.error('별점을 선택해 주세요'); return; }
      const content = contentEl.value.trim();
      if (!content) { Toast.error('후기 내용을 입력해 주세요'); return; }
      const btn = e.submitter || e.target.querySelector('[type=submit]');
      const restoreBtn = Loading.bindButton(btn, '등록 중...');
      try {
        await API.post(`/api/v1/matches/${matchId}/review`, {
          rating: selectedRating,
          content,
          proof_image_urls: [],
        });
        Toast.ok('후기가 등록되었습니다.');
        setTimeout(() => location.href = `match-detail.html?id=${matchId}`, 800);
      } catch (err) { Toast.error(err.message); restoreBtn(); }
    });
  };

  // ─── Page boot: 캘린더 ───────────────────────────────────────────────────
  PreviewApp.bootCalendar = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    let year = new Date().getFullYear(), month = new Date().getMonth() + 1;

    async function render() {
      const grid = document.getElementById('cal-grid');
      if (grid) {
        grid.innerHTML = '';
        // 6주 × 7일 = 42칸의 스켈레톤 셀로 채워 깜빡임 방지
        for (let i = 0; i < 42; i++) {
          grid.insertAdjacentHTML('beforeend', '<div class="cal-cell"><span class="sk-box" style="width:18px;height:14px;border-radius:6px;display:inline-block"></span></div>');
        }
      }
      try {
        const data = await API.get(`/api/v1/news/calendar?year=${year}&month=${month}`);
        const lblEl = document.getElementById('cal-month-label');
        if (lblEl) lblEl.textContent = `${year}년 ${month}월`;
        if (!grid) return;
        grid.innerHTML = '';
        const firstDay = new Date(year, month-1, 1).getDay();
        const lastDate = new Date(year, month, 0).getDate();
        const eventMap = new Map();
        (data.events || []).forEach(ev => {
          const start = new Date(ev.start_date + 'T00:00:00');
          const end = new Date(ev.end_date + 'T00:00:00');
          for (let d = new Date(start); d <= end; d.setDate(d.getDate()+1)) {
            if (d.getMonth()+1 !== month) continue;
            const key = d.getDate();
            if (!eventMap.has(key)) eventMap.set(key, []);
            eventMap.get(key).push(ev);
          }
        });
        for (let i = 0; i < firstDay; i++) grid.insertAdjacentHTML('beforeend', '<span class="cal-cell empty"></span>');
        for (let d = 1; d <= lastDate; d++) {
          const cell = document.createElement('div');
          cell.className = 'cal-cell';
          cell.innerHTML = `<span class="cal-day">${d}</span>`;
          if (eventMap.has(d)) {
            cell.classList.add('has-event');
            cell.innerHTML += '<span class="cal-event-dot"></span>';
            cell.addEventListener('click', () => {
              const evs = eventMap.get(d);
              alert(evs.map(e => `• ${e.title}`).join('\n'));
            });
          }
          grid.appendChild(cell);
        }
      } catch (err) {
        if (grid) grid.innerHTML = '';
        Toast.error(`캘린더 로딩 실패: ${err.message}`);
      }
    }
    document.getElementById('cal-prev')?.addEventListener('click', () => {
      month--; if (month < 1) { month = 12; year--; } render();
    });
    document.getElementById('cal-next')?.addEventListener('click', () => {
      month++; if (month > 12) { month = 1; year++; } render();
    });
    render();
  };

  // ─── Page boot: 신고 ─────────────────────────────────────────────────────
  PreviewApp.bootReports = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    const params = new URLSearchParams(location.search);
    const type = params.get('type') || 'user';
    const targetUserId = parseInt(params.get('target_user_id'), 10) || null;
    const matchId = parseInt(params.get('match_id'), 10) || null;
    const appId = parseInt(params.get('application_id'), 10) || null;

    const titleEl = document.querySelector('.page-title');
    if (titleEl) titleEl.textContent = type === 'chat' ? '채팅 신고' : '사용자 신고';

    const form = document.getElementById('report-form');
    const reasonEl = document.getElementById('report-reason');
    reasonEl?.addEventListener('input', () => {
      const c = document.getElementById('reason-count');
      if (c) c.textContent = `${reasonEl.value.length} / 2000`;
    });

    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const reason = reasonEl.value.trim();
      if (!reason) { Toast.error('신고 사유를 입력해 주세요'); return; }
      const btn = e.submitter || form.querySelector('[type=submit]');
      const restoreBtn = Loading.bindButton(btn, '제출 중...');
      try {
        if (type === 'chat') {
          const messageIdStr = document.getElementById('report-message-id')?.value.trim();
          const messageId = parseInt(messageIdStr, 10);
          if (!messageId) { Toast.error('메시지 ID가 필요합니다'); restoreBtn(); return; }
          // chat_id 는 chat_rooms.id. application_id 기반으로 조회 어렵기 때문에 매칭 상세에서 넘기는 편이 정공법.
          await API.post('/api/v1/reports/chat', {
            chat_id: appId, // 임시 — 안드로이드에서는 chat_id를 별도 query 로 받게 보강
            target_user_id: targetUserId,
            message_id: messageId,
            reason,
          });
        } else {
          await API.post('/api/v1/reports', { target_user_id: targetUserId, reason });
        }
        Toast.ok('신고가 접수되었습니다.');
        setTimeout(() => history.back(), 800);
      } catch (err) { Toast.error(err.message); restoreBtn(); }
    });

    // 차단 버튼 (옵션)
    document.getElementById('btn-block-user')?.addEventListener('click', async () => {
      if (!targetUserId) return;
      if (!confirm('이 사용자를 차단할까요? 차단 시 상호 글이 더이상 보이지 않아요.')) return;
      try {
        await API.post('/api/v1/users/me/blocks', { target_user_id: targetUserId });
        Toast.ok('차단되었습니다.');
        setTimeout(() => location.href = 'blocks.html', 600);
      } catch (err) { Toast.error(err.message); }
    });
  };

  // ─── Page boot: 차단 관리 ────────────────────────────────────────────────
  PreviewApp.bootBlocks = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    const listEl = document.getElementById('block-list');
    const tmpl = document.getElementById('tmpl-block');
    try {
      const data = await API.get('/api/v1/users/me/blocks');
      const items = data.items || [];
      const empty = document.getElementById('block-empty');
      if (empty) empty.hidden = items.length > 0;
      items.forEach(b => {
        const node = tmpl.content.cloneNode(true);
        node.querySelector('.block-nick').textContent = b.target_nickname || '(탈퇴한 사용자)';
        const dateEl = node.querySelector('.block-date');
        if (dateEl && b.created_at) dateEl.textContent = b.created_at.slice(0,10);
        node.querySelector('.btn-unblock').addEventListener('click', async () => {
          if (!confirm('차단을 해제할까요?')) return;
          try {
            await API.delete(`/api/v1/users/me/blocks/${b.block_id}`);
            Toast.ok('차단 해제되었습니다.');
            setTimeout(() => location.reload(), 400);
          } catch (err) { Toast.error(err.message); }
        });
        listEl.appendChild(node);
      });
    } catch (err) { Toast.error(err.message); }
  };

  // ─── Page boot: 비밀번호 변경 ────────────────────────────────────────────
  PreviewApp.bootPasswordChange = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    document.getElementById('password-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const current = document.getElementById('pw-current').value;
      const newPw = document.getElementById('pw-new').value;
      const confirmPw = document.getElementById('pw-confirm').value;
      if (newPw !== confirmPw) { Toast.error('새 비밀번호가 일치하지 않습니다'); return; }
      const btn = e.submitter || e.target.querySelector('[type=submit]');
      const restoreBtn = Loading.bindButton(btn, '변경 중...');
      try {
        await API.put('/api/v1/users/me/password', {
          current_password: current, new_password: newPw,
        });
        Toast.ok('비밀번호가 변경되었습니다. 다시 로그인해 주세요.');
        setTimeout(() => Auth.logout(), 1200);
      } catch (err) { Toast.error(err.message); restoreBtn(); }
    });
  };

  // ─── Page boot: 계정 탈퇴 ────────────────────────────────────────────────
  PreviewApp.bootAccountDelete = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    document.getElementById('delete-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const password = document.getElementById('delete-password').value;
      const reason = document.getElementById('delete-reason').value.trim();
      if (!confirm('정말 탈퇴하시겠습니까? 30일 후 영구 삭제됩니다.')) return;
      const btn = e.submitter || e.target.querySelector('[type=submit]');
      const restoreBtn = Loading.bindButton(btn, '처리 중...');
      try {
        await API.delete('/api/v1/users/me', { password, reason });
        // delete는 body 미지원 — 그래서 fetch로 직접 호출
      } catch (err) {
        // call() 에서 DELETE에 body 전달이 안 됨 → 별도 처리
        try {
          const res = await fetch('/api/v1/users/me', {
            method: 'DELETE',
            headers: { 'Content-Type':'application/json', ...Auth.headers() },
            body: JSON.stringify({ password, reason }),
          });
          if (!res.ok) {
            const e2 = await res.json().catch(() => ({}));
            throw new Error(e2.detail || res.statusText);
          }
        } catch (err2) {
          Toast.error(err2.message); restoreBtn(); return;
        }
      }
      Toast.ok('탈퇴되었습니다.');
      setTimeout(() => Auth.logout(), 1000);
    });
  };

  // ─── Page boot: 매장 등록 ────────────────────────────────────────────────
  PreviewApp.bootStoreAdd = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();
    let lat = 37.3451, lng = 126.7322;

    document.getElementById('btn-gps')?.addEventListener('click', async () => {
      if (!navigator.geolocation) { Toast.error('GPS 미지원'); return; }
      try {
        const pos = await new Promise((res, rej) =>
          navigator.geolocation.getCurrentPosition(res, rej, { timeout: 6000 })
        );
        lat = pos.coords.latitude; lng = pos.coords.longitude;
        const geo = await API.get(`/api/v1/geo/reverse?lat=${lat}&lng=${lng}`);
        const addrEl = document.getElementById('store-address');
        if (addrEl && !addrEl.value) addrEl.value = geo.formatted_address || '';
        Toast.ok(`현재 위치: ${geo.label}`);
      } catch (err) { Toast.error('GPS 실패'); }
    });

    document.getElementById('store-add-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const body = {
        name: document.getElementById('store-name').value.trim(),
        address: document.getElementById('store-address').value.trim(),
        category: document.getElementById('store-category').value,
        is_pet_allowed: document.getElementById('store-pet-allowed').checked,
        phone: document.getElementById('store-phone').value.trim() || null,
        operating_hours: document.getElementById('store-hours').value.trim() || null,
        latitude: lat,
        longitude: lng,
        photo_urls: [],
      };
      if (!body.name || !body.address) { Toast.error('이름과 주소는 필수입니다'); return; }
      const btn = e.submitter || e.target.querySelector('[type=submit]');
      const restoreBtn = Loading.bindButton(btn, '등록 중...');
      try {
        await API.post('/api/v1/maps/stores', body);
        Toast.ok('등록 요청이 접수되었습니다. 관리자 검토 후 지도에 노출됩니다.');
        setTimeout(() => location.href = 'map.html', 1000);
      } catch (err) { Toast.error(err.message); restoreBtn(); }
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
  window.Util = Util;
  window.Loading = Loading;
})();
