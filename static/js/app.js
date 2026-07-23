/* 流光 Luminous — 前端逻辑（对接 Flask API） */

const CATS = {
  all:    { label: '全部', en: 'All',    color: '#f4efe9' },
  life:   { label: '生活', en: 'Life',   color: '#f2b95c' },
  travel: { label: '旅行', en: 'Travel', color: '#4fc5bd' },
  love:   { label: '爱情', en: 'Love',   color: '#f0879e' },
  nature: { label: '自然', en: 'Nature', color: '#8fbe6a' },
};

const HEART = '<svg viewBox="0 0 24 24"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 1 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>';

let photos = [];        // 全部照片（服务器返回）
let filtered = [];      // 当前筛选后的列表
let activeCat = 'all';
let searchTerm = '';
let lbIndex = -1;
let shareCat = 'life';
let shareFileData = null;

// 本机点过赞的照片 id（存在浏览器里）
const liked = new Set(JSON.parse(localStorage.getItem('luminous_liked') || '[]'));
const saveLiked = () => localStorage.setItem('luminous_liked', JSON.stringify([...liked]));

const $ = (id) => document.getElementById(id);
const fmt = (n) => (n >= 1000 ? (n / 1000).toFixed(1) + 'k' : n);
const esc = (s) => (s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* ---------------------------------------------------------------- boot */
async function boot() {
  buildFilters();
  $('grid').innerHTML = `<div class="state"><div class="spinner"></div>正在把光召集起来…</div>`;
  try {
    const res = await fetch('/api/photos');
    const data = await res.json();
    photos = data.photos;
    fillHero();
    render();
    updateStats();
  } catch (e) {
    $('grid').innerHTML = `<div class="state"><h3>没连上服务器</h3><p>确认后端已经在运行，然后刷新页面。</p></div>`;
  }
}

/* ---------------------------------------------------------------- hero */
function fillHero() {
  const pick = (cat) => photos.find(p => p.category === cat);
  [['travel', 'hero-travel'], ['love', 'hero-love'], ['life', 'hero-life']].forEach(([cat, id]) => {
    const p = pick(cat);
    const el = $(id);
    if (p && el) { el.src = p.src; el.alt = p.title; }
  });
}

/* ---------------------------------------------------------------- filters */
function buildFilters() {
  $('filters').innerHTML = Object.entries(CATS).map(([k, v]) =>
    `<button class="pill ${k === activeCat ? 'active' : ''}" style="--pc:${v.color}" data-cat="${k}" onclick="setCat('${k}')">
      ${v.label}<span class="en">${v.en}</span></button>`).join('');
}
function setCat(k) {
  activeCat = k;
  document.querySelectorAll('.pill').forEach(p => p.classList.toggle('active', p.dataset.cat === k));
  render();
}

/* ---------------------------------------------------------------- render grid */
function applyFilter() {
  const q = searchTerm.trim().toLowerCase();
  filtered = photos.filter(p => {
    const okCat = activeCat === 'all' || p.category === activeCat;
    const hay = (p.title + ' ' + (p.subtitle || '') + ' ' + CATS[p.category].label).toLowerCase();
    return okCat && (!q || hay.includes(q));
  });
}
function render() {
  applyFilter();
  const grid = $('grid');
  if (!filtered.length) {
    grid.innerHTML = `<div class="state"><h3>这里还没有光</h3><p>换个关键词，或者分享一张属于你的照片。</p></div>`;
    return;
  }
  grid.innerHTML = filtered.map((p, i) => {
    const c = CATS[p.category];
    const on = liked.has(p.id);
    return `<figure class="card" style="--cc:${c.color};animation-delay:${Math.min(i * 45, 600)}ms">
      <button class="card-hit" onclick="openLightbox(${p.id})" aria-label="查看 ${esc(p.title)}">
        <img src="${p.src}" alt="${esc(p.title)}" loading="lazy" style="aspect-ratio:${p.width}/${p.height}">
        <span class="tag">${c.label}</span>
        <figcaption class="cap">
          <span class="cap-title">${esc(p.title)}</span>
          <span class="cap-sub">${esc(p.subtitle || '')}</span>
        </figcaption>
      </button>
      <button class="like ${on ? 'on' : ''}" onclick="toggleLike(${p.id},event)" aria-label="喜欢">
        ${HEART}<span>${fmt(p.likes)}</span>
      </button>
    </figure>`;
  }).join('');
  observeCards();
}

let io;
function observeCards() {
  if (io) io.disconnect();
  io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.card').forEach(c => io.observe(c));
}

/* ---------------------------------------------------------------- like */
async function toggleLike(id, e) {
  if (e) e.stopPropagation();
  const p = photos.find(x => x.id === id);
  if (!p) return;
  const nowLiked = !liked.has(id);
  nowLiked ? liked.add(id) : liked.delete(id);
  saveLiked();

  // 本地即时反馈
  p.likes = Math.max(0, p.likes + (nowLiked ? 1 : -1));
  refreshLikeUI(id);

  try {
    const res = await fetch(`/api/photos/${id}/like`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ liked: nowLiked }),
    });
    const data = await res.json();
    if (typeof data.likes === 'number') { p.likes = data.likes; refreshLikeUI(id); }
  } catch (_) { /* 离线也不影响本地显示 */ }

  updateStats();
}
function refreshLikeUI(id) {
  const p = photos.find(x => x.id === id);
  const on = liked.has(id);
  // 网格里的按钮
  document.querySelectorAll('.card .like').forEach(btn => {
    if (btn.getAttribute('onclick').includes(`(${id},`)) {
      btn.classList.toggle('on', on);
      btn.querySelector('span').textContent = fmt(p.likes);
    }
  });
  // 灯箱
  if (lbIndex >= 0 && filtered[lbIndex] && filtered[lbIndex].id === id) syncLbLike();
}

