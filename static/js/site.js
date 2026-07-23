/* 全站通用：滚动浮现、导航配色、提示条 */
(function () {
  var reduce = matchMedia('(prefers-reduced-motion:reduce)').matches;

  // 元素进入视口时浮现
  var rises = document.querySelectorAll('.rise');
  if (rises.length && !reduce && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e, i) {
        if (e.isIntersecting) {
          e.target.style.transitionDelay = Math.min(i * 60, 300) + 'ms';
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    rises.forEach(function (el) { io.observe(el); });
  } else {
    rises.forEach(function (el) { el.classList.add('in'); });
  }

  // 滚进黑色区域时，导航跟着变深
  var nav = document.getElementById('nav');
  var voids = document.querySelectorAll('.void');
  if (nav && voids.length) {
    var sync = function () {
      var h = nav.offsetHeight, on = false;
      voids.forEach(function (v) {
        var r = v.getBoundingClientRect();
        if (r.top <= h && r.bottom >= h) on = true;
      });
      nav.classList.toggle('on-void', on);
    };
    addEventListener('scroll', sync, { passive: true });
    addEventListener('resize', sync);
    sync();
  }

  // 提示条
  var t = document.getElementById('toast'), timer;
  window.toast = function (msg) {
    if (!t) return;
    t.textContent = msg; t.classList.add('show');
    clearTimeout(timer); timer = setTimeout(function () { t.classList.remove('show'); }, 2800);
  };
})();
