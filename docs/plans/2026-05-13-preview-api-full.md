# Preview API 통합 & 세부 화면 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `app/static/preview/` 내 모든 화면을 실제 FastAPI 백엔드 API에 연결하고, 10개의 신규 세부 화면을 구현한다.

**Architecture:** API-only 방식(정적 fallback 없음). JWT 토큰은 `sessionStorage` 우선 / `localStorage` 폴백. `preview-app.js`의 `Auth`, `API`, `Bind` 모듈을 공유하고, 각 페이지가 `PreviewApp.boot*()` 함수를 DOMContentLoaded 시 호출하는 구조.

**Tech Stack:** Vanilla ES2020, Phosphor Icons 2.1.1, SUIT Variable Font, FastAPI `/api/v1`

---

## 파일 구조

**수정:**
- `app/static/preview/preview-app.js` — Auth 메서드 추가, boot 함수 신규/수정
- `app/static/preview/index.html` — 뉴스/알림 뱃지 data-bind 추가
- `app/static/preview/news.html` — data-bind-each 템플릿 추가
- `app/static/preview/notifications.html` — data-bind-each 템플릿 추가
- `app/static/preview/match.html` — status 번역 + data-s 처리
- `app/static/preview/my.html` — user 데이터 data-bind 확인/수정
- `app/static/preview/map.html` — stores data-bind-each + 카테고리 필터

**신규:**
- `app/static/preview/login.html`
- `app/static/preview/signup.html`
- `app/static/preview/match-new.html` — 3-step wizard
- `app/static/preview/match-detail.html`
- `app/static/preview/my-matches.html`
- `app/static/preview/store-detail.html`
- `app/static/preview/news-detail.html`
- `app/static/preview/chat.html`
- `app/static/preview/profile-edit.html`
- `app/static/preview/pet-form.html`

---

## API 응답 필드 레퍼런스

### `GET /api/v1/home/dashboard` → `HomeDashboardResponse`
```
walk_score: int|null, weather: {condition, temp_c, dust_grade}, nearby_store_count: int,
my_match_summary: {as_author: {match_id,title,desired_date,status,applications_count}|null,
                   as_applicant: {match_id,title,desired_date,status,my_application_status}|null},
volunteer_stats: {total_count, avg_rating}|null, unread_notification_count: int,
user: {nickname, role, region_si, region_dong}
```

### `GET /api/v1/news` → `NewsListResponse`
```
news: [{news_id, title, summary, published_date, link, image_url|null, category, publisher}]
```
※ category 값: POLICY / EVENT / VOLUNTEER / SUPPORT — 필터링은 클라이언트에서 처리

### `GET /api/v1/notifications` → `NotificationListResponse`
```
items: [{id, category, title, body, is_read, link|null, created_at}], total, unread_count, page, size
```
※ category 값: MATCH / NEWS / SYSTEM / VOLUNTEER

### `GET /api/v1/matches` → `MatchListResponse`
```
items: [{match_id, title, address|null, desired_date|null, status, author_nickname|null, created_at}],
total, page, size
```
※ status 값: WAITING / MATCHING / PROGRESS / DONE  
※ UI 레이블: WAITING→모집중, MATCHING→검토중, PROGRESS→진행중, DONE→완료

### `GET /api/v1/users/me` → `UserMeResponse`
```
id, email, nickname, phone|null, role, profile_image_url|null,
region_si|null, region_dong|null, pets:[{pet_id, name, species, breed|null, is_neutered}], created_at
```

### `GET /api/v1/users/me/activity-stats` → `ActivityStatsResponse`
```
my_match_count, volunteer_completed_count, favorite_count,
badge: {level, label, next_level_threshold, current_count}
```

### `GET /api/v1/matches/{id}` → `MatchDetail`
```
match_id, author:{user_id,nickname}, pet:{pet_id,name,species,is_neutered}|null,
title, content, address|null, desired_date|null, status, applications_count, created_at
```

### `GET /api/v1/matches/{id}/applications` → `ApplicationListResponse`
```
items: [{application_id, applicant:{applicant_id,nickname}, message|null, status, created_at}],
total, page, size
```

### `GET /api/v1/maps/stores` → `StoreNearbyResponse`
```
stores: [{store_id, name, category, address, distance_m, lat, lng, avg_rating|null, review_count, is_favorited}]
```

### `GET /api/v1/news/{news_id}` → `NewsDetail`
```
news_id, title, content, official_link, published_date, image_url|null, category, publisher
```

---

## Phase 1 Tasks

---

### Task 1: Auth 메서드 추가 + login.html + signup.html

**Files:**
- Modify: `app/static/preview/preview-app.js`
- Create: `app/static/preview/login.html`
- Create: `app/static/preview/signup.html`

- [ ] **Step 1: preview-app.js에 Auth.login / logout / signup 메서드 추가**

`preview-app.js`의 `Auth` 객체 (`clear()` 메서드 직후)에 추가:

```javascript
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
  window.location.href = '/preview/login.html';
},
```

- [ ] **Step 2: login.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#F5EDDE" />
  <title>시흥가개 — 로그인</title>
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/variable/woff2/SUIT-Variable.css" />
  <link rel="stylesheet" href="styles-v3.css" />
  <style>
    .auth-wrap { display:flex; flex-direction:column; align-items:center; justify-content:center;
      min-height:100dvh; padding:32px 32px calc(32px + env(safe-area-inset-bottom,0px)); }
    .auth-logo { font-size:36px; font-weight:900; letter-spacing:-0.05em; color:var(--ink); margin-bottom:8px; }
    .auth-logo span { color:var(--accent); }
    .auth-sub { font-size:13px; font-weight:600; color:var(--ink-mute); margin-bottom:40px; }
    .auth-form { width:100%; display:flex; flex-direction:column; gap:12px; }
    .auth-field { width:100%; padding:15px 16px; border-radius:var(--r-lg);
      border:1.5px solid var(--line); background:var(--card);
      font:inherit; font-size:14px; font-weight:600; color:var(--ink);
      outline:none; transition:border-color 0.18s; box-sizing:border-box; }
    .auth-field:focus { border-color:var(--accent); }
    .auth-field::placeholder { color:var(--ink-mute); font-weight:500; }
    .auth-btn { width:100%; padding:16px; border-radius:var(--r-lg);
      background:var(--ink); color:#fff; border:none; font:inherit;
      font-size:15px; font-weight:800; letter-spacing:-0.02em; cursor:pointer;
      transition:transform 0.18s var(--spring); margin-top:4px; }
    .auth-btn:active { transform:scale(0.97); }
    .auth-link { font-size:13px; font-weight:600; color:var(--ink-mute);
      text-align:center; margin-top:20px; }
    .auth-link a { color:var(--accent); font-weight:800; }
    .auth-err { font-size:12.5px; font-weight:700; color:var(--raspberry); text-align:center; min-height:18px; }
  </style>
</head>
<body>
<div class="auth-wrap">
  <div class="auth-logo">시흥<span>가개</span></div>
  <div class="auth-sub">반려동물 이동 지원 매칭 서비스</div>
  <form class="auth-form" id="loginForm">
    <input class="auth-field" type="tel" id="phone" placeholder="전화번호" autocomplete="tel" required />
    <input class="auth-field" type="password" id="password" placeholder="비밀번호" autocomplete="current-password" required />
    <div class="auth-err" id="errMsg"></div>
    <button class="auth-btn" type="submit">로그인</button>
  </form>
  <div class="auth-link">계정이 없으신가요? <a href="signup.html">회원가입</a></div>
