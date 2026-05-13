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
    // sessionStorage 우선(탭별 독립), 없으면 localStorage(콘솔과 공유)
    getAccess: () =>
      sessionStorage.getItem(K_ACCESS) || localStorage.getItem(K_ACCESS) || "",
    getRefresh: () =>
      sessionStorage.getItem(K_REFRESH) || localStorage.getItem(K_REFRESH) || "",
    headers() {
      const tok = this.getAccess();
      return tok ? { Authorization: `Bearer ${tok}` } : {};
    },
    // preview 내부에서 새로 로그인하면 sessionStorage 에만 저장 (콘솔 영향 X)
    set(access, refresh) {
      if (access !== undefined) sessionStorage.setItem(K_ACCESS, access);
      if (refresh !== undefined) sessionStorage.setItem(K_REFRESH, refresh);
    },
    // preview 의 clear 는 탭 범위만 (콘솔의 localStorage 는 건드리지 않음)
    clear() {
      sessionStorage.removeItem(K_ACCESS);
      sessionStorage.removeItem(K_REFRESH);
    },
    async login(phone, password) {
      const data = await API.post('/api/v1/auth/login', { phone, password });
      this.set(data.access_token, data.refresh_token);
      return data;
    },
    async signup(phone, password, nickname) {
      const data = await API.post('/api/v1/auth/signup', { phone, password, nickname });
      this.set(data.access_token, data.refresh_token);
      return data;
    },
    logout() {
      API.post('/api/v1/auth/logout', {}).catch(() => {});
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
      const [dash, newsData] = await Promise.all([
        API.get('/api/v1/home/dashboard'),
        API.get('/api/v1/news'),
      ]);

      // dashboard 바인딩
      Bind.apply(document, dash);

      // 알림 dot 표시
      const dot = document.querySelector('.tb-bell .dot');
      if (dot) dot.hidden = !dash.unread_notification_count;

      // 매칭 pill: as_author 또는 as_applicant 중 존재하는 것 사용
      const matchSrc = dash.my_match_summary?.as_author || dash.my_match_summary?.as_applicant;
      const pill = document.querySelector('.match-pill');
      if (pill) {
        if (matchSrc) {
          pill.hidden = false;
          pill.href = `match-detail.html?id=${matchSrc.match_id}`;
          const pillText = pill.querySelector('.match-pill-text');
          if (pillText) pillText.textContent = matchSrc.title;
        } else {
          pill.hidden = true;
        }
      }

      // 홈 뉴스 프리뷰: 피처드 + 최대 3개 목록
      const CAT_LABEL = { POLICY:'정책', EVENT:'행사', VOLUNTEER:'봉사', SUPPORT:'지원' };
      const news = newsData.news || [];
      const featEl = document.querySelector('.news-feat');
      if (featEl && news[0]) {
        const n = news[0];
        featEl.href = `news-detail.html?id=${n.news_id}`;
        const img = featEl.querySelector('.nf-img');
        if (img) { img.src = n.image_url || ''; img.style.display = n.image_url ? '' : 'none'; }
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
          const cls = { POLICY:'policy', EVENT:'event', VOLUNTEER:'volunteer', SUPPORT:'support' };
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
          // tb-loc-pill 안의 data-bind="user.region_dong" 노드를 GPS 라벨로 덮어쓰기
          const pill = document.querySelector('.tb-loc-pill [data-bind="user.region_dong"]');
          if (pill) {
            pill.textContent = geo.label;
            pill.removeAttribute("data-bind"); // 이후 Bind.apply 가 덮어쓰지 못하게
          }
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

    async function load(status) {
      const qs = status ? `?status=${status}` : '';
      try {
        const data = await API.get(`/api/v1/matches${qs}`);
        Bind.apply(document, data);
        postProcess();
      } catch (err) {
        Toast.error(`매칭 목록 실패: ${err.message}`);
      }
    }

    // 활동 요약 카드
    try {
      const [author, applicant] = await Promise.all([
        API.get('/api/v1/users/me/matches?role=author&status=MATCHING&size=1'),
        API.get('/api/v1/users/me/matches?role=applicant&status=PROGRESS&size=1'),
      ]);
      const reqEl = document.querySelector('.mac-side:first-child .mac-val');
      if (reqEl) reqEl.innerHTML = `${author.total}건<span>검토 중</span>`;
      const volEl = document.querySelector('.mac-side:last-child .mac-val');
      if (volEl) volEl.innerHTML = `${applicant.total}건<span>진행 중</span>`;
    } catch { /* 활동 카드 실패는 무시 */ }

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
  };

  // ─── Page boot: 지도 (카드 리스트 fallback) ─────────────────────────────────
  PreviewApp.bootMap = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const mapCanvas = document.getElementById('kakao-map-canvas');
    if (mapCanvas) mapCanvas.innerHTML = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#B8D9D9,#D4E8C4);font-size:13px;font-weight:700;color:rgba(30,18,10,0.4);">지도 준비 중</div>';

    let userLat = 37.3451, userLng = 126.7322;
    const radius = 5000;
    let currentCat = '';

    async function loadNearby(cat) {
      const catQs = cat ? `&category=${cat}` : '';
      try {
        const data = await API.get(`/api/v1/maps/stores?lat=${userLat}&lng=${userLng}&radius=${radius}${catQs}`);
        Bind.apply(document, data);
        document.querySelectorAll('#store-list a.place-row').forEach((a) => {
          const id = a.dataset.storeId;
          if (id) a.href = `store-detail.html?id=${id}`;
        });
      } catch (err) {
        Toast.error(`매장 로딩 실패: ${err.message}`);
      }
    }

    async function loadSearch(keyword) {
      try {
        const data = await API.get(`/api/v1/maps/stores/search?keyword=${encodeURIComponent(keyword)}`);
        Bind.apply(document, { stores: (data.results || []).map((r) => ({ ...r, distance_m: '—' })) });
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

    const CAT_MAP = { 전체:'', 카페:'CAFE', 공원:'PARK', 병원:'VET', 미용:'GROOMING', 식당:'RESTAURANT' };
    document.querySelectorAll('.chips-row .chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.chips-row .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentCat = CAT_MAP[chip.textContent.trim()] ?? '';
        loadNearby(currentCat);
      });
    });

    await loadNearby(currentCat);
  };

  // ─── Page boot: 매칭 생성 ────────────────────────────────────────────────
  PreviewApp.bootMatchNew = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const state = { petId: null, date: null, time: null, title: '', address: '', content: '' };
    let myPets = [];

    const steps = document.querySelectorAll('.wizard-step');
    function showStep(n) {
      steps.forEach((s, i) => s.hidden = i !== n);
      document.getElementById('step-indicator').textContent = `${n+1}/3`;
    }

    try {
      const me = await API.get('/api/v1/users/me');
      myPets = me.pets || [];
      const petGrid = document.getElementById('pet-select-grid');
      petGrid.innerHTML = '';
      myPets.forEach((p) => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'pet-v-card';
        card.dataset.petId = p.pet_id;
        card.innerHTML = `<div class="pet-v-icon ${p.species === 'CAT' ? 'cat' : 'dog'}"><i class="ph ph-${p.species === 'CAT' ? 'cat' : 'dog'}"></i></div><div class="pet-v-name">${p.name}</div>`;
        card.addEventListener('click', () => {
          petGrid.querySelectorAll('.pet-v-card').forEach(c => c.classList.remove('selected'));
          card.classList.add('selected');
          state.petId = p.pet_id;
        });
        petGrid.appendChild(card);
      });
    } catch (err) {
      Toast.error(`반려동물 로딩 실패: ${err.message}`);
    }

    document.getElementById('btn-step1-next').addEventListener('click', () => {
      if (!state.petId) { Toast.error('반려동물을 선택해 주세요.'); return; }
      showStep(1);
      initCalendar();
    });

    function initCalendar() {
      const cal = document.getElementById('calendar-grid');
      const now = new Date();
      const year = now.getFullYear(), month = now.getMonth();
      const firstDay = new Date(year, month, 1).getDay();
      const daysInMonth = new Date(year, month + 1, 0).getDate();
      document.getElementById('cal-month-label').textContent = `${year}년 ${month+1}월`;
      cal.innerHTML = '';
      for (let i = 0; i < firstDay; i++) cal.insertAdjacentHTML('beforeend', '<span></span>');
      for (let d = 1; d <= daysInMonth; d++) {
        const btn = document.createElement('button');
        btn.type = 'button'; btn.textContent = d; btn.className = 'cal-day';
        if (new Date(year, month, d) < now) { btn.disabled = true; btn.className += ' past'; }
        btn.addEventListener('click', () => {
          cal.querySelectorAll('.cal-day').forEach(b => b.classList.remove('selected'));
          btn.classList.add('selected');
          state.date = `${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
        });
        cal.appendChild(btn);
      }
    }

    document.querySelectorAll('.time-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.time-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        state.time = chip.dataset.time;
      });
    });

    document.getElementById('btn-step2-next').addEventListener('click', () => {
      if (!state.date) { Toast.error('날짜를 선택해 주세요.'); return; }
      showStep(2);
    });

    document.getElementById('match-new-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      state.title = document.getElementById('match-title').value.trim();
      state.address = document.getElementById('match-address').value.trim();
      state.content = document.getElementById('match-content').value.trim();
      if (!state.title) { Toast.error('제목을 입력해 주세요.'); return; }
      const btn = e.submitter || e.target.querySelector('[type=submit]');
      btn.disabled = true;
      try {
        const body = {
          pet_id: state.petId,
          title: state.title,
          address: state.address || null,
          content: state.content,
          desired_date: state.date,
          latitude: 37.3451,
          longitude: 126.7322,
        };
        const created = await API.post('/api/v1/matches', body);
        location.href = `match-detail.html?id=${created.match_id}`;
      } catch (err) {
        Toast.error(`요청 생성 실패: ${err.message}`);
        btn.disabled = false;
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

    const seen = new Set();
    try {
      const initial = await API.get(`/api/v1/matches/${matchId}/applications/${appId}/messages?size=30`);
      // created_at DESC → 화면은 오래된→최신 → reverse
      const items = initial.items || [];
      items.forEach((m) => seen.add(m.id));
      [...items].reverse().forEach(renderMsg);
    } catch (err) {
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
  };

  // ─── Page boot: 소식 ──────────────────────────────────────────────────────
  PreviewApp.bootNews = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const CAT_LABEL = { POLICY:'정책', EVENT:'행사', VOLUNTEER:'봉사', SUPPORT:'지원' };
    let allNews = [];

    function renderNews(list) {
      const feat = document.getElementById('news-feat');
      const rows = document.getElementById('news-rows');
      if (!list.length) { feat && (feat.hidden = true); rows && (rows.innerHTML = ''); return; }

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
            const catClass = { POLICY:'policy', EVENT:'event', VOLUNTEER:'volunteer', SUPPORT:'support' };
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

    try {
      const data = await API.get('/api/v1/news');
      allNews = data.news || [];
      renderNews(allNews);
    } catch (err) {
      Toast.error(`뉴스 로딩 실패: ${err.message}`);
    }

    const CAT_MAP = { all:'', 행사:'EVENT', 봉사:'VOLUNTEER', 지원:'SUPPORT', 정책:'POLICY' };
    document.querySelectorAll('.chips-row .chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.chips-row .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        const cat = CAT_MAP[chip.textContent.trim()] ?? '';
        const filtered = cat ? allNews.filter(n => n.category === cat) : allNews;
        renderNews(filtered);
      });
    });
  };

  // ─── Page boot: 알림 ──────────────────────────────────────────────────────
  PreviewApp.bootNotifications = async function () {
    if (!Auth.requireLogin()) return;
    DebugPanel.mount();

    const CAT_MAP = { 전체:'', 매칭:'MATCH', 소식:'NEWS', 시스템:'SYSTEM' };
    let currentCat = '';

    async function load(cat) {
      const qs = cat ? `?category=${cat}` : '';
      try {
        const data = await API.get(`/api/v1/notifications${qs}`);
        const listEl = document.getElementById('notif-list');
        const tmpl = document.getElementById('tmpl-notif');
        if (!listEl || !tmpl) return;
        listEl.innerHTML = '';
        (data.items || []).forEach((item) => {
          const node = tmpl.content.cloneNode(true);
          const row = node.querySelector('.notif-item');
          if (row) {
            if (!item.is_read) row.classList.add('unread');
            row.addEventListener('click', async () => {
              if (!item.is_read) {
                await API.post(`/api/v1/notifications/${item.id}/read`, {}).catch(() => {});
                row.classList.remove('unread');
              }
              if (item.link) location.href = item.link;
            });
          }
          const titleEl = node.querySelector('.notif-title');
          if (titleEl) titleEl.textContent = item.title;
          const bodyEl = node.querySelector('.notif-body');
          if (bodyEl) bodyEl.textContent = item.body;
          const timeEl = node.querySelector('.notif-time');
          if (timeEl) {
            const d = new Date(item.created_at);
            timeEl.textContent = `${d.getMonth()+1}.${d.getDate()}`;
          }
          const iconEl = node.querySelector('.notif-icon');
          if (iconEl) {
            const cls = { MATCH:'type-match', NEWS:'type-news', SYSTEM:'type-sys', VOLUNTEER:'type-vol' };
            iconEl.className = `notif-icon ${cls[item.category] || ''}`;
          }
          listEl.appendChild(node);
        });
      } catch (err) {
        Toast.error(`알림 로딩 실패: ${err.message}`);
      }
    }

    await load(currentCat);

    document.querySelectorAll('.chips-row .chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.chips-row .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentCat = CAT_MAP[chip.textContent.trim()] ?? '';
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

    let me, detail;
    try {
      [me, detail] = await Promise.all([
        API.get('/api/v1/users/me'),
        API.get(`/api/v1/matches/${matchId}`),
      ]);
    } catch (err) { Toast.error(err.message); return; }

    const STATUS_LABEL = { WAITING:'모집중', MATCHING:'검토중', PROGRESS:'진행중', DONE:'완료' };
    const isOwner = detail.author?.user_id === me.id;

    Bind.apply(document, {
      ...detail,
      status_label: STATUS_LABEL[detail.status] || detail.status,
      pet_name: detail.pet?.name || '—',
      pet_species: detail.pet?.species === 'CAT' ? '고양이' : '강아지',
      author_nickname: detail.author?.nickname || '—',
    });

    const appsSection = document.getElementById('apps-section');
    if (appsSection) appsSection.hidden = !isOwner;

    if (isOwner && detail.status === 'WAITING') {
      try {
        const apps = await API.get(`/api/v1/matches/${matchId}/applications`);
        const listEl = document.getElementById('apps-list');
        const tmpl = document.getElementById('tmpl-applicant');
        (apps.items || []).forEach((app) => {
          const node = tmpl.content.cloneNode(true);
          node.querySelector('.app-nickname').textContent = app.applicant?.nickname || '—';
          node.querySelector('.app-status').textContent = app.status;
          const acceptBtn = node.querySelector('.btn-accept');
          const rejectBtn = node.querySelector('.btn-reject');
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
              rejectBtn.disabled = true;
              rejectBtn.textContent = '거절됨';
            } catch (err) { Toast.error(err.message); }
          });
          listEl.appendChild(node);
        });
      } catch (err) { Toast.error(err.message); }
    }

    const applyBtn = document.getElementById('btn-apply');
    if (applyBtn) {
      if (!isOwner && detail.status === 'WAITING') {
        applyBtn.hidden = false;
        applyBtn.addEventListener('click', async () => {
          applyBtn.disabled = true;
          try {
            await API.post(`/api/v1/matches/${matchId}/apply`, { message: '' });
            Toast.ok('봉사 신청이 완료되었습니다.');
            applyBtn.textContent = '신청 완료';
          } catch (err) {
            Toast.error(err.message);
            applyBtn.disabled = false;
          }
        });
      } else {
        applyBtn.hidden = true;
      }
    }
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
