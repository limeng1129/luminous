/* 写作页：分类、封面、插图、发布 */
(function () {
  var cat = document.querySelector('#catSeg button').dataset.cat;
  var coverFile = null;

  document.querySelectorAll('#catSeg button').forEach(function (b) {
    b.addEventListener('click', function () {
      cat = b.dataset.cat;
      document.querySelectorAll('#catSeg button').forEach(function (x) {
        x.classList.toggle('on', x === b);
      });
    });
  });

  // 封面
  var drop = document.getElementById('drop'), cover = document.getElementById('cover');
  cover.addEventListener('change', function () {
    var f = cover.files[0]; if (!f) return;
    coverFile = f;
    var fr = new FileReader();
    fr.onload = function (e) {
      drop.classList.add('has');
      document.getElementById('dropInner').innerHTML = '<img src="' + e.target.result + '" alt="封面预览">';
    };
    fr.readAsDataURL(f);
  });
  ['dragover', 'dragenter'].forEach(function (n) {
    drop.addEventListener(n, function (e) { e.preventDefault(); drop.classList.add('over'); });
  });
  ['dragleave', 'drop'].forEach(function (n) {
    drop.addEventListener(n, function (e) { e.preventDefault(); drop.classList.remove('over'); });
  });
  drop.addEventListener('drop', function (e) {
    var f = e.dataTransfer.files[0];
    if (f && f.type.indexOf('image/') === 0) { cover.files = e.dataTransfer.files;
      cover.dispatchEvent(new Event('change')); }
  });

  // 正文插图：上传后把 Markdown 插到光标处
  var body = document.getElementById('body');
  document.getElementById('inline').addEventListener('change', function (e) {
    var f = e.target.files[0]; if (!f) return;
    var fd = new FormData();
    fd.append('file', f); fd.append('title', f.name.replace(/\.[^.]+$/, '')); fd.append('category', 'life');
    window.toast && toast('正在上传…');
    fetch('/api/photos', { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.src) throw new Error(d.error || '上传失败');
        var md = '\n![' + (d.title || '') + '](' + d.src + ')\n';
        var s = body.selectionStart || body.value.length;
        body.value = body.value.slice(0, s) + md + body.value.slice(s);
        body.focus(); body.selectionStart = body.selectionEnd = s + md.length;
        window.toast && toast('已插入到正文');
      })
      .catch(function (err) { window.toast && toast(err.message); })
      .finally(function () { e.target.value = ''; });
  });

  // 发布
  var btn = document.getElementById('publish');
  btn.addEventListener('click', function () {
    var title = document.getElementById('title').value.trim();
    var text = body.value.trim();
    if (!title) { window.toast && toast('给它起个标题'); return; }
    if (!text) { window.toast && toast('正文还是空的'); return; }

    btn.disabled = true; btn.textContent = '发布中…';
    var fd = new FormData();
    fd.append('title', title);
    fd.append('dek', document.getElementById('dek').value.trim());
    fd.append('place', document.getElementById('place').value.trim());
    fd.append('body', text);
    fd.append('category', cat);
    if (coverFile) fd.append('cover', coverFile);

    fetch('/api/posts', { method: 'POST', body: fd })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.d.error || '发布失败');
        location.href = '/p/' + res.d.slug;
      })
      .catch(function (err) {
        window.toast && toast(err.message);
        btn.disabled = false; btn.textContent = '发布';
      });
  });
})();