/* ---------------------------------------------------------------- lightbox */
function openLightbox(id) {
  lbIndex = filtered.findIndex(p => p.id === id);
  if (lbIndex < 0) return;
  paintLb();
  $('lightbox').classList.add('open');
  document.body.style.overflow = 'hidden';
}
function paintLb() {
  const p = filtered[lbIndex];
  const c = CATS[p.category];
  $('lbImg').src = p.src;
  $('lbImg').alt = p.title;
  $('lbTitle').textContent = p.title;
  $('lbSub').textContent = p.subtitle || '';
  const tag = $('lbTag');
  tag.textContent = c.label; tag.style.background = c.color;
  document.querySelector('.lb-inner').style.setProperty('--cc', c.color);
  $('lbIndex').textContent = `${lbIndex + 1} / ${filtered.length}`;
  syncLbLike();
}
function syncLbLike() {
  const p = filtered[lbIndex];
  const on = liked.has(p.id);
  $('lbLike').classList.toggle('on', on);
  $('lbLikeText').textContent = on ? '已喜欢' : '喜欢';
  $('lbCount').textContent = fmt(p.likes) + ' 次喜欢';
}
function lbToggleLike() { toggleLike(filtered[lbIndex].id, null); }
function lbNav(dir) {
  lbIndex = (lbIndex + dir + filtered.length) % filtered.length;
  paintLb();
}
function closeLightbox() {
  $('lightbox').classList.remove('open');
  document.body.style.overflow = '';
  lbIndex = -1;
}
async function lbDelete() {
  const p = filtered[lbIndex];
  if (!p) return;
  if (!confirm(`确定删除「${p.title}」吗？删除后无法恢复。`)) return;
  try {
    await fetch(`/api/photos/${p.id}`, { method: 'DELETE' });
    photos = photos.filter(x => x.id !== p.id);
    liked.delete(p.id); saveLiked();
    closeLightbox();
    fillHero(); render(); updateStats();
    toast('已删除这张照片');
  } catch (_) { toast('删除失败，请重试'); }
}
$('lightbox').addEventListener('click', e => { if (e.target.id === 'lightbox') closeLightbox(); });

