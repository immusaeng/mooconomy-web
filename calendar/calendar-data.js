/* ═══════════════════════════════════════════════════════════════
   Daily MOO:conomy — /calendar/ 데이터 배선
   1순위: ../data/calendar_events.json (통합 캘린더 파이프라인의 canonical
   dataset — scripts/calendar_events/build_calendar.py 산출물). fresh 또는
   partial이고 이벤트가 1건 이상일 때만 이 데이터를 쓴다.
   fallback: ../data/home.json (calendar[]) + ../data/calendar_results.json
   — 파이프라인에 아직 실제 API 키가 배선되지 않았거나(현재 상태) 새
   데이터가 stale/검증 실패면 기존처럼 이 두 파일만으로 렌더링한다.
   샘플/픽스처 데이터는 어떤 경우에도 fallback으로 쓰지 않는다(canonical
   dataset은 실제 수집기가 만든 것만 이 경로에 존재한다).
   ═══════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  async function fetchJSON(url) {
    try {
      var res = await fetch(url + '?v=' + Date.now(), { cache: 'no-cache' });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { return null; }
  }
  function dateToYMD(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  var DOW_EN = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  var MONTH_EN = ['January','February','March','April','May','June','July','August','September','October','November','December'];

  function mergeEvents(home, results) {
    var base = (home && Array.isArray(home.calendar)) ? home.calendar.slice() : [];
    var byId = {};
    if (results && results.results) Object.keys(results.results).forEach(function (k) { byId[k] = results.results[k]; });
    return base.filter(function (e) { return e && e.time && e.title; }).map(function (ev) {
      var r = byId[ev.id];
      return {
        id: ev.id, time: ev.time, country: ev.country, title: ev.title,
        importance: ev.importance, resultText: r && r.resultText, resultStatus: r && r.status
      };
    }).sort(function (a, b) { return a.time < b.time ? -1 : 1; });
  }

  /* canonical dataset(data/calendar_events.json)을 이 페이지가 이미 쓰는
     내부 이벤트 모양({id,time,country,title,importance,resultText})으로
     바꾼다. fresh/partial이 아니거나 이벤트가 없으면 null을 돌려줘서
     호출부가 기존 fallback으로 넘어가게 한다. */
  function eventsFromCanonical(dataset) {
    if (!dataset || !dataset.freshness) return null;
    var status = dataset.freshness.status;
    if (status !== 'fresh' && status !== 'partial') return null;
    var events = Array.isArray(dataset.events) ? dataset.events : [];
    if (!events.length) return null;
    return events.map(function (e) {
      var resultText = null;
      if (e.actual !== null && e.actual !== undefined) {
        resultText = '실제 ' + e.actual + (e.unit ? e.unit : '') +
          (e.consensus !== null && e.consensus !== undefined ? ' (예상 ' + e.consensus + (e.unit ? e.unit : '') + ')' : '');
      }
      return {
        id: e.id, time: e.scheduledDate, country: e.country, title: e.title,
        importance: e.importance === 'unknown' ? null : e.importance,
        resultText: resultText, resultStatus: e.status,
      };
    }).sort(function (a, b) { return a.time < b.time ? -1 : 1; });
  }

  function parseMonthParam() {
    var q = new URLSearchParams(location.search).get('m');
    if (q && /^\d{4}-\d{2}$/.test(q)) {
      var parts = q.split('-');
      return { y: parseInt(parts[0], 10), m: parseInt(parts[1], 10) - 1 };
    }
    var today = new Date();
    return { y: today.getFullYear(), m: today.getMonth() };
  }

  function render(events, ym) {
    var today = new Date();
    var todayStr = dateToYMD(today);
    var y = ym.y, m = ym.m;
    var monthKey = y + '-' + String(m + 1).padStart(2, '0');

    $('curYear').textContent = y + ' · ' + (m + 1);
    $('curMonth').textContent = MONTH_EN[m];

    var prev = new Date(y, m - 1, 1), next = new Date(y, m + 1, 1);
    $('prevNum').textContent = String(prev.getMonth() + 1).padStart(2, '0');
    $('prevName').textContent = MONTH_EN[prev.getMonth()] + ' · 지난달';
    $('nextNum').textContent = String(next.getMonth() + 1).padStart(2, '0');
    $('nextName').textContent = MONTH_EN[next.getMonth()] + ' · 다음달';
    $('calPrev').href = '?m=' + prev.getFullYear() + '-' + String(prev.getMonth() + 1).padStart(2, '0');
    $('calNext').href = '?m=' + next.getFullYear() + '-' + String(next.getMonth() + 1).padStart(2, '0');

    var monthEvents = events.filter(function (e) { return e.time.slice(0, 7) === monthKey; });
    var byDate = {};
    monthEvents.forEach(function (e) { (byDate[e.time] = byDate[e.time] || []).push(e); });

    var firstDow = new Date(y, m, 1).getDay();
    var daysInMonth = new Date(y, m + 1, 0).getDate();
    var cells = [];
    for (var i = 0; i < firstDow; i++) cells.push('<div class="bcd bcd-blank"></div>');
    for (var day = 1; day <= daysInMonth; day++) {
      var ds = monthKey + '-' + String(day).padStart(2, '0');
      var dow = new Date(y, m, day).getDay();
      var evs = byDate[ds] || [];
      var cls = ['bcd'];
      if (dow === 0) cls.push('bcd-sun-cell');
      if (dow === 6) cls.push('bcd-sat-cell');
      if (evs.length) cls.push('bcd-has');
      if (ds === todayStr) cls.push('bcd-today');
      var inner = '<span class="bcd-n">' + day + '</span>';
      if (evs.length) {
        inner += '<div class="bcd-evs">' + evs.map(function (e) {
          var tagCls = e.importance === 'high' ? 'bcd-ev-hi' : (e.country === 'KR' ? 'bcd-ev-kr' : 'bcd-ev-us');
          return '<div class="bcd-ev ' + tagCls + '"><span class="bcd-ev-name">' + esc(e.title) + '</span></div>';
        }).join('') + '</div>';
      }
      cells.push('<div class="' + cls.join(' ') + '">' + inner + '</div>');
    }
    $('bcDays').innerHTML = cells.join('');

    $('metaTotal').textContent = monthEvents.length;
    $('metaHi').textContent = monthEvents.filter(function (e) { return e.importance === 'high'; }).length;

    var byCountry = { US: 0, KR: 0, hi: 0, other: 0 };
    monthEvents.forEach(function (e) {
      if (e.importance === 'high') byCountry.hi++;
      else if (e.country === 'KR') byCountry.KR++;
      else if (e.country === 'US') byCountry.US++;
      else byCountry.other++;
    });
    var filters = [];
    if (byCountry.US) filters.push('<div class="cs-filter"><span class="cs-filter-dot d-us"></span><span class="cs-filter-label">미국</span><span class="cs-filter-count">' + byCountry.US + '</span></div>');
    if (byCountry.KR) filters.push('<div class="cs-filter"><span class="cs-filter-dot d-kr"></span><span class="cs-filter-label">한국</span><span class="cs-filter-count">' + byCountry.KR + '</span></div>');
    if (byCountry.other) filters.push('<div class="cs-filter"><span class="cs-filter-dot d-corp"></span><span class="cs-filter-label">기타</span><span class="cs-filter-count">' + byCountry.other + '</span></div>');
    if (byCountry.hi) filters.push('<div class="cs-filter"><span class="cs-filter-dot d-hi"></span><span class="cs-filter-label">HIGH IMPACT</span><span class="cs-filter-count">' + byCountry.hi + '</span></div>');
    $('csFilters').innerHTML = filters.length ? filters.join('') : '<p class="cs-empty">이번 달 이벤트가 없습니다.</p>';

    var highlights = monthEvents.filter(function (e) { return e.importance === 'high'; }).slice(0, 3);
    if (highlights.length) {
      $('csHighlights').innerHTML = highlights.map(function (e) {
        var d = new Date(e.time + 'T00:00:00+09:00');
        return '<div class="cs-highlight"><div class="csh-top"><span class="csh-day">' + d.getDate() + '</span><span class="csh-dow">' + DOW_EN[d.getDay()] + '</span></div>' +
          '<h5 class="csh-title">' + esc(e.title) + '</h5></div>';
      }).join('');
    }

    $('calListTitle').textContent = MONTH_EN[m] + ' · 날짜순 상세';
    $('calListMeta').textContent = monthEvents.length + '건';
    var tl = $('calTl');
    if (!monthEvents.length) {
      tl.innerHTML = '<p class="cal-tl-empty">이번 달 예정된 이벤트 데이터가 없습니다.</p>';
    } else {
      tl.innerHTML = monthEvents.map(function (e) {
        var d = new Date(e.time + 'T00:00:00+09:00');
        var isToday = e.time === todayStr;
        var isHi = e.importance === 'high';
        var tags = isHi ? '<span class="ct-tag t-hi">HIGH IMPACT</span>' : '';
        if (e.country === 'KR') tags += '<span class="ct-tag t-kr">한국</span>';
        else if (e.country) tags += '<span class="ct-tag">' + esc(e.country) + '</span>';
        return '<article class="ct-item' + (isToday ? ' ct-today' : '') + '">' +
          '<div class="ct-date"><span class="ct-date-day">' + d.getDate() + '</span><span class="ct-date-dow">' + DOW_EN[d.getDay()] + '</span></div>' +
          '<div class="ct-body"><div class="ct-tags">' + tags + '</div><h4 class="ct-title">' + esc(e.title) + '</h4>' +
          (e.resultText ? '<p class="ct-desc">' + esc(e.resultText) + '</p>' : '') + '</div>' +
          '</article>';
      }).join('');
    }
  }

  async function init() {
    var canonicalP = fetchJSON('../data/calendar_events.json');
    var homeP = fetchJSON('../data/home.json');
    var resultsP = fetchJSON('../data/calendar_results.json');
    var canonical = await canonicalP, home = await homeP, results = await resultsP;

    var events = eventsFromCanonical(canonical);
    var usingCanonical = !!events;
    if (!events) events = mergeEvents(home, results);  // fallback: 기존 방식

    render(events, parseMonthParam());

    var freshnessEl = $('dataFreshness');
    if (freshnessEl) {
      if (usingCanonical && canonical.freshness && canonical.freshness.lastSuccessfulAt) {
        var d = new Date(canonical.freshness.lastSuccessfulAt);
        freshnessEl.textContent = '데이터 갱신 ' + d.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }) +
          ' (KST) · 상태: ' + canonical.freshness.status;
      } else {
        freshnessEl.textContent = '';
      }
    }
  }
  init();
})();
