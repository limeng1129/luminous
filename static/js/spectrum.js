/* 光谱：把照片压成色条，横向划过预览，可切换三种排法 */
(function () {
  var S = window.SPEC || {};
  var items = S.items || [], orders = S.orders || {};
  if (!items.length) return;

  var band = document.getElementById('band');
  var pImg = document.getElementById('pImg');
  var hint = document.getElementById('hint');
  var meta = document.getElementById('meta');
  var pTitle = document.getElementById('pTitle'), pSub = document.getElementById('pSub');
  var axL = document.getElementById('axL'), axR = document.getElementById('axR');

  var AXIS = {
    time: ['最早', '最近'],
    warm: ['最冷', '最暖'],
    light: ['最暗', '最亮']
  };

  // 每张照片一根色条
  var bars = items.map(function (it) {
    var el = document.createElement('i');
    el.style.background = it.rgb;
    band.appendChild(el);
    return el;
  });

  var current = 'time', layout = [], cur = -1;

  function place(sort) {
    var order = orders[sort] || orders.time;
    var n = order.length, w = 100 / n;
    layout = new Array(n);
    order.forEach(function (itemIdx, pos) {
      var el = bars[itemIdx];
      // 加一点点重叠，避免亚像素缝隙
      el.style.left = (pos * w) + '%';
      el.style.width = (w + 0.06) + '%';
      el.style.transitionDelay = Math.min(pos * 7, 260) + 'ms';
      layout[pos] = itemIdx;
    });
    axL.textContent = AXIS[sort][0];
    axR.textContent = AXIS[sort][1];
  }

  function show(pos) {
    if (pos < 0 || pos >= layout.length || pos === cur) return;
    if (cur >= 0 && bars[layout[cur]]) bars[layout[cur]].classList.remove('hot');
    cur = pos;
    var it = items[layout[pos]];
    bars[layout[pos]].classList.add('hot');
    pImg.src = it.src;
    pImg.alt = it.title || '';
    pImg.classList.add('on');
    hint.classList.add('off');
    pTitle.textContent = it.title || '';
    pSub.textContent = it.subtitle || '';
    meta.classList.add('on');
  }

  function posFromX(clientX) {
    var r = band.getBoundingClientRect();
    var t = (clientX - r.left) / r.width;
    return Math.max(0, Math.min(layout.length - 1, Math.floor(t * layout.length)));
  }

  band.addEventListener('mousemove', function (e) { show(posFromX(e.clientX)); });
  band.addEventListener('touchstart', function (e) {
    show(posFromX(e.touches[0].clientX));
  }, { passive: true });
  band.addEventListener('touchmove', function (e) {
    show(posFromX(e.touches[0].clientX));
  }, { passive: true });

  // 点开进全屏看图（复用看图器的数据顺序）
  band.addEventListener('click', function (e) {
    var pos = posFromX(e.clientX);
    if (pos < 0) return;
    var it = items[layout[pos]];
    var idx = (window.PHOTOS || []).findIndex(function (p) { return p.id === it.id; });
    if (idx >= 0 && window.openViewer) window.openViewer(idx);
  });

  // 键盘：左右移动，回车放大
  band.tabIndex = 0;
  band.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight') { show(Math.min(layout.length - 1, cur + 1)); e.preventDefault(); }
    else if (e.key === 'ArrowLeft') { show(Math.max(0, cur - 1)); e.preventDefault(); }
    else if (e.key === 'Enter' && cur >= 0) {
      var it = items[layout[cur]];
      var idx = (window.PHOTOS || []).findIndex(function (p) { return p.id === it.id; });
      if (idx >= 0 && window.openViewer) window.openViewer(idx);
    }
  });

  // 切换排法
  document.querySelectorAll('.spec-sorts button').forEach(function (b) {
    b.addEventListener('click', function () {
      if (b.dataset.sort === current) return;
      current = b.dataset.sort;
      document.querySelectorAll('.spec-sorts button').forEach(function (x) {
        x.classList.toggle('on', x === b);
      });
      place(current);
    });
  });

  // 补算颜色
  var an = document.getElementById('analyze');
  if (an) an.addEventListener('click', function () {
    an.disabled = true; an.textContent = '分析中…';
    fetch('/api/spectrum/analyze', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.error) throw new Error(d.error);
        window.toast && toast('已分析 ' + d.analyzed + ' 张' + (d.remaining ? '，还剩 ' + d.remaining : ''));
        setTimeout(function () { location.reload(); }, 900);
      })
      .catch(function (err) {
        window.toast && toast(err.message);
        an.disabled = false; an.textContent = '现在分析';
      });
  });

  place('time');
})();