</div>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js"></script>
<script src="preview-app.js"></script>
<script>
(() => {
  if (Auth.getAccess()) {
    const params = new URLSearchParams(location.search);
    location.href = params.get('redirect') || 'index.html';
    return;
  }
  DebugPanel.mount();
  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const phone = document.getElementById('phone').value.trim();
    const password = document.getElementById('password').value;
    const errEl = document.getElementById('errMsg');
    errEl.textContent = '';
    try {
      await Auth.login(phone, password);
      const params = new URLSearchParams(location.search);
      location.href = params.get('redirect') || 'index.html';
    } catch (err) {
      errEl.textContent = err.status === 401 ? '전화번호 또는 비밀번호가 올바르지 않습니다.' : err.message;
    }
  });
})();
</script>
</body>
</html>
```

- [ ] **Step 3: signup.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#F5EDDE" />
  <title>시흥가개 — 회원가입</title>
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/variable/woff2/SUIT-Variable.css" />
  <link rel="stylesheet" href="styles-v3.css" />
  <style>
    /* login.html과 동일한 .auth-* 스타일 포함 (복사) */
    .auth-wrap { display:flex; flex-direction:column; align-items:center; justify-content:center;
      min-height:100dvh; padding:32px 32px calc(32px + env(safe-area-inset-bottom,0px)); }
    .auth-logo { font-size:36px; font-weight:900; letter-spacing:-0.05em; color:var(--ink); margin-bottom:8px; }
    .auth-logo span { color:var(--accent); }
    .auth-sub { font-size:13px; font-weight:600; color:var(--ink-mute); margin-bottom:40px; }
    .auth-form { width:100%; display:flex; flex-direction:column; gap:12px; }
    .auth-field { width:100%; padding:15px 16px; border-radius:var(--r-lg);
      border:1.5px solid var(--line); background:var(--card);
      font:inherit; font-size:14px; font-weight:600; color:var(--ink);
      outline:none; transition:border-color 0.18s; box-sizing:border-box; }
    .auth-field:focus { border-color:var(--accent); }
    .auth-field::placeholder { color:var(--ink-mute); font-weight:500; }
    .auth-btn { width:100%; padding:16px; border-radius:var(--r-lg);
      background:var(--ink); color:#fff; border:none; font:inherit;
      font-size:15px; font-weight:800; letter-spacing:-0.02em; cursor:pointer;
      transition:transform 0.18s var(--spring); margin-top:4px; }
    .auth-btn:active { transform:scale(0.97); }
    .auth-link { font-size:13px; font-weight:600; color:var(--ink-mute);
      text-align:center; margin-top:20px; }
    .auth-link a { color:var(--accent); font-weight:800; }
    .auth-err { font-size:12.5px; font-weight:700; color:var(--raspberry); text-align:center; min-height:18px; }
  </style>
</head>
<body>
<div class="auth-wrap">
  <div class="auth-logo">시흥<span>가개</span></div>
  <div class="auth-sub">새 계정 만들기</div>
  <form class="auth-form" id="signupForm">
    <input class="auth-field" type="text" id="nickname" placeholder="닉네임" required />
    <input class="auth-field" type="tel" id="phone" placeholder="전화번호" autocomplete="tel" required />
    <input class="auth-field" type="password" id="password" placeholder="비밀번호 (8자 이상)" autocomplete="new-password" required />
    <div class="auth-err" id="errMsg"></div>
    <button class="auth-btn" type="submit">가입하기</button>
  </form>
  <div class="auth-link">이미 계정이 있으신가요? <a href="login.html">로그인</a></div>
</div>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js"></script>
<script src="preview-app.js"></script>
<script>
(() => {
  DebugPanel.mount();
  document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const nickname = document.getElementById('nickname').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const password = document.getElementById('password').value;
    const errEl = document.getElementById('errMsg');
    errEl.textContent = '';
    try {
      await Auth.signup(phone, password, nickname);
      location.href = 'index.html';
    } catch (err) {
      errEl.textContent = err.body?.detail || err.message;
    }
  });
})();
</script>
</body>
</html>
```

- [ ] **Step 4: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/login.html app/static/preview/signup.html
git commit -m "feat(preview): add auth methods + login/signup pages"
```

---

### Task 2: bootNews() 추가 + news.html data-bind 마크업

**Files:**
- Modify: `app/static/preview/preview-app.js`
- Modify: `app/static/preview/news.html`

- [ ] **Step 1: preview-app.js에 bootNews() 추가**

`PreviewApp.bootChat` 정의 뒤에 추가:

```javascript
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

    // 피처드: 첫 번째 아이템
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

    // 목록: 나머지 아이템
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

  // 카테고리 필터 칩
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
```

- [ ] **Step 2: news.html 수정 — data-bind 마크업 교체**

news.html의 `<a class="news-feat ...">` ID 추가, 뉴스 목록 구조 교체:

```html
<!-- 피처드 뉴스: id 추가, href는 JS에서 설정 -->
<a class="news-feat anim-fade-slide-up delay-2" id="news-feat" href="#">
  <img class="nf-img" src="" alt="" loading="lazy" />
  <div class="nf-body">
    <span class="nf-cat">정책</span>
    <div class="nf-title">로딩 중...</div>
    <div class="nf-meta"></div>
  </div>
</a>

<!-- 뉴스 목록: id 추가 + 템플릿 -->
<template id="tmpl-news-row">
  <a class="news-row" href="#">
    <span class="nr-cat policy">정책</span>
    <span class="nr-title"></span>
    <span class="nr-date"></span>
  </a>
</template>
<div class="news-rows anim-fade-slide-up delay-3" id="news-rows"></div>
```

기존 정적 `<a class="news-row">` 8개는 `<div id="news-rows">` 내부에서 삭제하고 위 구조로 교체.

마지막 `<script>` 섹션 아래에 boot 호출 추가:
```html
<script src="preview-app.js"></script>
<script>document.addEventListener("DOMContentLoaded", () => PreviewApp.bootNews());</script>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/news.html
git commit -m "feat(preview): wire news page to GET /api/v1/news + client-side category filter"
```

---

### Task 3: bootNotifications() 추가 + notifications.html data-bind 마크업

**Files:**
- Modify: `app/static/preview/preview-app.js`
- Modify: `app/static/preview/notifications.html`

- [ ] **Step 1: preview-app.js에 bootNotifications() 추가**

```javascript
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

  // 필터 칩
  document.querySelectorAll('.chips-row .chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.chips-row .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      currentCat = CAT_MAP[chip.textContent.trim()] ?? '';
      load(currentCat);
    });
  });

  // 모두 읽음
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
```

- [ ] **Step 2: notifications.html 수정 — 템플릿 + ID 추가**

`notifications.html`에서:
1. "모두 읽음" 버튼에 `id="btn-read-all"` 추가
2. 정적 알림 5개를 `<div id="notif-list">` 안에 넣고, 별도 `<template>` 으로 구조 정의:

```html
<template id="tmpl-notif">
  <div class="notif-item">
    <div class="notif-icon type-match"><i class="ph ph-handshake"></i></div>
    <div class="notif-body-wrap">
      <div class="notif-title"></div>
      <div class="notif-body"></div>
    </div>
    <span class="notif-time"></span>
  </div>
</template>
<div id="notif-list"></div>
```

기존 정적 알림 아이템들은 제거하고 `#notif-list` 빈 div로 교체.

3. boot 호출 추가 (기존 inline script 아래):
```html
<script src="preview-app.js"></script>
<script>document.addEventListener("DOMContentLoaded", () => PreviewApp.bootNotifications());</script>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/notifications.html
git commit -m "feat(preview): wire notifications page to GET /api/v1/notifications"
```

---

### Task 4: index.html — 뉴스 프리뷰 + 알림 뱃지 연결

**Files:**
- Modify: `app/static/preview/preview-app.js` (bootHome 업데이트)
- Modify: `app/static/preview/index.html`

- [ ] **Step 1: bootHome() 업데이트 — 뉴스 병렬 fetch 추가**

`preview-app.js`의 기존 `PreviewApp.bootHome` 함수에서 `try` 블록을 아래로 교체:

```javascript
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

  // 홈 뉴스 프리뷰: 피처드 + 2개 목록
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
    row.querySelector('.nr-title') && (row.querySelector('.nr-title').textContent = item.title);
    const dateEl = row.querySelector('.nr-date');
    if (dateEl) dateEl.textContent = item.published_date ? item.published_date.slice(5) : '';
  });
} catch (err) {
  Toast.error(`홈 로딩 실패: ${err.message}`);
}
```

- [ ] **Step 2: index.html — 알림 dot 기본값 hidden, 뉴스 href 업데이트**

`index.html`의 `.tb-bell .dot` span에 `hidden` 속성 추가 (JS에서 조건부 표시):
```html
<span class="dot" hidden></span>
```

"전체 보기" 뉴스 링크:
```html
<a class="v3-sh-link" href="news.html"><i class="ph ph-newspaper"></i>전체 보기</a>
```

