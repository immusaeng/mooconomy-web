/* ═══════════════════════════════════════════════════════════════
   Daily MOO:conomy — Homepage v3 (script)
   - 실시간 티커: ticker.json 로드 후 무한 스크롤
   - 스크롤 시 상단 nav 활성 섹션 표시
   실패 시에도 콘텐츠·내비게이션은 그대로 사용 가능해야 하므로
   가짜 수치를 채우지 않는다 — 빈 상태 문구로 대체.
   ═══════════════════════════════════════════════════════════════ */

/* ─── 1. Ticker ─── */
function renderTicker(data) {
  var bar = document.querySelector('.ticker-bar');
  var inner = document.getElementById('tickerInner');
  if (!inner) return;
  var items = (data && data.items) || [];
  if (!items.length) {
    if (bar) bar.classList.add('ticker-empty');
    inner.innerHTML = '<span class="ti-item ti-empty">지표를 불러오지 못했습니다</span>';
    return;
  }
  var html = items.map(function (it) {
    var chg = typeof it.change === 'number' ? it.change : parseFloat(it.change);
    var hasChg = !isNaN(chg);
    var cls = !hasChg || chg === 0 ? 'flat' : (chg > 0 ? 'up' : 'dn');
    var arrow = !hasChg || chg === 0 ? '·' : (chg > 0 ? '▲' : '▼');
    var chgTxt = hasChg ? Math.abs(chg).toFixed(2) + '%' : '—';
    return '<span class="ti-item">' +
      '<span class="ti-name">' + it.name + '</span>' +
      '<span class="ti-val">' + it.value + '</span>' +
      '<span class="ti-chg ' + cls + '">' + arrow + ' ' + chgTxt + '</span>' +
      '</span><span class="ti-sep">·</span>';
  }).join('');
  inner.innerHTML = html + html;
}

async function loadTicker() {
  try {
    var base = document.body.getAttribute('data-root') || '';
    var res = await fetch(base + 'ticker.json?v=' + Date.now(), { cache: 'no-cache' });
    if (!res.ok) throw new Error('ticker fetch fail');
    var data = await res.json();
    renderTicker(data);
  } catch (e) {
    renderTicker({ items: [] });
  }
}
loadTicker();

/* ─── 2. 스크롤 시 상단 nav 활성화 (홈 전용, 앵커 nav가 있을 때만) ─── */
var navLinks = document.querySelectorAll('.topnav-list a[href^="#"]');
if (navLinks.length) {
  var sections = Array.prototype.map.call(navLinks, function (a) {
    return document.querySelector(a.getAttribute('href'));
  }).filter(Boolean);
  var updateActiveNav = function () {
    var y = window.scrollY + 120;
    var idx = 0;
    sections.forEach(function (s, i) { if (s.offsetTop <= y) idx = i; });
    navLinks.forEach(function (a) { a.classList.remove('active'); });
    if (navLinks[idx]) navLinks[idx].classList.add('active');
  };
  window.addEventListener('scroll', updateActiveNav, { passive: true });
}