/* ---------------------------------------------------------------- share */
function openShare() {
  $('modal').classList.add('open');
  document.body.style.overflow = 'hidden';
  buildCatPicker();
}
function closeShare() {
  $('modal').classList.remove('open');
  document.body.style.overflow = '';
  resetShare();
}
function resetShare() {
  shareFileData = null; shareCat = 'life';
  $('fileInput').value = ''; $('urlInput').value = '';
  $('titleInput').value = ''; $('subInput').value = '';
  const drop = $('drop'); drop.classList.remove('has');
  $('dropInner').innerHTML =
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/></svg><p><b>点击选择照片</b><br>支持 JPG / PNG / WEBP / GIF，最大 12MB</p>`;
}
function buildCatPicker() {
  $('catPicker').innerHTML = Object.entries(CATS).filter(([k]) => k !== 'all').map(([k, v]) =>
    `<button data-cat="${k}" onclick="pickCat('${k}',event)">${v.label}</button>`).join('');
  syncPicker();
}
function pickCat(k, e) { e.preventDefault(); shareCat = k; syncPicker(); }
function syncPicker() {
  document.querySelectorAll('#catPicker button').forEach(b => {
    const on = b.dataset.cat === shareCat;
    b.classList.toggle('sel', on);
    b.style.background = on ? CATS[b.dataset.cat].color : 'transparent';
    b.style.borderColor = on ? 'transparent' : 'var(--line)';
  });
}

// 选择本地文件
$('fileInput').addEventListener('change', e => {
  const f = e.target.files[0];
  if (!f) return;
  const reader = new FileReader();
  reader.onload = ev => {
    shareFileData = f;
    $('urlInput').value = '';
    $('drop').classList.add('has');
    $('dropInner').innerHTML = `<img src="${ev.target.result}" alt="预览">`;
  };
  reader.readAsDataURL(f);
});
// 拖拽上传
const drop = $('drop');
['dragover', 'dragenter'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('hover'); }));
['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('hover'); }));
drop.addEventListener('drop', e => {
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('image/')) { $('fileInput').files = e.dataTransfer.files; $('fileInput').dispatchEvent(new Event('change')); }
});

$('modal').addEventListener('click', e => { if (e.target.id === 'modal') closeShare(); });

async function publish() {
  const url = $('urlInput').value.trim();
  if (!shareFileData && !url) { shake(); toast('请先选一张照片或填写链接'); return; }

  const btn = $('publishBtn');
  btn.disabled = true; btn.textContent = '发布中…';

  const fd = new FormData();
  fd.append('title', $('titleInput').value.trim());
  fd.append('subtitle', $('subInput').value.trim());
  fd.append('category', shareCat);
  if (shareFileData) fd.append('file', shareFileData);
  else fd.append('url', url);

  try {
    const res = await fetch('/api/photos', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '发布失败');
    photos.unshift(data);
    activeCat = 'all'; searchTerm = ''; $('searchInput').value = '';
    buildFilters(); fillHero(); render(); updateStats();
    closeShare();
    toast('已发布，你的照片在最前面');
    window.scrollTo({ top: $('gallery').offsetTop - 80, behavior: 'smooth' });
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false; btn.textContent = '发布';
  }
}
function shake() {
  $('modal').querySelector('.sheet').animate(
    [{ transform: 'translateX(0)' }, { transform: 'translateX(-8px)' }, { transform: 'translateX(8px)' }, { transform: 'translateX(0)' }],
    { duration: 300 });
}

/* ---------------------------------------------------------------- search */
let searchTimer;
$('searchInput').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { searchTerm = e.target.value; render(); }, 160);
});

/* ---------------------------------------------------------------- stats */
function updateStats() {
  $('stat-count').textContent = photos.length;
  $('stat-likes').textContent = fmt(photos.reduce((s, p) => s + p.likes, 0));
}

/* ---------------------------------------------------------------- toast */
let toastTimer;
function toast(msg) {
  $('toastText').textContent = msg;
  $('toast').classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2600);
}

/* ---------------------------------------------------------------- hero parallax */
const hg = $('heroGallery');
if (window.matchMedia('(hover:hover)').matches && !window.matchMedia('(prefers-reduced-motion:reduce)').matches) {
  hg.addEventListener('mousemove', e => {
    const r = hg.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - .5;
    const y = (e.clientY - r.top) / r.height - .5;
    hg.querySelectorAll('.float').forEach(f => {
      const base = f.classList.contains('f1') ? -5 : f.classList.contains('f2') ? 4 : -2;
      const d = f.classList.contains('f1') ? 18 : f.classList.contains('f2') ? 34 : 52;
      f.style.transform = `translate(${x * d}px,${y * d}px) rotate(${base}deg)`;
    });
  });
  hg.addEventListener('mouseleave', () => {
    hg.querySelectorAll('.float').forEach(f => {
      const base = f.classList.contains('f1') ? -5 : f.classList.contains('f2') ? 4 : -2;
      f.style.transform = `rotate(${base}deg)`;
    });
  });
}

/* ---------------------------------------------------------------- keyboard */
document.addEventListener('keydown', e => {
  if ($('lightbox').classList.contains('open')) {
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') lbNav(-1);
    if (e.key === 'ArrowRight') lbNav(1);
  }
  if (e.key === 'Escape' && $('modal').classList.contains('open')) closeShare();
});

boot();
