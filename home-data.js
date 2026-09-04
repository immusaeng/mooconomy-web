/* ═══════════════════════════════════════════════════════════════
   Daily MOO:conomy — 홈페이지 데이터 배선
   v3 시안 마크업(index.html)에 실제 저장소 데이터(data/*.json)를 연결한다.
   원칙: 데이터가 없으면 요소를 숨기거나 빈 상태 문구를 쓴다.
         시안의 샘플 숫자(247호, Vol.Ⅵ, 9월 이벤트 28건 등)는 절대 쓰지 않는다.
   ═══════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  var IND_META = {
    kospi:  { name: '코스피', code: 'KS11', decimals: 2, absUnit: '' },
    kosdaq: { name: '코스닥', code: 'KQ11', decimals: 2, absUnit: '' },
    nasdaq: { name: '나스닥', code: 'IXIC', decimals: 2, absUnit: '' },
    sp500:  { name: 'S&P 500', code: 'SPX', decimals: 2, absUnit: '' },
    usdkrw: { name: '원/달러', code: 'USDKRW', decimals: 1, absUnit: '원' },
    wti:    { name: 'WTI', code: 'CL=F', decimals: 2, absUnit: '$', absPrefix: true },
    vix:    { name: 'VIX', code: '공포지수', decimals: 2, absUnit: 'pt' }
  };
  var METRIC_IDS = ['kospi', 'kosdaq', 'nasdaq', 'sp500', 'usdkrw', 'wti'];
  var PULSE_IDS = ['kospi', 'kosdaq', 'nasdaq', 'usdkrw', 'wti', 'vix'];
  /* 판정 표시 라벨 — scripts/archive_export/verdict_labels.py가 단일
     진실 공급원이다(TASK_TRACK=HOMEPAGE_DATA_REFRESH_AND_CONSOLE_HYGIENE
     §C 표준: MATCH=적중/PARTIAL_MATCH=부분 적중/MISMATCH=불일치/
     NEUTRAL=중립/PENDING=판정 대기). invalidated/error도 questions
     아카이브(export.py의 _VERDICT_MAP)와 동일하게 PENDING으로 묶는다 —
     이전에는 홈 카드만 "무효"/"오류"로 따로 표시해 아카이브의 "판단보류"
     문구와 어긋났었다. 이 객체를 고칠 때는 verdict_labels.py도 함께
     고칠 것 — tests/test_verdict_label_consistency.py가 어긋나면 실패한다. */
  var VERDICT_LABEL = { hit: '적중', miss: '불일치', neutral: '중립', unresolved: '판정 대기', invalidated: '판정 대기', error: '판정 대기' };
  function fmtNum(v) {
    return typeof v === 'number' ? v.toLocaleString('en-US', { maximumFractionDigits: 2 }) : v;
  }

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
  var DOW_KO = ['일', '월', '화', '수', '목', '금', '토'];
  var MONTH_KO = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월'];
  var COUNTRY_KO = {
    US: '미국', KR: '한국', EU: '유로존', EUROZONE: '유로존', JP: '일본',
    CN: '중국', UK: '영국', GB: '영국',
  };
  function countryLabel(code) { return (code && COUNTRY_KO[code]) || code; }
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
      if (headlineEl.tagName === 'A') headlineEl.href = latest.public_path || ('/issues/' + latest.issue_date + '.html');
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

  /* ─── 4. MOO:Q → CHECK 카드
     표시 순서: 헤더(정적) → 최신 검증 질문 전문 → 판정 상태 → 기준값→결과값
     → 누적 적중/불일치/중립/판정 대기 → /questions/ 링크.
     "최신 검증 질문"은 이미 판정이 끝난 가장 최근 claim(previousClaims[0]) —
     오늘자 claim(todayClaims[0])은 아직 미판정이라 여기 쓰지 않는다.
     질문 문장은 claimText를 그대로 쓰고 축약·재작성하지 않는다. ─── */
  function renderMooCheck(home) {
    var claims = home && home.claims;
    if (!claims) return;
    var latest = (claims.previousClaims && claims.previousClaims[0]) || null;
    if (!latest || !latest.claimText) return;

    $('mcQ').textContent = latest.claimText;

    var verdict = (latest.resolution && latest.resolution.verdict) || latest.status;
    // 알 수 없는 verdict 값은 임의로 원문 그대로 보여주지 않는다(§C) —
    // 빌드 단계(publish_mooq_archive.py)가 이미 걸러내지만, 클라이언트
    // 쪽도 방어적으로 인식 못 하는 값이면 배지를 그냥 비워 둔다.
    if (verdict && VERDICT_LABEL[verdict]) {
      var vEl = $('mcVerdict');
      vEl.textContent = VERDICT_LABEL[verdict];
      vEl.className = 'mc-verdict' + (verdict === 'hit' ? ' hit' : verdict === 'miss' ? ' miss' : '');
    }

    var res = latest.resolution;
    if (res && typeof res.startValue === 'number' && typeof res.endValue === 'number') {
      var mname = (IND_META[res.metricId] && IND_META[res.metricId].name) || res.metricId;
      $('mcValues').textContent = mname + ' ' + fmtNum(res.startValue) + ' → ' + fmtNum(res.endValue);
    }

    var totals = claims.totals;
    if (totals) {
      var resolved = (totals.hit || 0) + (totals.miss || 0) + (totals.neutral || 0);
      $('mcStats').innerHTML = '누적 <b>' + resolved + '건</b> 검증 · 적중 <b>' + (totals.hit || 0) + '</b> · 불일치 <b>' + (totals.miss || 0) + '</b> · 중립 <b>' + (totals.neutral || 0) + '</b>' +
        (totals.unresolved ? ' · 판정 대기 <b>' + totals.unresolved + '</b>' : '') + '.';
    }

    $('moocheckCard').hidden = false;
  }

  /* ─── 5. Market Pulse — data/history/*.json 최근 창(최대 20일 후보) ─── */
  function ymdMinus(dateStr, days) {
    var d = new Date(dateStr + 'T00:00:00+09:00');
    d.setDate(d.getDate() - days);
    return dateToYMD(d);
  }

  /* data/history/index.json(build_history_index.py가 daily.yml 안에서
     data/history/*.json과 같은 커밋으로 함께 생성) — 실제 존재하는 날짜만
     담긴 정렬된 목록. 이게 있으면 휴장일 파일을 추측 fetch하지 않는다.
     index 자체가 없거나 파싱 실패하면 null을 반환해 아래 두 함수가 전부
     "날짜별로 직접 fetch해 보고 404는 무시" 하던 예전 방식으로 안전하게
     되돌아간다(무한 재시도 없음 — 한 번의 fetch 시도로 끝나는 건 그대로). */
  var _historyIndexPromise = null;
  function fetchHistoryIndex() {
    if (!_historyIndexPromise) {
      _historyIndexPromise = fetchJSON('data/history/index.json').then(function (idx) {
        if (!idx || !Array.isArray(idx.dates)) return null;
        var set = {};
        idx.dates.forEach(function (d) { set[d] = true; });
        return set;
      }).catch(function () { return null; });
    }
    return _historyIndexPromise;
  }

  /* startTarget/endTarget이 휴장일이면 그 날짜 이전(과거 방향으로만)
     가장 가까운 유효 관측값을 찾는다 — 최대 7일 역탐색(장기 연휴 대비),
     기간 자체를 늘리는 게 아니라 경계값의 fallback일 뿐이다. 선택 결과
     (어느 날짜가 뽑히는지)는 index 유무와 무관하게 동일 — index는 그
     선택에 이르는 과정에서 존재하지 않는 날짜의 fetch만 건너뛴다. */
  async function fetchNearestOnOrBefore(dateStr, maxLookback) {
    var indexSet = await fetchHistoryIndex();
    for (var i = 0; i <= maxLookback; i++) {
      var ds = ymdMinus(dateStr, i);
      if (indexSet && !indexSet[ds]) continue;
      var data = await fetchJSON('data/history/' + ds + '.json');
      if (data) return { date: ds, data: data };
    }
    return null;
  }

  async function fetchHistoryRange(fromDate, toDate) {
    var dates = [];
    var cur = new Date(fromDate + 'T00:00:00+09:00');
    var end = new Date(toDate + 'T00:00:00+09:00');
    while (cur <= end) {
      dates.push(dateToYMD(cur));
      cur.setDate(cur.getDate() + 1);
    }
    var indexSet = await fetchHistoryIndex();
    var candidates = indexSet ? dates.filter(function (d) { return indexSet[d]; }) : dates;
    var results = await Promise.allSettled(candidates.map(function (ds) {
      return fetchJSON('data/history/' + ds + '.json').then(function (data) {
        return data ? { date: ds, data: data } : null;
      });
    }));
    return results
      .map(function (r) { return r.status === 'fulfilled' ? r.value : null; })
      .filter(Boolean)
      .sort(function (a, b) { return a.date < b.date ? -1 : 1; });
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

  /* Market Pulse 카드 — 대표 숫자는 전부 같은 두 값(14일 시작/종료)에서만
     계산한다(일간 변동값을 대표로 쓰지 않는다). 화살표·절대차·등락률은
     전부 같은 dir 하나에서 파생되므로 부호가 어긋날 수 없다 — 그래도
     방어적으로 한 번 더 assert해서, 로직이 나중에 바뀌어도 조용히
     틀린 화면이 나가지 않게 한다(콘솔 경고 + 해당 카드 렌더 중단). */
  // history 스냅샷의 indicator 객체엔 displayValue가 없다(그건
  // home.json 전용 필드) — raw value를 지표별 decimals/단위 정책으로
  // 직접 포맷한다(같은 정책을 pc-value-current/-start 양쪽에 동일 적용).
  function fmtIndicatorValue(value, meta) {
    var decimals = meta.decimals != null ? meta.decimals : 2;
    var text = value.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    var unit = meta.absUnit || '';
    if (unit) text = meta.absPrefix ? unit + text : text + unit;
    return text;
  }

  /* 2026-09-04(TASK_ID=HOMEPAGE_NARRATIVE_PULSE_VALUES_AND_CALENDAR_KO §4-7)
     정보 위계: 시작 지수 → 현재 지수 → 방향 → 절대/등락률 → sparkline →
     날짜. 계산식은 그대로(§7): absoluteChange = current - start,
     percentChange = ((current/start)-1)*100 — 바뀌는 건 어떤 숫자를
     크고 굵게 보여주느냐일 뿐, 계산 로직은 위 renderPulse()가 이미
     검증한 그대로 재사용한다. */
  function renderPulseCard(id, rows) {
    var meta = IND_META[id];
    var series = rows.map(function (r) {
      var ind = (r.data.indicators || []).find(function (x) { return x.id === id; });
      return ind && typeof ind.value === 'number' ? { date: r.date, value: ind.value } : null;
    }).filter(Boolean);
    if (series.length < 2) return null;

    var start = series[0], end = series[series.length - 1];
    var values = series.map(function (s) { return s.value; });
    var min = Math.min.apply(null, values), max = Math.max.apply(null, values);
    var pts = sparkPoints(values);

    var absDelta = end.value - start.value;
    var pctChange = start.value !== 0 ? ((end.value / start.value) - 1) * 100 : 0;
    var dir = absDelta > 0 ? 'up' : absDelta < 0 ? 'dn' : 'flat';
    var arrow = dir === 'up' ? '▲' : dir === 'dn' ? '▼' : '·';

    // sign(absolute) == sign(percent) == 화살표/색 방향 — 하나라도 어긋나면
    // 이 카드는 그리지 않는다(틀린 방향을 보여주느니 숨기는 게 낫다).
    var signsConsistent = (absDelta === 0 && Math.abs(pctChange) < 1e-9) ||
      (Math.sign(absDelta) === Math.sign(pctChange));
    if (!signsConsistent) {
      if (typeof console !== 'undefined') {
        console.warn('[MarketPulse] sign mismatch for', id, { absDelta: absDelta, pctChange: pctChange });
      }
      return null;
    }

    var decimals = meta.decimals != null ? meta.decimals : 2;
    var absUnit = meta.absUnit || '';
    var absText = Math.abs(absDelta).toFixed(decimals);
    if (meta.absPrefix) absText = absUnit + absText; else if (absUnit) absText = absText + absUnit;

    var pointsAttr = pts.join(' ');
    var fillPoints = pointsAttr + ' 240,60 0,60';

    // 목표 기간(발행일 기준 14일 전 → 발행일)과 실제 데이터 날짜(휴장 시
    // 가장 가까운 이전 거래일)가 다를 수 있다 — 카드에는 실제 값이 쓰인
    // 날짜만 표시하고, 목표 기간은 섹션 상단 pulseRange가 이미 별도로
    // 안내한다(§6 날짜 정책 — 여기서 다시 병기해 중복하지 않는다).
    // 2026-09-04(TASK_ID=HOMEPAGE_FINAL_VISUAL_CLEANUP §2)
    // 카드 헤더 우측은 원래 KS11/CL=F 같은 원자재·지수 심볼이었다 —
    // 이 카드에서 가장 중요한 정보(등락 기호+절대변화+변화율)를 대신
    // 그 자리로 올리고, 현재값 아래 있던 같은 정보(중복)는 지운다.
    var changeText = arrow + ' ' + esc(absText) + ' · ' + (pctChange < 0 ? '−' : '+') + Math.abs(pctChange).toFixed(2) + '%';
    return '<a class="pcard pulse-card" href="/markets.html">' +
      '<header class="pc-head pulse-card-head"><h3 class="pc-name">' + esc(meta.name) + '</h3><span class="pc-change-header ' + dir + '">' + changeText + '</span></header>' +
      '<div class="pulse-flow">' +
        '<div class="pulse-point pulse-start">' +
          '<span class="pulse-date">' + fmtMD(start.date) + '</span>' +
          '<div class="pulse-value-line"><span class="pulse-label">시작</span><strong class="pulse-value">' + esc(fmtIndicatorValue(start.value, meta)) + '</strong></div>' +
        '</div>' +
        '<div class="pulse-arrow" aria-hidden="true">→</div>' +
        '<div class="pulse-point pulse-current">' +
          '<span class="pulse-date">' + fmtMD(end.date) + '</span>' +
          '<div class="pulse-value-line"><span class="pulse-label">현재</span><strong class="pulse-value">' + esc(fmtIndicatorValue(end.value, meta)) + '</strong></div>' +
        '</div>' +
      '</div>' +
      '<svg class="pc-chart pulse-chart" viewBox="0 0 240 60" preserveAspectRatio="none">' +
        '<polyline points="' + fillPoints + '" fill="var(--gold-tint)" stroke="none" opacity=".35"/>' +
        '<polyline points="' + pointsAttr + '" fill="none" stroke="var(--ink)" stroke-width="1.6"/>' +
      '</svg>' +
      '<div class="pc-foot">' +
        '<span class="pc-range">' + series.length + '일 저 ' + min.toFixed(2) + ' · 고 ' + max.toFixed(2) + '</span>' +
      '</div>' +
    '</a>';
  }

  /* Market Pulse = 발행일 기준 정확히 최근 14일 비교 (장기 누적 아님).
     endTarget=publishDate, startTarget=publishDate-14일. 경계일이 휴장일이면
     그 이전 가장 가까운 유효값으로 대체하되, 비교 구간 자체를 늘리지 않는다.
     14일 구간에 관측치가 부족하면 부족 상태를 명시한다(임의 확장 금지). */
  async function renderPulse(home) {
    var endTarget = home && home.publishDate;
    if (!endTarget) {
      $('pulseEmpty').hidden = false;
      $('pulseEmpty').textContent = '발행일 정보가 없어 Market Pulse를 표시할 수 없습니다.';
      return;
    }
    var startTarget = ymdMinus(endTarget, 14);

    var endObs = await fetchNearestOnOrBefore(endTarget, 7);
    var startObs = await fetchNearestOnOrBefore(startTarget, 7);
    if (!endObs || !startObs) {
      $('pulseEmpty').hidden = false;
      $('pulseEmpty').textContent = '최근 14일 구간의 시장 기록이 부족해 Market Pulse를 표시할 수 없습니다.';
      return;
    }

    var rows = await fetchHistoryRange(startObs.date, endObs.date);
    if (rows.length < 2) {
      $('pulseEmpty').hidden = false;
      $('pulseEmpty').textContent = '최근 14일 구간의 시장 기록이 부족해 Market Pulse를 표시할 수 없습니다.';
      return;
    }

    var cards = PULSE_IDS.map(function (id) { return renderPulseCard(id, rows); }).filter(Boolean);
    if (!cards.length) {
      $('pulseEmpty').hidden = false;
      $('pulseEmpty').textContent = '최근 14일 구간의 시장 기록이 부족해 Market Pulse를 표시할 수 없습니다.';
      return;
    }
    $('pulseGrid').innerHTML = cards.join('');
    $('pulseSub').textContent = '발행일 기준 최근 14일';
    $('pulseRange').textContent = '목표 기간 ' + startTarget + ' → ' + endTarget +
      (startObs.date !== startTarget || endObs.date !== endTarget
        ? ' · 표시 기간 ' + startObs.date + ' → ' + endObs.date
        : '');
  }

  /* ─── 6. Daily / Weekly 최근 발행 목록 ─── */
  function renderDailyRecent(manifest) {
    var ul = $('dailyRecent');
    if (!manifest || !manifest.length) { ul.innerHTML = '<li class="rc-empty">발행 기록이 없습니다.</li>'; return; }
    var recent = manifest.slice(-3).reverse();
    ul.innerHTML = recent.map(function (m) {
      var href = m.public_path || ('/issues/' + m.issue_date + '.html');
      return '<li><a href="' + esc(href) + '"><span class="date">' + fmtMD(m.issue_date) + '</span><span class="title">' + esc(m.title) + '</span></a></li>';
    }).join('');
    $('dailyMeta').textContent = '화–토 · 오전 7시 도착 · 총 ' + manifest.length + '호';

    var monthUl = $('monthlyRecent');
    if (monthUl) {
      var byMonth = {};
      manifest.forEach(function (m) { var ym = m.issue_date.slice(0, 7); byMonth[ym] = (byMonth[ym] || 0) + 1; });
      var months = Object.keys(byMonth).sort().reverse();
      monthUl.innerHTML = months.map(function (ym) {
        return '<li><span class="date">' + ym + '</span><span class="title">' + byMonth[ym] + '건 발행</span></li>';
      }).join('') || '<li class="rc-empty">월별 기록이 없습니다.</li>';
    }
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
  /* data/calendar_views/home.json(통합 캘린더 파이프라인이 만드는 "오늘부터
     14일" view)를 기존 렌더 함수가 쓰는 모양으로 바꾼다. fresh/partial이
     아니거나 이벤트가 없으면 null — 호출부가 기존 home.json.calendar
     fallback으로 넘어간다. 샘플 데이터는 이 경로에 절대 오지 않는다
     (build_calendar.py가 fixture 모드에선 data/ 밖에만 쓴다). */
  function eventsFromCanonicalView(view) {
    if (!view || !view.freshness) return null;
    var status = view.freshness.status;
    if (status !== 'fresh' && status !== 'partial') return null;
    var events = Array.isArray(view.events) ? view.events : [];
    if (!events.length) return null;
    return events.map(function (e) {
      return {
        id: e.id, time: e.scheduledDate, country: e.country,
        title: e.titleKo || e.title, originalTitle: e.originalTitle || e.title,
        importance: e.importance === 'unknown' ? null : e.importance,
        resultText: null, resultStatus: e.status,
      };
    });
  }

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
    $('cmhMo').textContent = MONTH_KO[m];
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
        var evTitleAttr = (evs[0].originalTitle && evs[0].originalTitle !== evs[0].title) ? ' title="원문: ' + esc(evs[0].originalTitle) + '"' : '';
        inner += '<span class="cd-ev ' + tagCls + '"' + evTitleAttr + ' lang="ko">' + esc(evs[0].title) + '</span>';
      }
      if (ds === todayStr) inner += '<span class="cd-today-mark">오늘</span>';
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
          '<div class="cl-day"><span class="cl-d">' + d.getDate() + '</span><span class="cl-dow">' + DOW_KO[d.getDay()] + '</span></div>' +
          '<div class="cl-body">' +
            '<div class="cl-tag-row"><span class="cl-tag' + (isHi ? ' cl-t-hi' : '') + '">' + (isHi ? '주요' : esc(countryLabel(e.country) || '매크로')) + '</span>' +
            (isToday ? '<span class="cl-status">● 오늘</span>' : '') + '</div>' +
            '<h5 class="cl-title" lang="ko">' + esc(e.title) + '</h5>' +
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
    var calViewP = fetchJSON('data/calendar_views/home.json');

    var home = await homeP;
    var manifest = (await manifestP) || [];

    renderMasthead(home, manifest);
    renderCover(home, manifest);
    if (home) { renderMetrics(home); renderMooCheck(home); }
    renderDailyRecent(manifest);
    if (manifest.length) $('subProofCount').textContent = manifest.length;
    renderWeeklyRecent();
    renderPulse(home);

    var calResults = await calResultsP;
    var calView = await calViewP;
    var calEvents = eventsFromCanonicalView(calView) || mergeCalendarEvents(home, calResults);
    renderHomeCalendar(calEvents);
  }
  init();
})();
