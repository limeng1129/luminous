/* 此刻：一天二十四小时的光。当前钟点按访客本地时间算。 */
(function () {
  var H = window.HOURS || {};
  var buckets = H.buckets || [];
  if (!buckets.length || !H.known) return;

  var clock = document.getElementById('clock');
  var nowLine = document.getElementById('nowLine');
  var shots = document.getElementById('nowShots');
  var emptyMsg = document.getElementById('nowEmpty');
  var sec = document.getElementById('hoursec');

  var maxCount = Math.max.apply(null, buckets.map(function (b) { return b.count; })) || 1;
  var picked = -1;

  // 二十四格。有照片的用那个钟点的平均色，没有的留一道暗痕。
  var cells = buckets.map(function (b, h) {
    var el = document.createElement('button');
    el.className = 'hcell' + (b.count ? '' : ' bare');
    el.style.setProperty('--c', b.rgb || 'rgba(255,255,255,.05)');
    el.style.setProperty('--hgt', (b.count ? 22 + (b.count / maxCount) * 78 : 8) + '%');
    el.setAttribute('aria-label', h + ' 点 ' + b.label + '，' + b.count + ' 张');
    el.addEventListener('click', function () { pick(h, true); });
    clock.appendChild(el);
    return el;
  });

  function two(n) { return (n < 10 ? '0' : '') + n; }

  function pick(h, byUser) {
    if (h === picked) return;
    if (picked >= 0) cells[picked].classList.remove('on');
    picked = h;
    var b = buckets[h];
    cells[h].classList.add('on');

    // 整页染上这个钟点的光
    sec.style.setProperty('--glow', b.rgb || 'rgba(255,255,255,.06)');
    sec.classList.toggle('lit', !!b.rgb);

    var now = new Date();
    var prefix = byUser ? (two(h) + ':00 前后' ) :
      ('现在是 ' + two(now.getHours()) + ':' + two(now.getMinutes()));
    if (b.count) {
      nowLine.innerHTML = prefix + '，' + b.label + '。这个钟点你拍过 <b>' + b.count + '</b> 张。';
      emptyMsg.textContent = '';
    } else {
      nowLine.innerHTML = prefix + '，' + b.label + '。';
      emptyMsg.textContent = '这个钟点还没有照片。';
    }

    shots.innerHTML = '';
    window.PHOTOS = b.photos;
    b.photos.slice(0, 12).forEach(function (p, i) {
      var f = document.createElement('button');
      f.className = 'hshot';
      f.style.animationDelay = (i * 70) + 'ms';
      f.innerHTML = '<img src="' + p.src + '" alt="' + (p.title || '') + '" loading="lazy">' +
        '<span><b>' + (p.title || '') + '</b>' +
        (p.subtitle ? '<i>' + p.subtitle + '</i>' : '') + '</span>';
      f.addEventListener('click', function () { if (window.openViewer) window.openViewer(i); });
      shots.appendChild(f);
    });
  }

  // 开场：跳到访客当地的此刻
  var h0 = new Date().getHours();
  pick(h0, false);

  // 跨过整点时自动跟上
  setInterval(function () {
    var h = new Date().getHours();
    if (h !== picked) pick(h, false);
  }, 60000);

  // 键盘左右换钟点
  clock.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight') { pick((picked + 1) % 24, true); e.preventDefault(); }
    else if (e.key === 'ArrowLeft') { pick((picked + 23) % 24, true); e.preventDefault(); }
  });
})();
