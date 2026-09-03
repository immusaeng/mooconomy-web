/* ═══════════════════════════════════════════════════════════════
   Daily MOO:conomy — 홈페이지 데이터 배선
   v3 시안 마크업(index.html)에 실제 저장소 데이터(data/*.json)를 연결한다.
   원칙: 데이터가 없으면 요소를 숨기거나 빈 상태 문구를 쓴다.
         시안의 샘플 숫자(247호, Vol.Ⅵ, 9월 이벤트 28건 등)는 절대 쓰지 않는다.
   ═══════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  var IND_META = {
    kospi:  { name: '코스피', code: 'KS11' },
    kosdaq: { name: '코스닥', code: 'KQ11' },
    nasdaq: { name: '나스닥', code: 'IXIC' },
    sp500:  { name: 'S&P 500', code: 'SPX' },
    usdkrw: { name: '원/달러', code: 'USDKRW' },
    wti:    { name: 'WTI', code: 'CL=F' },
    vix:    { name: 'VIX', code: '공포지수' }
  };
  var METRIC_IDS = ['kospi', 'kosdaq', 'nasdaq', 'sp500', 'usdkrw', 'wti'];
  var PULSE_IDS = ['kospi', 'kosdaq', 'nasdaq', 'usdkrw', 'wti', 'vix'];

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  async function fetchJSON(url) {
    try {
      var res = await fetch(url + (url.indexOf('?') >= 0 ? '&' : '?') + 'v=' + Date.now(), { cache: 'no-cache' });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { return null; }
  }
  function dateToYMD(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  var DOW_KR = ['일', '월', '화', '수', '목', '금', '토'];
  var DOW_EN = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  function fmtKoreanDate(dateStr) {
    var d = new Date(dateStr + 'T00:00:00+09:00');
    if (isNaN(d)) return dateStr;
    return d.getFullYear() + '년 ' + (d.getMonth() + 1) + '월 ' + d.getDate() + '일 ' + DOW_KR[d.getDay()] + '요일';
  }
  function fmtMD(dateStr) {
    var d = new Date(dateStr + 'T00:00:00+09:00');
    if (isNaN(d)) return dateStr;
    return String(d.getMonth() + 1).padStart(2, '0') + '.' + String(d.getDate()).padStart(2, '0');
  }

  /* ─── 1. 마스트헤드 메타 (최신 발행일 — publishDate/manifest 실제값만) ─── */
  function renderMasthead(home, manifest) {
    var row = $('mastMetaRow');
    if (!row) return;
    var latest = manifest && manifest.length ? manifest[manifest.length - 1] : null;
    var dateStr = (home && home.publishDate) || (latest && latest.issue_date);
    if (!dateStr) { row.remove(); return; }
    var html = '<div class="mast-meta-left"><span class="mm-date">' + esc(fmtKoreanDate(dateStr)) + '</span></div>';
    html += '<div class="mast-meta-right"><span class="status-badge"><span class="dot"></span> 최근 발행 ' + esc(fmtMD(dateStr)) + '</span></div>';
    row.innerHTML = html;
  }

  /* ─── 2. 커버 스토리 (issues_manifest 최신 항목 + home.json.dailyThree) ─── */
  function renderCover(home, manifest) {
    var latest = manifest && manifest.length ? manifest[manifest.length - 1] : null;
    var headlineEl = $('csHeadline'), deckEl = $('csDeck'), flagR = $('csFlagR');
    if (latest) {
      headlineEl.textContent = latest.title;
      deckEl.textContent = latest.morning_thesis && latest.morning_thesis !== latest.title ? latest.morning_thesis : '';
      if (!deckEl.textContent) deckEl.hidden = true;
      flagR.textContent = '발행 · ' + fmtMD(latest.issue_date);
    } else if (home && home.marketTemperature && home.marketTemperature.summary) {
      headlineEl.textContent = home.marketTemperature.summary;
      flagR.textContent = home.publishDate ? '기준 · ' + fmtMD(home.publishDate) : '';
    } else {
      headlineEl.textContent = '오늘의 발행판을 준비 중입니다';
      flagR.remove();
    }

    var signals = (home && Array.isArray(home.dailyThree)) ? home.dailyThree.filter(function (s) { return s && s.status === 'ok' && s.text; }) : [];
    if (signals.length) {
      var list = $('sigList');
      list.innerHTML = signals.map(function (s, i) {
        return '<li><span class="sig-idx">' + String(i + 1).padStart(2, '0') + '</span><span class="sig-txt"><b>' + esc(s.title) + '</b> — ' + esc(s.text) + '</span></li>';
      }).join('');
      $('csSignalsBlock').hidden = false;
    }
  }

  /* ─── 3. Market Snapshot 6카드 (home.json.indicators) ─── */
  function metChgHTML(ind) {
    var dir = ind.direction === 'up' ? 'up' : ind.direction === 'down' ? 'dn' : 'flat';
    var arrow = dir === 'up' ? '▲' : dir === 'dn' ? '▼' : '·';
    var chg = typeof ind.change === 'number' ? ind.change : null;
    var chgTxt = chg == null ? '보합' : (Math.abs(chg).toFixed(ind.changeUnit === '원' || ind.changeUnit === '%p' ? 1 : 2) + (ind.changeUnit || ''));
    return '<div class="met-chg ' + dir + '">' + arrow + ' ' + chgTxt + '</div>';
  }
  function renderMetrics(home) {
    var grid = $('metricsGrid');
    var indicators = (home && Array.isArray(home.indicators)) ? home.indicators : [];
    var byId = {};
    indicators.forEach(function (i) { byId[i.id] = i; });
    var cards = METRIC_IDS.map(function (id) { return byId[id]; }).filter(function (i) { return i && i.status === 'ok'; });
    if (!cards.length) { grid.closest('.ac-card').hidden = true; return; }
    grid.innerHTML = cards.map(function (ind) {
      return '<div class="met">' +
        '<div class="met-name">' + esc(ind.name) + '</div>' +
        '<div class="met-val">' + esc(ind.displayValue) + '</div>' +
        metChgHTML(ind) +
        '</div>';
    }).join('');
    var asOf = cards[0].asOf;
    if (asOf) $('metricsAsOf').textContent = fmtMD(asOf) + ' 기준';
  }

  /* ─── 4. MOO:Q 마이크로 카드 (claims.totals — 실제 누적 검증 집계) ─── */
  function renderMooCheck(home) {
    var claims = home && home.claims;
    var totals = claims && claims.totals;
    if (!totals) return;
    var resolved = (totals.hit || 0) + (totals.miss || 0) + (totals.neutral || 0);
    if (!resolved) return;
    $('mcQ').textContent = '지금까지의 검증, 몇 번이나 맞았을까?';
    $('mcA').innerHTML = '누적 <b>' + resolved + '건</b> 검증 중 적중 <b>' + (totals.hit || 0) + '건</b> · 오차 <b>' + (totals.miss || 0) + '건</b> · 중립 <b>' + (totals.neutral || 0) + '건</b>' +
      (totals.unresolved ? ' · 판정 대기 ' + totals.unresolved + '건' : '') + '.';
    $('moocheckCard').hidden = false;
  }

  /* ─── 5. Market Pulse — data/history/*.json 최근 창(최대 20일 후보) ─── */
  async function collectHistory() {
    var today = new Date();
    var candidates = [];
    for (var i = 0; i < 24; i++) {
      var d = new Date(today);
      d.setDate(d.getDate() - i);
      candidates.push(dateToYMD(d));
    }
    var results = await Promise.allSettled(candidates.map(function (ds) {
      return fetchJSON('data/history/' + ds + '.json').then(function (data) {
        return data ? { date: ds, data: data } : null;
      });
    }));
    var rows = results
      .map(function (r) { return r.status === 'fulfilled' ? r.value : null; })
      .filter(Boolean)
      .sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    return rows;
  }

  function sparkPoints(values) {
    if (values.length < 2) return null;
    var min = Math.min.apply(null, values), max = Math.max.apply(null, values);
    var span = max - min || 1;
    var n = values.length;
    return values.map(function (v, i) {
      var x = (i / (n - 1)) * 240;
      var y = 56 - ((v - min) / span) * 52;
      return x.toFixed(1) + ',' + y.toFixed(1);
    });
  }

  function renderPulseCard(id, rows) {
    var meta = IND_META[id];
    var series = rows.map(function (r) {
      var ind = (r.data.indicators || []).find(function (x) { return x.id === id; });
      return ind && typeof ind.value === 'number' ? { date: r.date, value: ind.value, displayValue: ind.displayValue, changeUnit: ind.changeUnit } : null;
    }).filter(Boolean);
    if (series.length < 2) return null;

    var start = series[0], end = series[series.length - 1];
    var values = series.map(function (s) { return s.value; });
    var min = Math.min.apply(null, values), max = Math.max.apply(null, values);
    var pts = sparkPoints(values);
    var pctChange = start.value !== 0 ? ((end.value - start.value) / Math.abs(start.value)) * 100 : 0;
    var dir = pctChange > 0.005 ? 'up' : pctChange < -0.005 ? 'dn' : 'flat';
    var arrow = dir === 'up' ? '▲' : dir === 'dn' ? '▼' : '·';
    var absDelta = end.value - start.value;

    var pointsAttr = pts.join(' ');
    var fillPoints = pointsAttr + ' 240,60 0,60';

    return '<a class="pcard" href="/markets.html">' +
      '<div class="pc-head"><span class="pc-name">' + esc(meta.name) + '</span><span class="pc-code">' + esc(meta.code) + '</span></div>' +
      '<div class="pc-row">' +
        '<div class="pc-from-blk"><span class="pc-cap">' + fmtMD(start.date) + ' 시작</span><span class="pc-val-sm">' + esc(start.displayValue) + '</span></div>' +
        '<span class="pc-arw">→</span>' +
        '<div class="pc-to-blk"><span class="pc-cap-now">' + fmtMD(end.date) + ' 최근 <b>NOW</b></span><span class="pc-val-lg">' + esc(end.displayValue) + '</span></div>' +
      '</div>' +
      '<svg class="pc-chart" viewBox="0 0 240 60" preserveAspectRatio="none">' +
        '<polyline points="' + fillPoints + '" fill="var(--gold-tint)" stroke="none" opacity=".35"/>' +
        '<polyline points="' + pointsAttr + '" fill="none" stroke="var(--ink)" stroke-width="1.6"/>' +
      '</svg>' +
      '<div class="pc-foot">' +
        '<span class="pc-delta ' + dir + '"><span class="pc-delta-pct">' + arrow + ' ' + Math.abs(pctChange).toFixed(2) + '%</span><span class="pc-delta-abs">' + (absDelta >= 0 ? '+' : '') + absDelta.toFixed(2) + '</span></span>' +
        '<span class="pc-range">' + series.length + '일 저 ' + min.toFixed(2) + ' · 고 ' + max.toFixed(2) + '</span>' +
      '</div>' +
    '</a>';
  }

  async function renderPulse() {
    var rows = await collectHistory();
    if (rows.length < 2) {
      $('pulseEmpty').hidden = false;
      return;
    }
    var cards = PULSE_IDS.map(function (id) { return renderPulseCard(id, rows); }).filter(Boolean);
    if (!cards.length) { $('pulseEmpty').hidden = false; return; }
    $('pulseGrid').innerHTML = cards.join('');
    $('pulseSub').textContent = fmtMD(rows[0].date) + ' · ' + fmtMD(rows[rows.length - 1].date);
    $('pulseRange').textContent = '기준 · ' + rows[0].date + ' → ' + rows[rows.length - 1].date + ' (' + rows.length + '일)';
  }

  /* ─── 6. Daily / Weekly 최근 발행 목록 ─── */
  function renderDailyRecent(manifest) {
    var ul = $('dailyRecent');
    if (!manifest || !manifest.length) { ul.innerHTML = '<li class="rc-empty">발행 기록이 없습니다.</li>'; return; }
    var recent = manifest.slice(-3).reverse();
    ul.innerHTML = recent.map(function (m) {
      return '<li><span class="date">' + fmtMD(m.issue_date) + '</span><span class="title">' + esc(m.title) + '</span></li>';
    }).join('');
    $('dailyMeta').textContent = '월–토 · 매일 06:00 · 총 ' + manifest.length + '호';
  }

  async function renderWeeklyRecent() {
    var ul = $('weeklyRecent');
    var idx = await fetchJSON('data/weekly/index.json');
    var weeks = (idx && idx.weeks) || [];
    if (!weeks.length) { ul.innerHTML = '<li class="rc-empty">발행된 주간 리포트가 없습니다.</li>'; return; }
    var recent = weeks.slice(0, 3);
    ul.innerHTML = recent.map(function (w) {
      return '<li><span class="date">' + esc(w.week_id) + '</span><span class="title">' + esc(w.period_start_kst) + ' – ' + esc(w.period_end_kst) + ' · 요약 준비 중</span></li>';
    }).join('');
    $('weeklyMeta').textContent = '누적 ' + weeks.length + '건 발행';
  }

  /* ─── 7. 홈 미니 캘린더 (실제 이벤트만, 없으면 빈 상태) ─── */
  function mergeCalendarEvents(home, results) {
    var base = (home && Array.isArray(home.calendar)) ? home.calendar.slice() : [];
    var byId = {};
    (results && results.results) ? Object.keys(results.results).forEach(function (k) {
      byId[k] = results.results[k];
    }) : null;
    return base.map(function (ev) {
      var r = byId[ev.id];
      return {
        id: ev.id, time: ev.time, country: ev.country, title: ev.title,
        importance: ev.importance, resultText: r && r.resultText, resultStatus: r && r.status
      };
    }).sort(function (a, b) { return a.time < b.time ? -1 : 1; });
  }

  function renderHomeCalendar(events) {
    var today = new Date();
    var y = today.getFullYear(), m = today.getMonth();
    var todayStr = dateToYMD(today);
    $('cmhNum').textContent = String(m + 1).padStart(2, '0');
    $('cmhYear').textContent = y;
    $('cmhMo').textContent = today.toLocaleString('en-US', { month: 'long' });
    $('evMonthLabel').textContent = '· ' + (m + 1) + '월 이벤트 캘린더';

    var monthEvents = events.filter(function (e) { return e.time && e.time.slice(0, 7) === (y + '-' + String(m + 1).padStart(2, '0')); });
    var byDate = {};
    monthEvents.forEach(function (e) { (byDate[e.time] = byDate[e.time] || []).push(e); });

    var firstDow = new Date(y, m, 1).getDay();
    var daysInMonth = new Date(y, m + 1, 0).getDate();
    var cells = [];
    for (var i = 0; i < firstDow; i++) cells.push('<div class="cd cd-blank"></div>');
    for (var day = 1; day <= daysInMonth; day++) {
      var ds = y + '-' + String(m + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
      var dow = new Date(y, m, day).getDay();
      var evs = byDate[ds] || [];
      var cls = ['cd'];
      if (dow === 0) cls.push('cd-sun-cell');
      if (dow === 6) cls.push('cd-sat-cell');
      if (evs.length) cls.push('cd-has');
      if (ds < todayStr && evs.length) cls.push('cd-past');
      if (ds === todayStr) cls.push('cd-today');
      if (evs.some(function (e) { return e.importance === 'high'; })) cls.push('cd-hi');
      var inner = '<span class="cd-n">' + day + '</span>';
      if (evs.length) {
        var tagCls = evs[0].country === 'KR' ? 'cd-ev-kr' : evs[0].importance === 'high' ? 'cd-ev-hi' : 'cd-ev-us';
        inner += '<span class="cd-ev ' + tagCls + '">' + esc(evs[0].title) + '</span>';
      }
      if (ds === todayStr) inner += '<span class="cd-today-mark">TODAY</span>';
      cells.push('<div class="' + cls.join(' ') + '" data-day="' + day + '">' + inner + '</div>');
    }
    $('calDays').innerHTML = cells.join('');

    var upcoming = events.filter(function (e) { return e.time >= todayStr; }).slice(0, 5);
    var listEl = $('calList');
    if (!upcoming.length) {
      listEl.outerHTML = '<div class="cal-empty" id="calList">예정된 이벤트 데이터가 아직 없습니다.</div>';
      $('calSideRange').textContent = '';
    } else {
      listEl.innerHTML = upcoming.map(function (e) {
        var d = new Date(e.time + 'T00:00:00+09:00');
        var isToday = e.time === todayStr;
        var isHi = e.importance === 'high';
        return '<li class="cl-item' + (isToday ? ' cl-today' : '') + (isHi ? ' cl-hi' : '') + '">' +
          '<div class="cl-day"><span class="cl-d">' + d.getDate() + '</span><span class="cl-dow">' + DOW_EN[d.getDay()] + '</span></div>' +
          '<div class="cl-body">' +
            '<div class="cl-tag-row"><span class="cl-tag' + (isHi ? ' cl-t-hi' : '') + '">' + (isHi ? 'HIGH IMPACT' : esc(e.country || '매크로')) + '</span>' +
            (isToday ? '<span class="cl-status">● 오늘</span>' : '') + '</div>' +
            '<h5 class="cl-title">' + esc(e.title) + '</h5>' +
            (e.resultText ? '<p class="cl-desc">' + esc(e.resultText) + '</p>' : '') +
          '</div>' +
        '</li>';
      }).join('');
      $('calSideRange').textContent = 'D-0 → D-' + Math.max.apply(null, upcoming.map(function (e) {
        return Math.round((new Date(e.time) - new Date(todayStr)) / 86400000);
      }));
    }
  }

  /* ─── 8. 구독 폼 (기존 Worker 로직 그대로) ─── */
  var WORKER_SUBSCRIBE_URL = "https://mooconomy-subscribe.immusaeng.workers.dev";
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  function validateEmail(raw) {
    var email = (raw || '').trim().toLowerCase();
    if (!email) return { ok: false, msg: '이메일 주소를 입력해 주세요.' };
    if (!EMAIL_RE.test(email)) return { ok: false, msg: '이메일 형식을 확인해 주세요. (예: name@gmail.com)' };
    return { ok: true, email: email };
  }
  function wireSubscribeForm() {
    var form = document.querySelector('.sub-form');
    if (!form) return;
    var msgEl = $('subMsg');
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      var emailInput = form.querySelector('input[name="email"]');
      var company = form.querySelector('input[name="company"]').value;
      var btn = form.querySelector('button[type="submit"]');
      var v = validateEmail(emailInput.value);
      if (!v.ok) { msgEl.textContent = v.msg; emailInput.focus(); return; }
      var originalText = btn.textContent;
      btn.disabled = true; btn.textContent = '처리 중…';
      try {
        var res = await fetch(WORKER_SUBSCRIBE_URL + '/api/subscribe', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: v.email, company: company })
        });
        if (res.status === 200) { msgEl.textContent = '🎉 구독 신청이 완료되었습니다. 매일 아침 만나요!'; emailInput.value = ''; }
        else if (res.status === 409) msgEl.textContent = '이미 구독 중인 이메일 주소입니다. 감사합니다!';
        else if (res.status === 400) msgEl.textContent = '이메일 형식을 확인해 주세요.';
        else if (res.status === 429) msgEl.textContent = '요청이 많습니다. 잠시 후 다시 시도해 주세요.';
        else msgEl.textContent = '⚠️ 일시적 오류입니다. 잠시 후 다시 시도해 주세요.';
      } catch (err) {
        msgEl.textContent = '⚠️ 네트워크 오류입니다. 잠시 후 다시 시도해 주세요.';
      } finally {
        btn.disabled = false; btn.textContent = originalText;
      }
    });
  }

  /* ─── 실행 ─── */
  async function init() {
    wireSubscribeForm();
    var homeP = fetchJSON('data/home.json');
    var manifestP = fetchJSON('data/archive/issues_manifest.json');
    var calResultsP = fetchJSON('data/calendar_results.json');

    var home = await homeP;
    var manifest = (await manifestP) || [];

    renderMasthead(home, manifest);
    renderCover(home, manifest);
    if (home) { renderMetrics(home); renderMooCheck(home); }
    renderDailyRecent(manifest);
    if (manifest.length) $('subProofCount').textContent = manifest.length;
    renderWeeklyRecent();
    renderPulse();

    var calResults = await calResultsP;
    renderHomeCalendar(mergeCalendarEvents(home, calResults));
  }
  init();
})();
