"""
文章模块：随笔 / 旅行 / 感悟。

- Markdown 正文，渲染时做白名单清洗，避免注入。
- 写作和删除需要管理员密码（环境变量 ADMIN_PASSWORD）。
  没设密码时不作限制，方便本地调试；线上一定要设。
"""
import os
import re
import html
import hashlib
import datetime

from db import get_db

CATEGORIES = {
    "travel":     {"label": "旅行", "en": "Travel"},
    "reflection": {"label": "感悟", "en": "Reflection"},
    "life":       {"label": "生活", "en": "Life"},
}


# ---------------------------------------------------------------- 管理员
def admin_password():
    return (os.environ.get("ADMIN_PASSWORD") or "").strip()


def admin_required_configured():
    return bool(admin_password())


def check_password(pw):
    real = admin_password()
    if not real:
        return True            # 没设密码 = 不设防（本地调试用）
    return (pw or "").strip() == real


def admin_cookie_value():
    """由密码派生的 cookie 值，密码变了旧 cookie 自动失效。"""
    return hashlib.sha256(("luminous:" + admin_password()).encode()).hexdigest()[:32]


def is_admin(request):
    if not admin_required_configured():
        return True
    return request.cookies.get("luminous_admin") == admin_cookie_value()


# ---------------------------------------------------------------- slug
def make_slug(title, existing_check):
    """中文标题生成可读 slug：优先用标题里的 ASCII，否则用日期+短哈希。"""
    base = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    if not base or len(base) < 3:
        stamp = datetime.datetime.now().strftime("%Y%m%d")
        digest = hashlib.md5((title or "").encode("utf-8")).hexdigest()[:6]
        base = f"{stamp}-{digest}"
    slug, i = base, 2
    while existing_check(slug):
        slug = f"{base}-{i}"
        i += 1
    return slug


# ---------------------------------------------------------------- Markdown
_INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"), r"<em>\1</em>"),
    (re.compile(r"`(.+?)`"), r"<code>\1</code>"),
    (re.compile(r"\[(.+?)\]\((https?://[^\s)]+)\)"), r'<a href="\2" rel="noopener" target="_blank">\1</a>'),
]


def _inline(text):
    out = html.escape(text, quote=False)
    for pattern, repl in _INLINE:
        out = pattern.sub(repl, out)
    return out


def render_markdown(md):
    """一个够用且安全的 Markdown 子集：标题、段落、引用、列表、图片、分隔线。

    自己实现而不是引第三方库，是为了默认转义所有 HTML —— 正文里写不进脚本。
    """
    lines = (md or "").replace("\r\n", "\n").split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        # 分隔线
        if re.fullmatch(r"-{3,}|\*{3,}", line.strip()):
            out.append('<hr class="a-rule">')
            i += 1
            continue

        # 独占一行的图片 → 出血大图
        m = re.fullmatch(r"!\[(.*?)\]\((\S+?)\)", line.strip())
        if m:
            alt, src = html.escape(m.group(1)), html.escape(m.group(2), quote=True)
            out.append(f'<figure class="a-figure"><img src="{src}" alt="{alt}" loading="lazy">'
                       + (f'<figcaption>{alt}</figcaption>' if alt else "") + '</figure>')
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1)) + 1          # h1 留给文章标题
            out.append(f"<h{lvl}>{_inline(m.group(2).strip())}</h{lvl}>")
            i += 1
            continue

        # 引用（连续多行合并）
        if line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip(">").strip())
                i += 1
            out.append(f'<blockquote>{_inline(" ".join(buf))}</blockquote>')
            continue

        # 列表
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(f"<li>{_inline(re.sub(r'^\s*[-*]\s+', '', lines[i]).strip())}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # 段落（连续行合并）
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#{1,3}\s|>|\s*[-*]\s|!\[)", lines[i]) and not re.fullmatch(
                r"-{3,}|\*{3,}", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append(f"<p>{_inline(' '.join(buf))}</p>")

    return "\n".join(out)


def excerpt(md, n=90):
    """从正文取一段纯文本摘要。"""
    text = re.sub(r"!\[.*?\]\(.*?\)", "", md or "")
    text = re.sub(r"[#>*`\-\[\]]|\(https?://\S+\)", "", text)
    text = " ".join(text.split())
    return text[:n] + ("…" if len(text) > n else "")


def read_minutes(md):
    """中文按每分钟 400 字估算。"""
    n = len(re.sub(r"\s", "", md or ""))
    return max(1, round(n / 400))


# ---------------------------------------------------------------- 数据操作
def row_to_post(r, with_body=False):
    d = {
        "id": r["id"], "slug": r["slug"], "category": r["category"],
        "title": r["title"], "dek": r["dek"], "cover": r["cover"],
        "place": r["place"], "created_at": r["created_at"],
        "excerpt": excerpt(r["body"]), "minutes": read_minutes(r["body"]),
    }
    if with_body:
        d["body"] = r["body"]
        d["html"] = render_markdown(r["body"])
    return d


def list_posts(category=None, limit=None):
    with get_db() as c:
        rows = c.execute(
            "SELECT * FROM posts WHERE published=1 ORDER BY id DESC").fetchall()
    posts = [row_to_post(r) for r in rows]
    if category and category != "all":
        posts = [p for p in posts if p["category"] == category]
    return posts[:limit] if limit else posts


def get_post(slug):
    with get_db() as c:
        r = c.execute("SELECT * FROM posts WHERE slug=?", (slug,)).fetchone()
    return row_to_post(r, with_body=True) if r else None


def create_post(title, dek, body, category, cover, place):
    def exists(s):
        with get_db() as c:
            return c.execute("SELECT id FROM posts WHERE slug=?", (s,)).fetchone() is not None

    slug = make_slug(title, exists)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    with get_db() as c:
        new_id = c.insert_returning_id(
            """INSERT INTO posts (slug, category, title, dek, cover, body, place, published, created_at)
               VALUES (?,?,?,?,?,?,?,1,?)""",
            (slug, category, title, dek, cover, body, place, now))
        r = c.execute("SELECT * FROM posts WHERE id=?", (new_id,)).fetchone()
    return row_to_post(r, with_body=True)


def delete_post(slug):
    with get_db() as c:
        r = c.execute("SELECT id FROM posts WHERE slug=?", (slug,)).fetchone()
        if not r:
            return False
        c.execute("DELETE FROM posts WHERE slug=?", (slug,))
    return True
