/* 文章页：阅读进度、删除 */
(function () {
  var bar = document.getElementById('progress');
  if (bar) {
    var sync = function () {
      var h = document.documentElement.scrollHeight - innerHeight;
      bar.style.width = (h > 0 ? (scrollY / h) * 100 : 0) + '%';
    };
    addEventListener('scroll', sync, { passive: true });
    addEventListener('resize', sync); sync();
  }

  var del = document.getElementById('delPost');
  if (del) del.addEventListener('click', function () {
    if (!confirm('确定删除这篇文章吗？删除后无法恢复。')) return;
    fetch('/api/posts/' + del.dataset.slug, { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) { location.href = '/writing'; }
        else { window.toast && toast(d.error || '删除失败'); }
      })
      .catch(function () { window.toast && toast('删除失败，请重试'); });
  });
})();
