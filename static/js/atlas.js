/* 地图：把走过的地方画成一片光点，按时间连成一条路径。
   用等距圆柱投影，自动缩放到所有点的范围——只去过国内就自动放大到国内。 */
(function () {
  var A = window.ATLAS || {};
  var spots = A.spots || [], anchors = A.anchors || [];
  if (!spots.length) return;

  var svg = document.getElementById('atlas');
  var card = document.getElementById('card');
  var NS = 'http://www.w3.org/2000/svg';

  // 视野：包住所有自己的点，留出边距；太小的范围也保证一个最小视野
  var lats = spots.map(function (s) { return s.lat; });
  var lngs = spots.map(function (s) { return s.lng; });
  var minLat = Math.min.apply(null, lats), maxLat = Math.max.apply(null, lats);
  var minLng = Math.min.apply(null, lngs), maxLng = Math.max.apply(null, lngs);
  var padLat = Math.max((maxLat - minLat) * 0.28, 6);
  var padLng = Math.max((maxLng - minLng) * 0.28, 8);
  minLat -= padLat; maxLat += padLat; minLng -= padLng; maxLng += padLng;
  minLat = Math.max(-85, minLat); maxLat = Math.min(85, maxLat);
  minLng = Math.max(-180, minLng); maxLng = Math.min(180, maxLng);

  var W = 1000, H = 560;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

  function X(lng) { return (lng - minLng) / (maxLng - minLng) * W; }
  function Y(lat) { return (maxLat - lat) / (maxLat - minLat) * H; }

  function el(tag, attrs) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }

  // ── 经纬网格 ──────────────────────────────────────
  var g = el('g', { class: 'grid' });
  var stepLat = (maxLat - minLat) > 60 ? 20 : (maxLat - minLat) > 25 ? 10 : 5;
  var stepLng = (maxLng - minLng) > 90 ? 30 : (maxLng - minLng) > 40 ? 15 : 10;
  for (var la = Math.ceil(minLat / stepLat) * stepLat; la <= maxLat; la += stepLat) {
    g.appendChild(el('line', { x1: 0, y1: Y(la), x2: W, y2: Y(la) }));
    var t = el('text', { x: 6, y: Y(la) - 5, class: 'gridlab' });
    t.textContent = la + '°';
    g.appendChild(t);
  }
  for (var ln = Math.ceil(minLng / stepLng) * stepLng; ln <= maxLng; ln += stepLng) {
    g.appendChild(el('line', { x1: X(ln), y1: 0, x2: X(ln), y2: H }));
  }
  svg.appendChild(g);

  // ── 参照城市（淡） ────────────────────────────────
  var ga = el('g', { class: 'anchors' });
  anchors.forEach(function (a) {
    if (a.lat < minLat || a.lat > maxLat || a.lng < minLng || a.lng > maxLng) return;
    ga.appendChild(el('circle', { cx: X(a.lng), cy: Y(a.lat), r: 1.8 }));
    var t = el('text', { x: X(a.lng) + 7, y: Y(a.lat) + 3.5 });
    t.textContent = a.name;
    ga.appendChild(t);
  });
  svg.appendChild(ga);

  // ── 光点 ─────────────────────────────────────────
  var maxCount = Math.max.apply(null, spots.map(function (s) { return s.count; }));

  // 先算好每个点的屏幕坐标和半径
  spots.forEach(function (s) {
    s._r = 4 + Math.sqrt(s.count / maxCount) * 9;
    s._x = X(s.lng); s._y = Y(s.lat);
  });

  // 挨得太近的点互相推开一点。像大理和洱海只差二十公里，
  // 在这个尺度上会完全重合，推开后两个都点得到。
  for (var pass = 0; pass < 60; pass++) {
    var moved = false;
    for (var i = 0; i < spots.length; i++) {
      for (var j = i + 1; j < spots.length; j++) {
        var a = spots[i], bb = spots[j];
        var dx = bb._x - a._x, dy = bb._y - a._y;
        var d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        var want = a._r + bb._r + 6;
        if (d < want) {
          var push = (want - d) / 2;
          var ux = dx / d, uy = dy / d;
          a._x -= ux * push; a._y -= uy * push;
          bb._x += ux * push; bb._y += uy * push;
          moved = true;
        }
      }
    }
    if (!moved) break;
  }

  var gs = el('g', { class: 'spots' });
  spots.slice().reverse().forEach(function (s, idx) {
    var r = s._r;
    var grp = el('g', { class: 'spot', tabindex: 0, role: 'button' });
    grp.setAttribute('aria-label', s.name + '，' + s.count + ' 条记录');
    grp.appendChild(el('circle', { cx: s._x, cy: s._y, r: r + 9, class: 'halo' }));
    grp.appendChild(el('circle', { cx: s._x, cy: s._y, r: r, class: 'core' }));
    var t = el('text', { x: s._x, y: s._y - r - 8, class: 'name' });
    s._label = t;
    t.textContent = s.name;
    grp.appendChild(t);
    grp.addEventListener('click', function () { openCard(s); });
    grp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCard(s); }
    });
    grp.style.animationDelay = (idx * 45) + 'ms';
    gs.appendChild(grp);
  });
  // ── 路径：按第一次去的时间把点连起来 ──────────────
  var ordered = spots.slice().filter(function (s) { return s.first; })
    .sort(function (a, b) { return a.first < b.first ? -1 : 1; });
  if (ordered.length > 1) {
    var d = ordered.map(function (s, i) {
      return (i ? 'L' : 'M') + s._x.toFixed(1) + ' ' + s._y.toFixed(1);
    }).join(' ');
    var path = el('path', { d: d, class: 'trail' });
    svg.insertBefore(path, gs.nextSibling || null);
    var len = path.getTotalLength ? path.getTotalLength() : 0;
    if (len && !matchMedia('(prefers-reduced-motion:reduce)').matches) {
      path.style.strokeDasharray = len;
      path.style.strokeDashoffset = len;
      path.getBoundingClientRect();           // 触发重排，动画才会跑
      path.style.transition = 'stroke-dashoffset 2.6s cubic-bezier(.16,1,.3,1) .3s';
      path.style.strokeDashoffset = 0;
    }
  }


  svg.appendChild(gs);


  // ── 标签避让 ─────────────────────────────────────
  // 密集区域的地名会糊成一团。按重要度依次放置：
  // 先试点上方，再试下方，都挤不下就先藏起来，鼠标悬停时再显示。
  requestAnimationFrame(function () {
    var placed = [];
    var hit = function (r) {
      return placed.some(function (p) {
        return !(r.x + r.width < p.x || r.x > p.x + p.width ||
                 r.y + r.height < p.y || r.y > p.y + p.height);
      });
    };
    spots.forEach(function (s) {
      var t = s._label;
      if (!t) return;
      var box;
      try { box = t.getBBox(); } catch (e) { return; }
      if (!hit(box)) { placed.push(box); return; }
      t.setAttribute('y', s._y + s._r + 15);        // 换到下方
      try { box = t.getBBox(); } catch (e) { return; }
      if (!hit(box)) { placed.push(box); return; }
      t.classList.add('shy');                        // 还是挤，先藏
    });
  });

  // ── 点开看这个地方 ────────────────────────────────
  function openCard(s) {
    document.getElementById('cardName').textContent = s.name;
    var bits = [];
    if (s.posts.length) bits.push(s.posts.length + ' 篇文章');
    if (s.photos.length) bits.push(s.photos.length + ' 张照片');
    document.getElementById('cardCount').textContent = bits.join(' · ');

    var pw = document.getElementById('cardPosts');
    pw.innerHTML = s.posts.map(function (p) {
      return '<a href="/p/' + p.slug + '"><b>' + p.title + '</b><time>' + p.date + '</time></a>';
    }).join('');

    var sw = document.getElementById('cardShots');
    sw.innerHTML = '';
    window.PHOTOS = s.photos;
    s.photos.forEach(function (ph, i) {
      var b = document.createElement('button');
      b.className = 'mini';
      b.innerHTML = '<img src="' + ph.src + '" alt="' + (ph.title || '') + '" loading="lazy">';
      b.addEventListener('click', function () {
        if (window.openViewer) window.openViewer(i);
      });
      sw.appendChild(b);
    });
    card.classList.add('open');
  }

  document.getElementById('cardX').addEventListener('click', function () {
    card.classList.remove('open');
  });
  addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && card.classList.contains('open')) card.classList.remove('open');
  });
})();
