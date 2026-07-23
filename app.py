"""
流光 Luminous — 图片分享网站后端
Flask + SQLite。运行:python app.py，然后打开 http://127.0.0.1:5000
"""
import io
import os
import time
import uuid
import datetime
from flask import (
    Flask, request, jsonify, render_template,
    send_from_directory
)
from storage import get_storage
from onedrive import to_direct_link, is_onedrive_link
from db import get_db, init_db, SQLITE_PATH, describe as db_describe, is_postgres

BASE = os.path.dirname(os.path.abspath(__file__))
# 数据库与上传目录可通过环境变量指向持久化磁盘（部署到云平台时用）
DB_PATH = SQLITE_PATH   # 仅 SQLite 模式用；设了 DATABASE_URL 就走 Postgres
UPLOAD_DIR = os.environ.get("LUMINOUS_UPLOAD_DIR", os.path.join(BASE, "static", "uploads"))
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_BYTES = 12 * 1024 * 1024  # 单张图片上限 12MB

# 四个分类 —— 每章一种身份色
CATEGORIES = {
    "life":   {"label": "生活", "en": "Life",   "color": "#f2b95c"},
    "travel": {"label": "旅行", "en": "Travel", "color": "#4fc5bd"},
    "love":   {"label": "爱情", "en": "Love",   "color": "#f0879e"},
    "nature": {"label": "自然", "en": "Nature", "color": "#8fbe6a"},
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES


# ---------------------------------------------------------------- db helpers
def row_to_photo(r):
    if r["url"]:
        src = r["url"]
    elif r["filename"]:
        src = get_storage(UPLOAD_DIR).url(r["filename"])
    else:
        src = ""
    return {
        "id": r["id"],
        "category": r["category"],
        "src": src,
        "title": r["title"],
        "subtitle": r["subtitle"],
        "width": r["width"],
        "height": r["height"],
        "likes": r["likes"],
        "created_at": r["created_at"],
    }


# 启动时如果存储有问题，把原因记下来，供自检页显示
BOOT_ERROR = None
PROCESS_START = time.time()


def bootstrap():
    """建表 + 首次运行时生成示例照片。

    关键：即使存储配置有问题，也绝不能让网站起不来——
    否则你连 /health/storage 这个用来查问题的页面都打不开。
    """
    global BOOT_ERROR
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except Exception:
        pass
    try:
        init_db()
    except Exception as e:
        BOOT_ERROR = f"数据库初始化失败：{type(e).__name__}: {e}"
        print(f"  [启动警告] {BOOT_ERROR}")
        return
    try:
        from seed import seed_if_empty
        seed_if_empty(UPLOAD_DIR)
    except Exception as e:
        BOOT_ERROR = f"示例照片写入存储失败：{type(e).__name__}: {e}"
        print(f"  [启动警告] {BOOT_ERROR}")
        print("  网站仍会正常启动。请访问 /health/storage 查看具体原因。")


# ---------------------------------------------------------------- pages
@app.route("/")
def index():
    return render_template("index.html", categories=CATEGORIES)


@app.route("/about")
def about():
    return render_template("about.html", categories=CATEGORIES)


@app.route("/uploads/<path:name>")
def uploaded_file(name):
    return send_from_directory(UPLOAD_DIR, name)


# ---------------------------------------------------------------- api
@app.get("/api/photos")
def list_photos():
    cat = request.args.get("cat", "all")
    q = request.args.get("q", "").strip().lower()
    with get_db() as c:
        rows = c.execute("SELECT * FROM photos ORDER BY id DESC").fetchall()
    photos = [row_to_photo(r) for r in rows]
    if cat != "all":
        photos = [p for p in photos if p["category"] == cat]
    if q:
        photos = [
            p for p in photos
            if q in (p["title"] + " " + (p["subtitle"] or "")).lower()
        ]
    return jsonify({"photos": photos, "categories": CATEGORIES})


@app.post("/api/photos")
def create_photo():
    title = (request.form.get("title") or "未命名的瞬间").strip()[:60]
    subtitle = (request.form.get("subtitle") or "").strip()[:40]
    category = request.form.get("category", "life")
    if category not in CATEGORIES:
        category = "life"

    url = (request.form.get("url") or "").strip()
    file = request.files.get("file")
    filename, width, height = None, 800, 1000

    if file and file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_EXT:
            return jsonify({"error": "不支持的图片格式，请用 JPG / PNG / WEBP / GIF"}), 400
        blob = io.BytesIO(file.read())
        try:
            from PIL import Image
            with Image.open(blob) as im:
                width, height = im.size
        except Exception:
            return jsonify({"error": "这个文件好像不是有效的图片"}), 400
        filename = f"{uuid.uuid4().hex}.{ext}"
        get_storage(UPLOAD_DIR).save(blob, filename, file.mimetype)
        url = None
    elif url:
        # OneDrive / SharePoint 分享链接自动转成可直接显示的直链
        if is_onedrive_link(url):
            url = to_direct_link(url)
        try:
            width = int(request.form.get("width") or 800)
            height = int(request.form.get("height") or 1000)
        except ValueError:
            width, height = 800, 1000
    else:
        return jsonify({"error": "请选择一张照片，或填写图片链接"}), 400

    if not subtitle:
        subtitle = CATEGORIES[category]["label"]

    now = datetime.datetime.now().isoformat(timespec="seconds")
    with get_db() as c:
        new_id = c.insert_returning_id(
            """INSERT INTO photos
               (category, filename, url, title, subtitle, width, height, likes, created_at)
               VALUES (?,?,?,?,?,?,?,0,?)""",
            (category, filename, url, title, subtitle, width, height, now),
        )
        r = c.execute("SELECT * FROM photos WHERE id=?", (new_id,)).fetchone()
    return jsonify(row_to_photo(r)), 201


@app.post("/api/photos/<int:pid>/like")
def like_photo(pid):
    data = request.get_json(silent=True) or {}
    delta = 1 if data.get("liked") else -1
    with get_db() as c:
        r = c.execute("SELECT likes FROM photos WHERE id=?", (pid,)).fetchone()
        if not r:
            return jsonify({"error": "照片不存在"}), 404
        new_val = max(0, r["likes"] + delta)
        c.execute("UPDATE photos SET likes=? WHERE id=?", (new_val, pid))
    return jsonify({"id": pid, "likes": new_val})


@app.delete("/api/photos/<int:pid>")
def delete_photo(pid):
    with get_db() as c:
        r = c.execute("SELECT filename FROM photos WHERE id=?", (pid,)).fetchone()
        if not r:
            return jsonify({"error": "照片不存在"}), 404
        if r["filename"]:
            get_storage(UPLOAD_DIR).delete(r["filename"])
        c.execute("DELETE FROM photos WHERE id=?", (pid,))
    return jsonify({"ok": True})


@app.get("/api/stats")
def stats():
    with get_db() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(likes),0) AS l FROM photos"
        ).fetchone()
    return jsonify({"count": row["n"], "likes": row["l"], "chapters": len(CATEGORIES)})