match-pill의 정적 href를 `#`으로 두고 JS에서 처리 (이미 `href="#"` 형태).

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/index.html
git commit -m "feat(preview): wire home page news preview + notification badge"
```

---

### Task 5: match.html — status 번역 + data-s 처리

**Files:**
- Modify: `app/static/preview/preview-app.js` (bootMatch 업데이트)
- Modify: `app/static/preview/match.html`

- [ ] **Step 1: bootMatch() 업데이트 — status 번역 + data-s 설정 + activity stats**

기존 `PreviewApp.bootMatch` 함수를 아래로 교체:

```javascript
PreviewApp.bootMatch = async function () {
  if (!Auth.requireLogin()) return;
  DebugPanel.mount();

  const STATUS_LABEL = { WAITING:'모집중', MATCHING:'검토중', PROGRESS:'진행중', DONE:'완료' };
  const STATUS_CLASS = { WAITING:'WAITING', MATCHING:'MATCHING', PROGRESS:'PROGRESS', DONE:'DONE' };

  function postProcess() {
    document.querySelectorAll('#match-list .mc').forEach((card) => {
      const badge = card.querySelector('.mc-badge');
      if (!badge) return;
      const raw = badge.textContent.trim();
      badge.textContent = STATUS_LABEL[raw] || raw;
      badge.dataset.s = STATUS_CLASS[raw] || raw;
      card.dataset.s = STATUS_CLASS[raw] || raw;
    });
    document.querySelectorAll('#match-list a.mc').forEach((a) => {
      const match_id = new URL(a.href, location.href).searchParams.get('id') ||
        a.href.replace(/.*#match-/, '');
    });
  }

  const tabs = document.querySelectorAll('.match-tabs .match-tab');
  let currentStatus = '';

  async function load(status) {
    const qs = status ? `?status=${status}` : '';
    try {
      const data = await API.get(`/api/v1/matches${qs}`);
      Bind.apply(document, data);
      // href 고치기: data-bind-attr="href:#match-{match_id}" → 실제 링크로
      document.querySelectorAll('#match-list a[href^="#match-"]').forEach((a) => {
        const id = a.getAttribute('href').replace('#match-', '');
        if (id) a.href = `match-detail.html?id=${id}`;
      });
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

  // FAB → match-new
  document.querySelector('.match-fab')?.addEventListener('click', (e) => {
    e.preventDefault();
    location.href = 'match-new.html';
  });

  await load(currentStatus);
};
```

- [ ] **Step 2: match.html 템플릿 href 수정**

기존 템플릿의 href를 match-detail로 변경:
```html
<template id="tmpl-match">
  <a class="mc" data-bind-attr="href:match-detail.html?id={match_id}">
    <div class="mc-top">
      <span class="mc-badge" data-bind="status">—</span>
    </div>
    <div class="mc-title" data-bind="title">—</div>
    <div class="mc-meta"><i class="ph ph-map-pin"></i><span data-bind="address">—</span><span class="mc-meta-dot"></span><i class="ph ph-calendar"></i><span data-bind="desired_date">—</span></div>
    <div class="mc-bottom"><span class="mc-cnt"><i class="ph ph-user"></i><span data-bind="author_nickname">—</span></span></div>
  </a>
</template>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/match.html
git commit -m "feat(preview): wire match list with status translation + activity summary"
```

---

### Task 6: my.html — 사용자 정보 data-bind 확인 및 수정

**Files:**
- Modify: `app/static/preview/my.html`

`bootMy()`는 이미 `/users/me`, `/users/me/activity-stats`, `/users/me/matches`를 fetch하므로 HTML data-bind 마크업만 점검한다.

- [ ] **Step 1: my.html 점검 및 data-bind 추가**

`my.html`에서 다음 data-bind 속성이 없으면 추가:

```html
<!-- 닉네임 -->
<span data-bind="nickname">—</span>

<!-- 반려동물 목록: pets 배열 렌더 -->
<template id="tmpl-pet">
  <div class="pet-v-card">
    <div class="pet-v-icon">
      <i class="ph ph-paw-print"></i>
    </div>
    <div class="pet-v-name" data-bind="name">—</div>
    <div class="pet-v-species" data-bind="species">—</div>
  </div>
</template>
<div class="pets-scroll" data-bind-each="pets" data-template="#tmpl-pet"></div>

<!-- 통계 -->
<span data-bind="my_match_count">—</span>
<span data-bind="volunteer_completed_count">—</span>
```

실제 `my.html` 파일의 현재 구조에 맞게 data-bind 속성이 없는 요소에 추가.

로그아웃 버튼:
```html
<button onclick="Auth.logout()">로그아웃</button>
```

"내 요청 관리" 링크 → `my-matches.html`:
```html
<a href="my-matches.html">내 요청 관리</a>
```

- [ ] **Step 2: 커밋**

```bash
git add app/static/preview/my.html
git commit -m "feat(preview): fix my-page data-bind markup for user profile + pets"
```

---

### Task 7: map.html — stores data-bind-each + 카테고리 필터

**Files:**
- Modify: `app/static/preview/preview-app.js` (bootMap 업데이트)
- Modify: `app/static/preview/map.html`

- [ ] **Step 1: bootMap() 업데이트 — 카테고리 필터 + 스토어 링크**

기존 `PreviewApp.bootMap` 함수에 카테고리 필터 처리 추가:

```javascript
PreviewApp.bootMap = async function () {
  if (!Auth.requireLogin()) return;
  DebugPanel.mount();

  // KakaoMap placeholder (SDK 없음 — div만)
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
      // 각 카드 href → store-detail
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

  // GPS
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => { userLat = pos.coords.latitude; userLng = pos.coords.longitude; loadNearby(currentCat); },
      () => {},
      { enableHighAccuracy: false, timeout: 6000, maximumAge: 300000 }
    );
  }

  // 검색
  const searchInput = document.getElementById('map-search-input');
  if (searchInput) {
    let timer = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(timer);
      const v = searchInput.value.trim();
      timer = setTimeout(() => v ? loadSearch(v) : loadNearby(currentCat), 300);
    });
  }

  // 카테고리 필터
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
```

- [ ] **Step 2: map.html — KakaoMap placeholder + store-list template 추가**

`map.html`의 지도 영역 (`#mapCanvas` or 지도 div)에 id 부여:
```html
<div id="kakao-map-canvas" style="width:100%;height:240px;overflow:hidden;border-radius:var(--r-xl)"></div>
```

스토어 목록 template 추가:
```html
<template id="tmpl-store-row">
  <a class="place-row" href="#">
    <span class="place-rank">—</span>
    <div class="place-row-body">
      <div class="place-row-title" data-bind="name">—</div>
      <div class="place-row-meta">
        <span data-bind="category">—</span>
        <span> · </span>
        <span data-bind="distance_m">—</span>m
      </div>
    </div>
    <button class="place-heart" type="button"><i class="ph ph-heart"></i></button>
  </a>
</template>
<div id="store-list" data-bind-each="stores" data-template="#tmpl-store-row"></div>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/map.html
git commit -m "feat(preview): wire map page to GET /api/v1/maps/stores + category filter"
```

---

## Phase 2 Tasks

---

### Task 8: match-new.html — 3-step wizard

**Files:**
- Modify: `app/static/preview/preview-app.js`
- Create: `app/static/preview/match-new.html`

- [ ] **Step 1: preview-app.js에 bootMatchNew() 추가**

