/* 全屏看图：切换、缩放、拖拽、触屏手势 */
(function () {
  var photos = window.PHOTOS || [];
  if (!photos.length) return;

  var v = document.getElementById('viewer'), img = document.getElementById('vImg');
  var i = 0, zoom = 1, ox = 0, oy = 0, dragging = false, sx = 0, sy = 0;

  function apply() {
    img.style.transform = 'translate(' + ox + 'px,' + oy + 'px) scale(' + zoom + ')';
    img.classList.toggle('zoomed', zoom > 1);
    v.classList.toggle('zoom-on', zoom > 1);
  }
  function reset() { zoom = 1; ox = oy = 0; apply(); }

  function show(n) {
    i = (n + photos.length) % photos.length;
    var p = photos[i];
    reset();
    img.src = p.src; img.alt = p.title || '';
    document.getElementById('vTitle').textContent = p.title || '';
    document.getElementById('vSub').textContent = p.subtitle || '';
    document.getElementById('vCount').textContent = (i + 1) + ' / ' + photos.length;
  }
  function open(n) {
    show(n); v.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function close() {
    v.classList.remove('open'); document.body.style.overflow = ''; reset();
  }

  document.querySelectorAll('.shot').forEach(function (el) {
    el.addEventListener('click', function () { open(+el.dataset.i); });
  });
  document.getElementById('vClose').onclick = close;
  document.getElementById('vPrev').onclick = function (e) { e.stopPropagation(); show(i - 1); };
  document.getElementById('vNext').onclick = function (e) { e.stopPropagation(); show(i + 1); };

  // 点图放大 / 还原
  img.addEventListener('click', function (e) {
    e.stopPropagation();
    if (zoom > 1) { reset(); return; }
    var r = img.getBoundingClientRect();
    zoom = 2.4;
    ox = (r.left + r.width / 2 - e.clientX) * (zoom - 1);
    oy = (r.top + r.height / 2 - e.clientY) * (zoom - 1);
    apply();
  });

  // 放大后可拖动
  img.addEventListener('mousedown', function (e) {
    if (zoom <= 1) return;
    dragging = true; sx = e.clientX - ox; sy = e.clientY - oy;
    img.style.cursor = 'grabbing'; e.preventDefault();
  });
  addEventListener('mousemove', function (e) {
    if (!dragging) return;
    ox = e.clientX - sx; oy = e.clientY - sy; apply();
  });
  addEventListener('mouseup', function () { dragging = false; img.style.cursor = ''; });

  // 滚轮缩放
  v.addEventListener('wheel', function (e) {
    if (!v.classList.contains('open')) return;
    e.preventDefault();
    zoom = Math.min(5, Math.max(1, zoom + (e.deltaY < 0 ? 0.22 : -0.22)));
    if (zoom === 1) { ox = oy = 0; }
    apply();
  }, { passive: false });

  // 点背景关闭
  v.addEventListener('click', function (e) { if (e.target === v) close(); });

  // 触屏：左右滑切换
  var tx = 0, ty = 0;
  v.addEventListener('touchstart', function (e) {
    tx = e.touches[0].clientX; ty = e.touches[0].clientY;
  }, { passive: true });
  v.addEventListener('touchend', function (e) {
    if (zoom > 1) return;
    var dx = e.changedTouches[0].clientX - tx, dy = e.changedTouches[0].clientY - ty;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) show(i + (dx < 0 ? 1 : -1));
    else if (dy > 90) close();
  }, { passive: true });

  addEventListener('keydown', function (e) {
    if (!v.classList.contains('open')) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft') show(i - 1);
    else if (e.key === 'ArrowRight') show(i + 1);
    else if (e.key === '0') reset();
  });
})();