@app.get("/health/storage")
def health_storage():
    """存储自检。浏览器直接访问即可；加 ?format=json 返回 JSON。"""
    token = os.environ.get("HEALTH_TOKEN")
    if token and request.args.get("token") != token:
        return jsonify({"error": "需要正确的 token"}), 403

    from checks import run_checks
    results = run_checks(DB_PATH, UPLOAD_DIR)
    mins = int((time.time() - PROCESS_START) // 60)
    started = time.strftime("%H:%M", time.localtime(PROCESS_START))
    results.insert(0, ("本次运行", "ok",
                       f"当前进程在 {started}（UTC）启动，已运行 {mins} 分钟",
                       "改完环境变量后必须等重新部署完成才生效。"
                       "如果这个时间早于你改变量的时间，说明新配置还没加载。"))
    if BOOT_ERROR:
        results.insert(0, ("启动时的错误", "fail", BOOT_ERROR,
                           "下面各项会指出具体是哪里的问题。"))

    if request.args.get("format") == "json":
        return jsonify({"checks": [
            {"name": n, "status": s, "detail": d, "fix": f} for n, s, d, f in results
        ]})

    worst = "ok"
    for _, s, _, _ in results:
        if s == "fail":
            worst = "fail"; break
        if s == "warn":
            worst = "warn"
    return render_template("health.html", results=results, worst=worst)


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": "图片太大了，请控制在 12MB 以内"}), 413


# 应用被导入时（gunicorn / PythonAnywhere / python app.py）即完成初始化：
# 建库 + 首次生成示例照片（幂等，多进程安全）
bootstrap()


if __name__ == "__main__":
    print("\n  流光 Luminous 已启动 →  http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