```javascript
// ─── Page boot: 매칭 생성 ────────────────────────────────────────────────
PreviewApp.bootMatchNew = async function () {
  if (!Auth.requireLogin()) return;
  DebugPanel.mount();

  const state = { petId: null, date: null, time: null, title: '', address: '', content: '' };
  let myPets = [];

  // Step 전환
  const steps = document.querySelectorAll('.wizard-step');
  function showStep(n) {
    steps.forEach((s, i) => s.hidden = i !== n);
    document.getElementById('step-indicator').textContent = `${n+1}/3`;
  }

  // Step 1: 반려동물 목록 로드
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

  // Step 1 → 2
  document.getElementById('btn-step1-next').addEventListener('click', () => {
    if (!state.petId) { Toast.error('반려동물을 선택해 주세요.'); return; }
    showStep(1);
    initCalendar();
  });

  // 달력 초기화
  function initCalendar() {
    const cal = document.getElementById('calendar-grid');
    const now = new Date();
    const year = now.getFullYear(), month = now.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    document.getElementById('cal-month-label').textContent = `${year}년 ${month+1}월`;
    cal.innerHTML = '';
    for (let i = 0; i < firstDay; i++) {
      cal.insertAdjacentHTML('beforeend', '<span></span>');
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const btn = document.createElement('button');
      btn.type = 'button'; btn.textContent = d;
      btn.className = 'cal-day';
      if (new Date(year, month, d) < now) { btn.disabled = true; btn.className += ' past'; }
      btn.addEventListener('click', () => {
        cal.querySelectorAll('.cal-day').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        state.date = `${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
      });
      cal.appendChild(btn);
    }
  }

  // 시간 칩
  document.querySelectorAll('.time-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.time-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.time = chip.dataset.time;
    });
  });

  // Step 2 → 3
  document.getElementById('btn-step2-next').addEventListener('click', () => {
    if (!state.date) { Toast.error('날짜를 선택해 주세요.'); return; }
    showStep(2);
  });

  // Step 3: 폼 → 제출
  document.getElementById('match-new-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    state.title = document.getElementById('match-title').value.trim();
    state.address = document.getElementById('match-address').value.trim();
    state.content = document.getElementById('match-content').value.trim();
    if (!state.title) { Toast.error('제목을 입력해 주세요.'); return; }
    try {
      const body = {
        pet_id: state.petId,
        title: state.title,
        address: state.address || null,
        content: state.content,
        desired_date: state.date,
        latitude: 37.3451,   // 기본 좌표 (위치 입력 없을 시 fallback)
        longitude: 126.7322,
      };
      const created = await API.post('/api/v1/matches', body);
      location.href = `match-detail.html?id=${created.match_id}`;
    } catch (err) {
      Toast.error(`요청 생성 실패: ${err.message}`);
    }
  });

  showStep(0);
};
```

- [ ] **Step 2: match-new.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#F5EDDE" />
  <title>시흥가개 — 이동 지원 요청</title>
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/variable/woff2/SUIT-Variable.css" />
  <link rel="stylesheet" href="styles-v3.css" />
  <style>
    .wiz-topbar { display:flex; align-items:center; gap:12px; padding:18px 24px 12px; }
    .wiz-back { width:36px; height:36px; border-radius:12px; background:var(--card); border:1px solid var(--line);
      display:flex; align-items:center; justify-content:center; cursor:pointer; text-decoration:none; color:var(--ink-soft); }
    .wiz-back i { font-size:18px; }
    .wiz-title { font-size:17px; font-weight:900; letter-spacing:-0.04em; color:var(--ink); flex:1; }
    .wiz-step { font-size:12px; font-weight:700; color:var(--ink-mute); }
    .wizard-step { padding:0 24px; }
    .wiz-section-title { font-size:15px; font-weight:900; letter-spacing:-0.03em; color:var(--ink); margin:20px 0 14px; }
    .pet-select-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
    .pet-v-card { display:flex; flex-direction:column; align-items:center; gap:8px; padding:14px 10px;
      background:var(--card); border:1.5px solid var(--line); border-radius:var(--r-lg);
      cursor:pointer; transition:border-color 0.18s, background 0.18s; }
    .pet-v-card.selected { border-color:var(--accent); background:var(--accent-soft); }
    .pet-v-icon { width:44px; height:44px; border-radius:14px; display:flex; align-items:center; justify-content:center; font-size:22px; }
    .pet-v-icon.dog { background:var(--accent-soft); color:var(--accent); }
    .pet-v-icon.cat { background:var(--raspberry-soft); color:var(--raspberry); }
    .pet-v-name { font-size:13px; font-weight:800; color:var(--ink); letter-spacing:-0.02em; }
    /* 달력 */
    .cal-month-row { display:flex; align-items:center; justify-content:center; margin-bottom:12px; }
    .cal-month-label { font-size:15px; font-weight:900; color:var(--ink); }
    .cal-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:4px; text-align:center; }
    .cal-day { width:100%; aspect-ratio:1; border-radius:10px; border:none; background:none;
      font:inherit; font-size:13px; font-weight:700; color:var(--ink); cursor:pointer;
      transition:background 0.15s; }
    .cal-day:hover { background:var(--accent-soft); }
    .cal-day.selected { background:var(--ink); color:#fff; }
    .cal-day.past { color:var(--line-strong); }
    .time-chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }
    .time-chip { padding:8px 16px; border-radius:999px; border:1.5px solid var(--line);
      background:var(--card); font:inherit; font-size:13px; font-weight:700;
      color:var(--ink-soft); cursor:pointer; transition:background 0.15s, border-color 0.15s; }
    .time-chip.active { background:var(--ink); color:#fff; border-color:var(--ink); }
    /* 폼 */
    .auth-form { display:flex; flex-direction:column; gap:12px; }
    .form-field { width:100%; padding:14px 16px; border-radius:var(--r-lg);
      border:1.5px solid var(--line); background:var(--card);
      font:inherit; font-size:14px; font-weight:600; color:var(--ink);
      outline:none; transition:border-color 0.18s; box-sizing:border-box; resize:none; }
    .form-field:focus { border-color:var(--accent); }
    .form-field::placeholder { color:var(--ink-mute); }
    .char-count { font-size:11px; font-weight:600; color:var(--ink-mute); text-align:right; }
    .btn-primary { width:100%; padding:16px; border-radius:var(--r-lg);
      background:var(--ink); color:#fff; border:none; font:inherit;
      font-size:15px; font-weight:800; cursor:pointer; margin-top:8px;
      transition:transform 0.18s var(--spring); }
    .btn-primary:active { transform:scale(0.97); }
    .safe-area { height:calc(40px + env(safe-area-inset-bottom,0px)); }
  </style>
</head>
<body>
<div class="app">
  <main class="screen">
    <div class="wiz-topbar">
      <a class="wiz-back" href="match.html"><i class="ph ph-arrow-left"></i></a>
      <span class="wiz-title">이동 지원 요청</span>
      <span class="wiz-step" id="step-indicator">1/3</span>
    </div>

    <!-- Step 1: 반려동물 선택 -->
    <div class="wizard-step" id="step-0">
      <div class="wiz-section-title">어떤 반려동물인가요?</div>
      <div class="pet-select-grid" id="pet-select-grid"></div>
      <button class="btn-primary" id="btn-step1-next" style="margin-top:32px">다음</button>
    </div>

    <!-- Step 2: 일정 선택 -->
    <div class="wizard-step" id="step-1" hidden>
      <div class="wiz-section-title">언제 필요하신가요?</div>
      <div class="cal-month-row"><span class="cal-month-label" id="cal-month-label"></span></div>
      <div class="cal-grid" id="calendar-grid"></div>
      <div class="time-chips">
        <button class="time-chip" type="button" data-time="09:00">오전 9시</button>
        <button class="time-chip" type="button" data-time="12:00">낮 12시</button>
        <button class="time-chip" type="button" data-time="15:00">오후 3시</button>
        <button class="time-chip" type="button" data-time="18:00">오후 6시</button>
      </div>
      <button class="btn-primary" id="btn-step2-next" style="margin-top:32px">다음</button>
    </div>

    <!-- Step 3: 요청 내용 -->
    <div class="wizard-step" id="step-2" hidden>
      <div class="wiz-section-title">요청 내용을 알려주세요</div>
      <form class="auth-form" id="match-new-form">
        <input class="form-field" type="text" id="match-title" placeholder="제목 (예: 정왕동 병원 이동 부탁드려요)" required />
        <input class="form-field" type="text" id="match-address" placeholder="목적지 주소 (선택)" />
        <textarea class="form-field" id="match-content" placeholder="추가 요청사항이나 메모 (500자 이내)" rows="5" maxlength="500"></textarea>
        <div class="char-count"><span id="char-cnt">0</span>/500</div>
        <button class="btn-primary" type="submit">요청 등록하기</button>
      </form>
    </div>

    <div class="safe-area"></div>
  </main>
</div>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js"></script>
<script src="preview-app.js"></script>
<script>
document.getElementById('match-content').addEventListener('input', function() {
  document.getElementById('char-cnt').textContent = this.value.length;
});
document.addEventListener("DOMContentLoaded", () => PreviewApp.bootMatchNew());
</script>
</body>
</html>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/match-new.html
git commit -m "feat(preview): add match creation 3-step wizard"
```

---

### Task 9: match-detail.html + bootMatchDetail()

**Files:**
- Modify: `app/static/preview/preview-app.js`
- Create: `app/static/preview/match-detail.html`

- [ ] **Step 1: preview-app.js에 bootMatchDetail() 추가**

```javascript
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

  // 기본 정보 바인딩
  Bind.apply(document, {
    ...detail,
    status_label: STATUS_LABEL[detail.status] || detail.status,
    pet_name: detail.pet?.name || '—',
    pet_species: detail.pet?.species === 'CAT' ? '고양이' : '강아지',
    author_nickname: detail.author?.nickname || '—',
  });

  // 오너: 신청자 목록 렌더
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
        node.querySelector('.btn-accept')?.addEventListener('click', async () => {
          try {
            await API.patch(`/api/v1/matches/${matchId}/applications/${app.application_id}`, { action: 'ACCEPT' });
            Toast.ok('신청을 수락했습니다. 채팅을 시작하세요.');
            location.href = `chat.html?match_id=${matchId}&application_id=${app.application_id}`;
          } catch (err) { Toast.error(err.message); }
        });
        node.querySelector('.btn-reject')?.addEventListener('click', async () => {
          try {
            await API.patch(`/api/v1/matches/${matchId}/applications/${app.application_id}`, { action: 'REJECT' });
            Toast.ok('거절했습니다.');
            node.querySelector('.app-status').textContent = 'REJECTED';
          } catch (err) { Toast.error(err.message); }
        });
        listEl.appendChild(node);
      });
    } catch (err) { Toast.error(err.message); }
  }

  // 봉사자: 신청 버튼 (WAITING 상태이고 비오너일 때)
  const applyBtn = document.getElementById('btn-apply');
  if (applyBtn) {
    if (!isOwner && detail.status === 'WAITING') {
      applyBtn.hidden = false;
      applyBtn.addEventListener('click', async () => {
        try {
          const res = await API.post(`/api/v1/matches/${matchId}/apply`, { message: '' });
          Toast.ok('봉사 신청이 완료되었습니다.');
          applyBtn.disabled = true;
          applyBtn.textContent = '신청 완료';
        } catch (err) { Toast.error(err.message); }
      });
    } else {
      applyBtn.hidden = true;
    }
  }
};
```

