/* 首页上那条安静的横带：说一句此刻的话，配三张这个钟点的照片 */
(function () {
  var H = window.HOURS || {};
  var bar = document.getElementById('nowbar');
  if (!bar || !H.buckets || !H.known) return;

  function two(n) { return (n < 10 ? '0' : '') + n; }

  function paint() {
    var now = new Date(), h = now.getHours(), b = H.buckets[h];
    var t = document.getElementById('nowbarText');
    if (b.count) {
      t.innerHTML = '现在是 ' + two(h) + ':' + two(now.getMinutes()) + '，' + b.label +
        '。这个钟点你拍过 <b>' + b.count + '</b> 张。';
      bar.style.setProperty('--glow', b.rgb);
    } else {
      // 这个钟点没有，就找最近的一个有照片的
      var near = null, best = 99;
      H.buckets.forEach(function (x) {
        if (!x.count) return;
        var d = Math.min(Math.abs(x.hour - h), 24 - Math.abs(x.hour - h));
        if (d < best) { best = d; near = x; }
      });
      if (!near) return;
      t.innerHTML = '现在是 ' + two(h) + ':' + two(now.getMinutes()) + '，' + b.label +
        '。这个钟点还没有照片——离得最近的是<b>' + near.label + '</b>。';
      bar.style.setProperty('--glow', near.rgb);
      b = near;
    }
    var w = document.getElementById('nowbarShots');
    w.innerHTML = b.photos.slice(0, 3).map(function (p) {
      return '<img src="' + p.src + '" alt="' + (p.title || '') + '" loading="lazy">';
    }).join('');
  }

  paint();
  setInterval(paint, 60000);
})();