- [ ] **Step 2: match-detail.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#F5EDDE" />
  <title>시흥가개 — 매칭 상세</title>
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/variable/woff2/SUIT-Variable.css" />
  <link rel="stylesheet" href="styles-v3.css" />
  <style>
    .detail-topbar { display:flex; align-items:center; gap:12px; padding:18px 24px 12px; }
    .back-btn { width:36px; height:36px; border-radius:12px; background:var(--card); border:1px solid var(--line);
      display:flex; align-items:center; justify-content:center; text-decoration:none; color:var(--ink-soft); }
    .back-btn i { font-size:18px; }
    .detail-content { padding:0 24px; }
    .detail-badge { display:inline-flex; align-items:center; padding:5px 14px; border-radius:999px;
      font-size:12px; font-weight:900; background:var(--accent-dim); color:var(--accent); margin-bottom:12px; }
    .detail-title { font-size:22px; font-weight:900; letter-spacing:-0.04em; color:var(--ink); line-height:1.3; margin-bottom:12px; }
    .detail-meta { display:flex; flex-direction:column; gap:7px; font-size:13px; font-weight:600; color:var(--ink-mute); }
    .detail-meta-row { display:flex; align-items:center; gap:8px; }
    .detail-meta-row i { font-size:14px; }
    .detail-divider { height:1px; background:var(--line); margin:20px 0; }
    .detail-section-title { font-size:14px; font-weight:900; color:var(--ink); margin-bottom:12px; }
    .detail-body { font-size:14px; font-weight:600; line-height:1.7; color:var(--ink-soft); }
    /* 신청자 목록 */
    .applicant-row { display:flex; align-items:center; gap:12px; padding:13px 0; border-bottom:1px solid var(--line); }
    .applicant-row:last-child { border-bottom:none; }
    .app-avatar { width:40px; height:40px; border-radius:50%; background:var(--accent-soft);
      display:flex; align-items:center; justify-content:center; font-size:18px; color:var(--accent); flex-shrink:0; }
    .app-info { flex:1; }
    .app-nickname { font-size:14px; font-weight:800; color:var(--ink); }
    .app-status { font-size:11.5px; font-weight:700; color:var(--ink-mute); }
    .app-actions { display:flex; gap:8px; }
    .btn-accept { padding:8px 16px; border-radius:999px; background:var(--ink); color:#fff; border:none; font:inherit; font-size:13px; font-weight:800; cursor:pointer; }
    .btn-reject { padding:8px 14px; border-radius:999px; background:var(--bg-2); color:var(--ink-mute); border:none; font:inherit; font-size:13px; font-weight:700; cursor:pointer; }
    /* 하단 CTA */
    .detail-cta { padding:16px 24px calc(16px + env(safe-area-inset-bottom,0px)); }
    .btn-cta { width:100%; padding:16px; border-radius:var(--r-lg); background:var(--raspberry); color:#fff;
      border:none; font:inherit; font-size:15px; font-weight:800; cursor:pointer; }
    .btn-cta:active { opacity:0.85; }
  </style>
</head>
<body>
<div class="app">
  <main class="screen">
    <div class="detail-topbar">
      <a class="back-btn" href="match.html"><i class="ph ph-arrow-left"></i></a>
    </div>

    <div class="detail-content">
      <div class="detail-badge" data-bind="status_label">모집중</div>
      <div class="detail-title" data-bind="title">—</div>
      <div class="detail-meta">
        <div class="detail-meta-row"><i class="ph ph-user"></i><span data-bind="author_nickname">—</span></div>
        <div class="detail-meta-row"><i class="ph ph-paw-print"></i><span data-bind="pet_name">—</span> · <span data-bind="pet_species">—</span></div>
        <div class="detail-meta-row"><i class="ph ph-calendar"></i><span data-bind="desired_date">—</span></div>
        <div class="detail-meta-row"><i class="ph ph-map-pin"></i><span data-bind="address">주소 미입력</span></div>
      </div>
      <div class="detail-divider"></div>
      <div class="detail-section-title">요청 내용</div>
      <div class="detail-body" data-bind="content">—</div>

      <!-- 신청자 목록 (오너만) -->
      <div id="apps-section" hidden>
        <div class="detail-divider"></div>
        <div class="detail-section-title">신청자 목록 (<span data-bind="applications_count">0</span>명)</div>
        <template id="tmpl-applicant">
          <div class="applicant-row">
            <div class="app-avatar"><i class="ph ph-user"></i></div>
            <div class="app-info">
              <div class="app-nickname">—</div>
              <div class="app-status">—</div>
            </div>
            <div class="app-actions">
              <button class="btn-accept" type="button">수락</button>
              <button class="btn-reject" type="button">거절</button>
            </div>
          </div>
        </template>
        <div id="apps-list"></div>
      </div>
    </div>

    <div style="height:100px"></div>
  </main>

  <!-- 봉사자 신청 버튼 -->
  <div class="detail-cta">
    <button class="btn-cta" id="btn-apply" hidden>봉사 신청하기</button>
  </div>
</div>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js"></script>
<script src="preview-app.js"></script>
<script>document.addEventListener("DOMContentLoaded", () => PreviewApp.bootMatchDetail());</script>
</body>
</html>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/match-detail.html
git commit -m "feat(preview): add match detail page with owner/volunteer views"
```

---

### Task 10: my-matches.html

**Files:**
- Modify: `app/static/preview/preview-app.js`
- Create: `app/static/preview/my-matches.html`

- [ ] **Step 1: preview-app.js에 bootMyMatches() 추가**

```javascript
// ─── Page boot: 내 요청 목록 ──────────────────────────────────────────────
PreviewApp.bootMyMatches = async function () {
  if (!Auth.requireLogin()) return;
  DebugPanel.mount();

  const STATUS_LABEL = { WAITING:'모집중', MATCHING:'검토중', PROGRESS:'진행중', DONE:'완료' };
  const STATUS_CLASS = { WAITING:'WAITING', MATCHING:'MATCHING', PROGRESS:'PROGRESS', DONE:'DONE' };
  const tabs = document.querySelectorAll('.status-tab');
  let currentStatus = '';

  async function load(status) {
    const qs = status ? `&status=${status}` : '';
    try {
      const data = await API.get(`/api/v1/users/me/matches?role=author${qs}`);
      const listEl = document.getElementById('my-match-list');
      const tmpl = document.getElementById('tmpl-my-match');
      listEl.innerHTML = '';
      (data.items || []).forEach((item) => {
        const node = tmpl.content.cloneNode(true);
        const a = node.querySelector('a');
        if (a) {
          a.href = `match-detail.html?id=${item.match_id}`;
          a.dataset.s = item.status;
        }
        node.querySelector('.mc-badge').textContent = STATUS_LABEL[item.status] || item.status;
        node.querySelector('.mc-badge').dataset.s = item.status;
        node.querySelector('.mc-title').textContent = item.title;
        node.querySelector('[data-bind="desired_date"]').textContent = item.desired_date || '날짜 미정';
        node.querySelector('[data-bind="address"]').textContent = item.address || '';
        listEl.appendChild(node);
      });
    } catch (err) {
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
```

- [ ] **Step 2: my-matches.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#F5EDDE" />
  <title>시흥가개 — 내 요청</title>
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/variable/woff2/SUIT-Variable.css" />
  <link rel="stylesheet" href="styles-v3.css" />
  <style>
    .detail-topbar { display:flex; align-items:center; gap:12px; padding:18px 24px 12px; }
    .back-btn { width:36px; height:36px; border-radius:12px; background:var(--card); border:1px solid var(--line);
      display:flex; align-items:center; justify-content:center; text-decoration:none; color:var(--ink-soft); }
    .back-btn i { font-size:18px; }
    .page-title { font-size:20px; font-weight:900; letter-spacing:-0.04em; color:var(--ink); }
    .status-tabs { display:flex; gap:0; padding:0 24px; border-bottom:1.5px solid var(--line); overflow-x:auto; scrollbar-width:none; }
    .status-tabs::-webkit-scrollbar { display:none; }
    .status-tab { flex-shrink:0; padding:12px 14px; font:inherit; font-size:13.5px; font-weight:700;
      color:var(--ink-mute); background:none; border:none; cursor:pointer; white-space:nowrap;
      position:relative; }
    .status-tab.active { color:var(--ink); font-weight:900; }
    .status-tab.active::after { content:''; position:absolute; bottom:-1.5px; left:0; right:0;
      height:2.5px; background:var(--ink); border-radius:999px; }
    .match-list { display:flex; flex-direction:column; gap:12px; padding:16px 24px; }
    .mc { background:var(--card); border-radius:var(--r-xl); border:1px solid var(--line);
      box-shadow:var(--shadow-md); padding:16px 18px 14px; display:flex; flex-direction:column; gap:10px;
      text-decoration:none; color:inherit; position:relative; overflow:hidden;
      transition:transform 0.22s var(--spring); }
    .mc:active { transform:scale(0.978); }
    .mc::before { content:''; position:absolute; left:0; top:16px; bottom:16px; width:3.5px; border-radius:0 4px 4px 0; }
    .mc[data-s="WAITING"]::before { background:var(--raspberry); }
    .mc[data-s="MATCHING"]::before { background:var(--accent); }
    .mc[data-s="PROGRESS"]::before { background:var(--mint); }
    .mc[data-s="DONE"]::before { background:var(--line-strong); }
    .mc-top { display:flex; align-items:center; gap:8px; }
    .mc-badge { font-size:10.5px; font-weight:900; padding:4px 10px; border-radius:999px; flex-shrink:0; }
    .mc-badge[data-s="WAITING"] { background:var(--raspberry-dim); color:var(--raspberry); }
    .mc-badge[data-s="MATCHING"] { background:var(--accent-dim); color:var(--accent); }
    .mc-badge[data-s="PROGRESS"] { background:var(--mint-dim); color:var(--mint); }
    .mc-badge[data-s="DONE"] { background:rgba(30,18,10,0.06); color:var(--ink-mute); }
    .mc-title { font-size:15px; font-weight:900; color:var(--ink); line-height:1.32; letter-spacing:-0.035em; }
    .mc-meta { font-size:12px; font-weight:600; color:var(--ink-mute); display:flex; align-items:center; gap:6px; }
  </style>
</head>
<body>
<div class="app">
  <main class="screen">
    <div class="detail-topbar">
      <a class="back-btn" href="my.html"><i class="ph ph-arrow-left"></i></a>
      <span class="page-title">내 요청 목록</span>
    </div>
    <div class="status-tabs">
      <button class="status-tab active" data-status="">전체</button>
      <button class="status-tab" data-status="WAITING">모집중</button>
      <button class="status-tab" data-status="MATCHING">검토중</button>
      <button class="status-tab" data-status="PROGRESS">진행중</button>
      <button class="status-tab" data-status="DONE">완료</button>
    </div>
    <template id="tmpl-my-match">
      <a class="mc" href="#">
        <div class="mc-top"><span class="mc-badge">—</span></div>
        <div class="mc-title">—</div>
        <div class="mc-meta">
          <i class="ph ph-calendar"></i><span data-bind="desired_date">—</span>
          <span>·</span>
          <i class="ph ph-map-pin"></i><span data-bind="address">—</span>
        </div>
      </a>
    </template>
    <div class="match-list" id="my-match-list"></div>
    <div class="safe-area"></div>
  </main>
</div>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js"></script>
<script src="preview-app.js"></script>
<script>document.addEventListener("DOMContentLoaded", () => PreviewApp.bootMyMatches());</script>
</body>
</html>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/my-matches.html
git commit -m "feat(preview): add my-matches page with status filter"
```

---

### Task 11: store-detail.html + bootStoreDetail()

**Files:**
- Modify: `app/static/preview/preview-app.js`
- Create: `app/static/preview/store-detail.html`

- [ ] **Step 1: preview-app.js에 bootStoreDetail() 추가**

```javascript
// ─── Page boot: 매장 상세 ─────────────────────────────────────────────────
PreviewApp.bootStoreDetail = async function () {
  if (!Auth.requireLogin()) return;
  DebugPanel.mount();

  const params = new URLSearchParams(location.search);
  const storeId = parseInt(params.get('id'), 10);
  if (!storeId) { Toast.error('잘못된 접근입니다.'); return; }

  let store;
  try {
    const [detail, reviews] = await Promise.all([
      API.get(`/api/v1/maps/stores/${storeId}`),
      API.get(`/api/v1/maps/stores/${storeId}/reviews`),
    ]);
    store = detail;
    Bind.apply(document, { ...detail, avg_rating: detail.avg_rating?.toFixed(1) ?? '—' });

    // 즐겨찾기 버튼
    const favBtn = document.getElementById('btn-favorite');
    if (favBtn) {
      favBtn.dataset.favorited = detail.is_favorited ? '1' : '0';
      favBtn.querySelector('i').className = detail.is_favorited ? 'ph-fill ph-heart' : 'ph ph-heart';
      favBtn.addEventListener('click', async () => {
        const on = favBtn.dataset.favorited === '1';
        try {
          if (on) { await API.delete(`/api/v1/favorites/stores/${storeId}`); }
          else { await API.post(`/api/v1/favorites/stores/${storeId}`, {}); }
          favBtn.dataset.favorited = on ? '0' : '1';
          favBtn.querySelector('i').className = on ? 'ph ph-heart' : 'ph-fill ph-heart';
        } catch (err) { Toast.error(err.message); }
      });
    }

    // 리뷰 목록
    const reviewList = document.getElementById('review-list');
    const tmpl = document.getElementById('tmpl-review');
    (reviews.items || []).forEach((r) => {
      const node = tmpl.content.cloneNode(true);
      node.querySelector('.rv-nick').textContent = r.nickname || '익명';
      node.querySelector('.rv-rating').textContent = '★'.repeat(r.rating);
      node.querySelector('.rv-body').textContent = r.content;
      reviewList.appendChild(node);
    });
  } catch (err) { Toast.error(err.message); }

  // KakaoMap placeholder
  const mapEl = document.getElementById('store-mini-map');
  if (mapEl) mapEl.innerHTML = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#B8D9D9,#D4E8C4);font-size:12px;color:rgba(30,18,10,0.4);font-weight:700;">지도 준비 중</div>';

  // 리뷰 폼
  document.getElementById('review-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const rating = parseInt(document.getElementById('rv-stars').value, 10);
    const content = document.getElementById('rv-content').value.trim();
    if (!content || !rating) return;
    try {
      await API.post(`/api/v1/maps/stores/${storeId}/reviews`, { rating, content });
      Toast.ok('리뷰가 등록되었습니다.');
      location.reload();
    } catch (err) { Toast.error(err.message); }
  });
};
```

- [ ] **Step 2: store-detail.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#F5EDDE" />
  <title>시흥가개 — 매장 상세</title>
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/variable/woff2/SUIT-Variable.css" />
  <link rel="stylesheet" href="styles-v3.css" />
  <style>
    .detail-topbar { display:flex; align-items:center; justify-content:space-between; padding:18px 24px 12px; }
    .back-btn { width:36px; height:36px; border-radius:12px; background:var(--card); border:1px solid var(--line);
      display:flex; align-items:center; justify-content:center; text-decoration:none; color:var(--ink-soft); }
    .back-btn i { font-size:18px; }
    .fav-btn { width:36px; height:36px; border-radius:12px; background:var(--card); border:1px solid var(--line);
      display:flex; align-items:center; justify-content:center; cursor:pointer; font-size:18px; color:var(--ink-mute); }
    .fav-btn[data-favorited="1"] { color:var(--raspberry); }
    .store-hero { margin:0 24px 16px; padding:20px; background:var(--card); border-radius:var(--r-xl);
      border:1px solid var(--line); box-shadow:var(--shadow-md); }
    .store-name { font-size:22px; font-weight:900; letter-spacing:-0.04em; color:var(--ink); }
    .store-cat { font-size:12px; font-weight:700; color:var(--accent); margin-top:4px; }
    .store-rating { display:flex; align-items:center; gap:6px; margin-top:8px; font-size:13px; font-weight:700; color:var(--ink-mute); }
    .store-rating .star { color:var(--star); }
    .mini-map { margin:0 24px 16px; height:160px; border-radius:var(--r-xl); overflow:hidden; border:1px solid var(--line); }
    .store-meta { padding:0 24px; display:flex; flex-direction:column; gap:10px; margin-bottom:16px; }
    .meta-row { display:flex; align-items:center; gap:10px; font-size:13px; font-weight:600; color:var(--ink-soft); }
    .meta-row i { font-size:15px; color:var(--ink-mute); }
    .section-title { font-size:15px; font-weight:900; color:var(--ink); padding:0 24px; margin-bottom:12px; }
    .review-item { padding:14px 24px; border-bottom:1px solid var(--line); }
    .rv-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:5px; }
    .rv-nick { font-size:13px; font-weight:800; color:var(--ink); }
    .rv-rating { color:var(--star); font-size:12px; }
    .rv-body { font-size:13px; font-weight:600; color:var(--ink-soft); line-height:1.6; }
    .review-form { padding:16px 24px; display:flex; flex-direction:column; gap:10px; }
    .form-field { width:100%; padding:12px 14px; border-radius:var(--r-lg); border:1.5px solid var(--line);
      background:var(--card); font:inherit; font-size:14px; font-weight:600; color:var(--ink);
      outline:none; resize:none; box-sizing:border-box; }
    .form-field:focus { border-color:var(--accent); }
    .btn-primary { width:100%; padding:14px; border-radius:var(--r-lg); background:var(--ink); color:#fff;
      border:none; font:inherit; font-size:14px; font-weight:800; cursor:pointer; }
  </style>
</head>
<body>
<div class="app">
  <main class="screen">
    <div class="detail-topbar">
      <a class="back-btn" href="javascript:history.back()"><i class="ph ph-arrow-left"></i></a>
      <button class="fav-btn" id="btn-favorite" type="button"><i class="ph ph-heart"></i></button>
    </div>
    <div class="store-hero">
      <div class="store-name" data-bind="name">—</div>
      <div class="store-cat" data-bind="category">—</div>
      <div class="store-rating"><span class="star">★</span><span data-bind="avg_rating">—</span> · <span data-bind="review_count">0</span>개 리뷰</div>
    </div>
    <div class="mini-map" id="store-mini-map"></div>
    <div class="store-meta">
      <div class="meta-row"><i class="ph ph-map-pin"></i><span data-bind="address">—</span></div>
      <div class="meta-row"><i class="ph ph-phone"></i><span data-bind="phone">—</span></div>
    </div>
    <div class="section-title">리뷰</div>
    <template id="tmpl-review">
      <div class="review-item">
        <div class="rv-head">
          <span class="rv-nick">—</span>
          <span class="rv-rating">—</span>
        </div>
        <div class="rv-body">—</div>
      </div>
    </template>
    <div id="review-list"></div>
    <div class="section-title" style="margin-top:20px">리뷰 작성</div>
    <form class="review-form" id="review-form">
      <select class="form-field" id="rv-stars">
        <option value="">별점 선택</option>
        <option value="5">★★★★★ 5점</option>
        <option value="4">★★★★ 4점</option>
        <option value="3">★★★ 3점</option>
        <option value="2">★★ 2점</option>
        <option value="1">★ 1점</option>
      </select>
      <textarea class="form-field" id="rv-content" placeholder="리뷰를 남겨주세요" rows="3"></textarea>
      <button class="btn-primary" type="submit">등록</button>
    </form>
    <div class="safe-area"></div>
  </main>
</div>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js"></script>
<script src="preview-app.js"></script>
<script>document.addEventListener("DOMContentLoaded", () => PreviewApp.bootStoreDetail());</script>
</body>
</html>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/store-detail.html
git commit -m "feat(preview): add store detail page with reviews + favorites"
```

---

### Task 12: news-detail.html + bootNewsDetail()

**Files:**
- Modify: `app/static/preview/preview-app.js`
- Create: `app/static/preview/news-detail.html`

- [ ] **Step 1: preview-app.js에 bootNewsDetail() 추가**

```javascript
// ─── Page boot: 뉴스 상세 ─────────────────────────────────────────────────
PreviewApp.bootNewsDetail = async function () {
  if (!Auth.requireLogin()) return;
  DebugPanel.mount();

  const params = new URLSearchParams(location.search);
  const newsId = params.get('id');
  if (!newsId) { Toast.error('잘못된 접근입니다.'); return; }

  const CAT_LABEL = { POLICY:'정책', EVENT:'행사', VOLUNTEER:'봉사', SUPPORT:'지원' };

  try {
    const data = await API.get(`/api/v1/news/${newsId}`);
    document.title = `시흥가개 — ${data.title}`;
    Bind.apply(document, {
      ...data,
      category_label: CAT_LABEL[data.category] || data.category,
    });

    // 이미지
    const img = document.getElementById('news-hero-img');
    if (img) {
      if (data.image_url) { img.src = data.image_url; img.hidden = false; }
      else img.hidden = true;
    }

    // 본문 (plain text → <p> 태그로 분리)
    const bodyEl = document.getElementById('news-body');
    if (bodyEl && data.content) {
      bodyEl.innerHTML = data.content
        .split(/\n\n+/)
        .map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`)
        .join('');
    }

    // 원문 링크
    const linkBtn = document.getElementById('btn-official-link');
    if (linkBtn && data.official_link) {
      linkBtn.href = data.official_link;
      linkBtn.hidden = false;
    }
  } catch (err) { Toast.error(err.message); }
};
```

- [ ] **Step 2: news-detail.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#F5EDDE" />
  <title>시흥가개 — 뉴스</title>
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/variable/woff2/SUIT-Variable.css" />
  <link rel="stylesheet" href="styles-v3.css" />
  <style>
    .detail-topbar { display:flex; align-items:center; gap:12px; padding:18px 24px 12px; }
    .back-btn { width:36px; height:36px; border-radius:12px; background:var(--card); border:1px solid var(--line);
      display:flex; align-items:center; justify-content:center; text-decoration:none; color:var(--ink-soft); }
    .back-btn i { font-size:18px; }
    .news-hero-img { width:100%; height:200px; object-fit:cover; display:block; }
    .news-content { padding:20px 24px; }
    .news-cat-badge { display:inline-flex; align-items:center; padding:4px 12px; border-radius:999px;
      font-size:11px; font-weight:900; background:var(--accent-dim); color:var(--accent); margin-bottom:12px; }
    .news-title { font-size:22px; font-weight:900; letter-spacing:-0.04em; color:var(--ink); line-height:1.3; margin-bottom:10px; }
    .news-meta { font-size:12px; font-weight:600; color:var(--ink-mute); margin-bottom:20px; }
    .news-body { font-size:14.5px; font-weight:500; color:var(--ink-soft); line-height:1.75; }
    .news-body p { margin:0 0 14px; }
    .btn-official { display:flex; align-items:center; justify-content:center; gap:6px;
      margin:24px 0; padding:14px; border-radius:var(--r-lg); border:1.5px solid var(--line);
      background:var(--card); font:inherit; font-size:13.5px; font-weight:800; color:var(--ink);
      text-decoration:none; transition:background 0.18s; }
    .btn-official:active { background:var(--bg-2); }
    .btn-official i { font-size:15px; }
  </style>
</head>
<body>
<div class="app">
  <main class="screen">
    <div class="detail-topbar">
      <a class="back-btn" href="news.html"><i class="ph ph-arrow-left"></i></a>
    </div>
    <img class="news-hero-img" id="news-hero-img" src="" alt="" loading="lazy" hidden />
    <div class="news-content">
      <div class="news-cat-badge" data-bind="category_label">정책</div>
      <div class="news-title" data-bind="title">—</div>
      <div class="news-meta"><span data-bind="published_date">—</span> · <span data-bind="publisher">—</span></div>
      <div class="news-body" id="news-body"></div>
      <a class="btn-official" id="btn-official-link" href="#" target="_blank" rel="noopener noreferrer" hidden>
        <i class="ph ph-arrow-square-out"></i>원문 보기
      </a>
    </div>
    <div class="safe-area"></div>
  </main>
</div>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js"></script>
<script src="preview-app.js"></script>
<script>document.addEventListener("DOMContentLoaded", () => PreviewApp.bootNewsDetail());</script>
</body>
</html>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/news-detail.html
git commit -m "feat(preview): add news detail page"
```

---

### Task 13: chat.html — HTML 작성 (bootChat 기존 구현 활용)

**Files:**
- Create: `app/static/preview/chat.html`

`bootChat()`은 `preview-app.js`에 이미 완전히 구현되어 있다.
`chat.html`은 그 함수가 참조하는 ID들(`#chat-messages`, `#chat-input-form`, `#chat-input`)을 가진 HTML만 작성하면 된다.

- [ ] **Step 1: chat.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#F5EDDE" />
  <title>시흥가개 — 채팅</title>
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/variable/woff2/SUIT-Variable.css" />
  <link rel="stylesheet" href="styles-v3.css" />
  <style>
    .chat-wrap { display:flex; flex-direction:column; height:100dvh; }
    .chat-topbar { display:flex; align-items:center; gap:12px; padding:18px 24px 12px;
      border-bottom:1px solid var(--line); background:var(--bg); flex-shrink:0; }
    .back-btn { width:36px; height:36px; border-radius:12px; background:var(--card); border:1px solid var(--line);
      display:flex; align-items:center; justify-content:center; text-decoration:none; color:var(--ink-soft); flex-shrink:0; }
    .back-btn i { font-size:18px; }
    .chat-room-info { flex:1; }
    .chat-room-title { font-size:15px; font-weight:900; color:var(--ink); letter-spacing:-0.03em; }
    #chat-messages { flex:1; overflow-y:auto; padding:16px 24px; display:flex; flex-direction:column; gap:10px;
      scrollbar-width:thin; }
    .ch-msg { display:flex; }
    .ch-msg.mine { justify-content:flex-end; }
    .ch-bubble { max-width:75%; padding:10px 14px; border-radius:16px; font-size:14px; font-weight:600; line-height:1.5; }
    .ch-msg.mine .ch-bubble { background:var(--ink); color:#fff; border-radius:16px 4px 16px 16px; }
    .ch-msg.other .ch-bubble { background:var(--card); color:var(--ink); border:1px solid var(--line); border-radius:4px 16px 16px 16px; }
    .chat-input-wrap { padding:12px 16px calc(12px + env(safe-area-inset-bottom,0px)); border-top:1px solid var(--line);
      background:var(--bg); flex-shrink:0; }
    #chat-input-form { display:flex; gap:10px; align-items:flex-end; }
    #chat-input { flex:1; padding:12px 14px; border-radius:var(--r-lg); border:1.5px solid var(--line);
      background:var(--card); font:inherit; font-size:14px; font-weight:600; color:var(--ink);
      outline:none; resize:none; max-height:100px; }
    #chat-input:focus { border-color:var(--accent); }
    .chat-send-btn { width:42px; height:42px; border-radius:14px; background:var(--ink); color:#fff;
      border:none; display:flex; align-items:center; justify-content:center; cursor:pointer; flex-shrink:0; }
    .chat-send-btn i { font-size:18px; }
  </style>
</head>
<body>
<div class="app">
  <div class="chat-wrap">
    <div class="chat-topbar">
      <a class="back-btn" href="javascript:history.back()"><i class="ph ph-arrow-left"></i></a>
      <div class="chat-room-info">
        <div class="chat-room-title">이동 지원 채팅</div>
      </div>
    </div>
    <div id="chat-messages"></div>
    <div class="chat-input-wrap">
      <form id="chat-input-form">
        <textarea id="chat-input" placeholder="메시지 입력..." rows="1"></textarea>
        <button class="chat-send-btn" type="submit"><i class="ph-bold ph-paper-plane-right"></i></button>
      </form>
    </div>
  </div>
</div>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js"></script>
<script src="preview-app.js"></script>
<script>document.addEventListener("DOMContentLoaded", () => PreviewApp.bootChat());</script>
</body>
</html>
```

- [ ] **Step 2: 커밋**

```bash
git add app/static/preview/chat.html
git commit -m "feat(preview): add chat page HTML (wires to existing bootChat)"
```

---

### Task 14: profile-edit.html + bootProfileEdit()

**Files:**
- Modify: `app/static/preview/preview-app.js`
- Create: `app/static/preview/profile-edit.html`

- [ ] **Step 1: preview-app.js에 bootProfileEdit() 추가**

```javascript
// ─── Page boot: 프로필 편집 ───────────────────────────────────────────────
PreviewApp.bootProfileEdit = async function () {
  if (!Auth.requireLogin()) return;
  DebugPanel.mount();

  let me;
  try {
    me = await API.get('/api/v1/users/me');
    document.getElementById('edit-nickname').value = me.nickname || '';
  } catch (err) { Toast.error(err.message); return; }

  document.getElementById('profile-edit-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const nickname = document.getElementById('edit-nickname').value.trim();
    if (!nickname) { Toast.error('닉네임을 입력해 주세요.'); return; }
    try {
      await API.patch('/api/v1/users/me', { nickname });
      Toast.ok('프로필이 저장되었습니다.');
      setTimeout(() => { location.href = 'my.html'; }, 800);
    } catch (err) { Toast.error(err.message); }
  });
};
```

- [ ] **Step 2: profile-edit.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <title>시흥가개 — 프로필 편집</title>
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/variable/woff2/SUIT-Variable.css" />
  <link rel="stylesheet" href="styles-v3.css" />
  <style>
    .edit-topbar { display:flex; align-items:center; gap:12px; padding:18px 24px 12px; }
    .back-btn { width:36px; height:36px; border-radius:12px; background:var(--card); border:1px solid var(--line);
      display:flex; align-items:center; justify-content:center; text-decoration:none; color:var(--ink-soft); }
    .back-btn i { font-size:18px; }
    .page-title { font-size:20px; font-weight:900; letter-spacing:-0.04em; color:var(--ink); }
    .edit-body { padding:20px 24px; }
    .field-label { font-size:12px; font-weight:800; color:var(--ink-mute); letter-spacing:0.04em;
      text-transform:uppercase; margin-bottom:6px; }
    .form-field { width:100%; padding:14px 16px; border-radius:var(--r-lg);
      border:1.5px solid var(--line); background:var(--card); font:inherit;
      font-size:14px; font-weight:600; color:var(--ink); outline:none;
      transition:border-color 0.18s; box-sizing:border-box; margin-bottom:16px; }
    .form-field:focus { border-color:var(--accent); }
    .btn-primary { width:100%; padding:16px; border-radius:var(--r-lg); background:var(--ink);
      color:#fff; border:none; font:inherit; font-size:15px; font-weight:800; cursor:pointer;
      margin-top:8px; }
  </style>
</head>
<body>
<div class="app">
  <main class="screen">
    <div class="edit-topbar">
      <a class="back-btn" href="my.html"><i class="ph ph-arrow-left"></i></a>
      <span class="page-title">프로필 편집</span>
    </div>
    <div class="edit-body">
      <form id="profile-edit-form">
        <div class="field-label">닉네임</div>
        <input class="form-field" type="text" id="edit-nickname" placeholder="닉네임" required />
        <button class="btn-primary" type="submit">저장</button>
      </form>
    </div>
    <div class="safe-area"></div>
  </main>
</div>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js"></script>
<script src="preview-app.js"></script>
<script>document.addEventListener("DOMContentLoaded", () => PreviewApp.bootProfileEdit());</script>
</body>
</html>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/profile-edit.html
git commit -m "feat(preview): add profile edit page"
```

---

### Task 15: pet-form.html + bootPetForm()

**Files:**
- Modify: `app/static/preview/preview-app.js`
- Create: `app/static/preview/pet-form.html`

- [ ] **Step 1: preview-app.js에 bootPetForm() 추가**

```javascript
// ─── Page boot: 반려동물 추가/수정 ────────────────────────────────────────
PreviewApp.bootPetForm = async function () {
  if (!Auth.requireLogin()) return;
  DebugPanel.mount();

  const params = new URLSearchParams(location.search);
  const petId = parseInt(params.get('pet_id'), 10) || null;
  const isEdit = !!petId;

  if (isEdit) {
    document.getElementById('form-title').textContent = '반려동물 수정';
    document.getElementById('btn-delete').hidden = false;
    try {
      const me = await API.get('/api/v1/users/me');
      const pet = (me.pets || []).find(p => p.pet_id === petId);
      if (pet) {
        document.getElementById('pet-name').value = pet.name || '';
        document.getElementById('pet-species').value = pet.species || 'DOG';
        document.getElementById('pet-breed').value = pet.breed || '';
        document.getElementById('pet-neutered').checked = !!pet.is_neutered;
      }
    } catch (err) { Toast.error(err.message); }
  }

  document.getElementById('pet-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      name: document.getElementById('pet-name').value.trim(),
      species: document.getElementById('pet-species').value,
      breed: document.getElementById('pet-breed').value.trim() || null,
      is_neutered: document.getElementById('pet-neutered').checked,
    };
    try {
      if (isEdit) {
        await API.patch(`/api/v1/pets/${petId}`, body);
      } else {
        await API.post('/api/v1/pets', body);
      }
      Toast.ok(isEdit ? '수정되었습니다.' : '반려동물이 추가되었습니다.');
      setTimeout(() => { location.href = 'my.html'; }, 800);
    } catch (err) { Toast.error(err.message); }
  });

  document.getElementById('btn-delete')?.addEventListener('click', async () => {
    if (!confirm('반려동물을 삭제할까요?')) return;
    try {
      await API.delete(`/api/v1/pets/${petId}`);
      Toast.ok('삭제되었습니다.');
      setTimeout(() => { location.href = 'my.html'; }, 800);
    } catch (err) { Toast.error(err.message); }
  });
};
```

- [ ] **Step 2: pet-form.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <title>시흥가개 — 반려동물</title>
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/variable/woff2/SUIT-Variable.css" />
  <link rel="stylesheet" href="styles-v3.css" />
  <style>
    .edit-topbar { display:flex; align-items:center; gap:12px; padding:18px 24px 12px; }
    .back-btn { width:36px; height:36px; border-radius:12px; background:var(--card); border:1px solid var(--line);
      display:flex; align-items:center; justify-content:center; text-decoration:none; color:var(--ink-soft); }
    .back-btn i { font-size:18px; }
    .page-title { font-size:20px; font-weight:900; letter-spacing:-0.04em; color:var(--ink); flex:1; }
    .edit-body { padding:20px 24px; }
    .field-label { font-size:12px; font-weight:800; color:var(--ink-mute); letter-spacing:0.04em;
      text-transform:uppercase; margin-bottom:6px; }
    .form-field { width:100%; padding:14px 16px; border-radius:var(--r-lg);
      border:1.5px solid var(--line); background:var(--card); font:inherit;
      font-size:14px; font-weight:600; color:var(--ink); outline:none;
      transition:border-color 0.18s; box-sizing:border-box; margin-bottom:16px;
      appearance:none; }
    .form-field:focus { border-color:var(--accent); }
    .checkbox-row { display:flex; align-items:center; gap:10px; margin-bottom:20px; }
    .checkbox-row label { font-size:14px; font-weight:700; color:var(--ink); }
    .btn-primary { width:100%; padding:16px; border-radius:var(--r-lg); background:var(--ink);
      color:#fff; border:none; font:inherit; font-size:15px; font-weight:800; cursor:pointer; margin-top:8px; }
    .btn-danger { width:100%; padding:14px; border-radius:var(--r-lg); background:var(--raspberry-soft);
      color:var(--raspberry); border:1.5px solid rgba(240,66,112,0.18); font:inherit;
      font-size:14px; font-weight:800; cursor:pointer; margin-top:12px; }
  </style>
</head>
<body>
<div class="app">
  <main class="screen">
    <div class="edit-topbar">
      <a class="back-btn" href="my.html"><i class="ph ph-arrow-left"></i></a>
      <span class="page-title" id="form-title">반려동물 추가</span>
    </div>
    <div class="edit-body">
      <form id="pet-form">
        <div class="field-label">이름</div>
        <input class="form-field" type="text" id="pet-name" placeholder="반려동물 이름" required />
        <div class="field-label">종류</div>
        <select class="form-field" id="pet-species">
          <option value="DOG">강아지</option>
          <option value="CAT">고양이</option>
        </select>
        <div class="field-label">품종 (선택)</div>
        <input class="form-field" type="text" id="pet-breed" placeholder="예: 믹스" />
        <div class="checkbox-row">
          <input type="checkbox" id="pet-neutered" />
          <label for="pet-neutered">중성화 완료</label>
        </div>
        <button class="btn-primary" type="submit">저장</button>
      </form>
      <button class="btn-danger" id="btn-delete" hidden type="button">반려동물 삭제</button>
    </div>
    <div class="safe-area"></div>
  </main>
</div>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js"></script>
<script src="preview-app.js"></script>
<script>document.addEventListener("DOMContentLoaded", () => PreviewApp.bootPetForm());</script>
</body>
</html>
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/preview/preview-app.js app/static/preview/pet-form.html
git commit -m "feat(preview): add pet add/edit form page"
```

---

## 완료 후 검증

모든 Task 완료 후:

1. `docker compose up -d` — 백엔드 기동
2. `curl http://localhost:8000/health` — 정상 응답 확인
3. 브라우저에서 `http://localhost:8000/preview/login.html` 접속
4. 테스트 계정으로 로그인 → index.html 리디렉션 확인
5. 각 탭 이동: 홈 / 매칭 / 지도 / 소식 / 마이
6. 소식 탭에서 카테고리 필터 → 기사 클릭 → news-detail 진입 확인
7. 매칭 탭 FAB → match-new.html 3-step wizard 완주 → match-detail 진입 확인
8. 채팅: match-detail에서 수락 → chat.html 진입 → WS 연결 확인 (DebugPanel)
