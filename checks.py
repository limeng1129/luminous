"""
存储自检。真的去连一次对象存储：写一个测试文件 → 从公开地址读回来 → 删掉。
读回来的内容必须和写进去的一模一样才算通过，这样连 CDN 缓存问题也能查出来。

用法：
  网页版   访问 /health/storage
  命令行   python check_storage.py
"""
import io
import os
import uuid
import urllib.request
import urllib.error

OK, WARN, FAIL = "ok", "warn", "fail"


def _fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "luminous-healthcheck"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def run_checks(db_path, upload_dir):
    """返回 [(标题, 状态, 说明, 修复建议), ...]"""
    out = []
    backend = os.environ.get("STORAGE_BACKEND", "local").lower()

    # ── 1. 当前使用的存储方式 ─────────────────────────────────────────
    if backend == "s3":
        out.append(("存储方式", OK, "对象存储（S3 兼容 / Cloudflare R2）", ""))
    else:
        out.append((
            "存储方式", WARN, "本地磁盘（STORAGE_BACKEND 没设成 s3）",
            "如果你已经配好了 R2，去 Render 的 Environment 里确认 STORAGE_BACKEND 的值是 s3，"
            "保存后会自动重新部署。"))
        out.append(_check_db(db_path))
        return out

    # ── 2. 必填变量是否齐全 ───────────────────────────────────────────
    need = ["S3_BUCKET", "S3_KEY", "S3_SECRET"]
    missing = [k for k in need if not os.environ.get(k)]
    if missing:
        out.append(("环境变量", FAIL, "缺少：" + "、".join(missing),
                    "去 Render 的 Environment 里补上这几个变量。"))
        return out

    bucket = os.environ["S3_BUCKET"]
    endpoint = os.environ.get("S3_ENDPOINT", "")
    public = os.environ.get("S3_PUBLIC_BASE", "").rstrip("/")
    key_masked = os.environ["S3_KEY"][:4] + "…" if os.environ.get("S3_KEY") else ""
    out.append(("环境变量", OK,
                f"桶名 {bucket}｜Key {key_masked}｜端点 {'已填' if endpoint else '（空，按 AWS S3 处理）'}", ""))

    # ── 3. 两个网址有没有填反 ─────────────────────────────────────────
    if not public:
        out.append(("公开地址 S3_PUBLIC_BASE", FAIL, "没有填",
                    "填 R2 桶的公开地址，形如 https://pub-xxxxxxxx.r2.dev（在桶的 Settings → "
                    "Public access 里开启 R2.dev subdomain 后可看到）。"))
    elif "r2.cloudflarestorage.com" in public:
        out.append(("公开地址 S3_PUBLIC_BASE", FAIL, "填成了写入端点，两个网址填反了",
                    "S3_PUBLIC_BASE 要填 https://pub-xxxx.r2.dev（浏览器读取用）；"
                    "https://账号ID.r2.cloudflarestorage.com 那个是 S3_ENDPOINT（程序写入用）。"))
    else:
        out.append(("公开地址 S3_PUBLIC_BASE", OK, public, ""))

    # ── 4. 能不能连上桶 ───────────────────────────────────────────────
    try:
        from storage import get_storage
        st = get_storage(upload_dir)
        resp = st.client.list_objects_v2(Bucket=bucket, MaxKeys=1000)
        n = resp.get("KeyCount", 0)
        out.append(("连接对象存储", OK, f"连接成功，桶里现有 {n} 个文件", ""))
    except Exception as e:
        out.append(("连接对象存储", FAIL, f"连不上：{type(e).__name__} {str(e)[:160]}",
                    "多半是 S3_KEY / S3_SECRET / S3_ENDPOINT 填错，或桶名不对、密钥没给读写权限。"))
        out.append(_check_db(db_path))
        return out

    # ── 5. 写入 ───────────────────────────────────────────────────────
    token = uuid.uuid4().hex
    probe_key = f"_healthcheck_{token}.txt"
    payload = f"luminous-check-{token}".encode()
    try:
        st.save(io.BytesIO(payload), probe_key, "text/plain")
        out.append(("写入测试", OK, f"已写入 {probe_key}", ""))
    except Exception as e:
        out.append(("写入测试", FAIL, f"写不进去：{type(e).__name__} {str(e)[:160]}",
                    "密钥可能只有读权限。在 Cloudflare 重新建一个 Object Read & Write 的 API Token。"))
        out.append(_check_db(db_path))
        return out

    # ── 6. 公开读取（最关键的一步）────────────────────────────────────
    if public:
        probe_url = f"{public}/{probe_key}"
        try:
            status, body = _fetch(probe_url)
            if status == 200 and body.strip() == payload:
                out.append(("公开读取", OK, "从公开地址读回的内容与写入一致，图片能正常显示", ""))
            elif status == 200:
                out.append(("公开读取", WARN, "能访问，但内容对不上（可能是缓存）",
                            "稍等一两分钟再试一次。"))
            else:
                out.append(("公开读取", FAIL, f"返回 HTTP {status}", _public_fix()))
        except urllib.error.HTTPError as e:
            out.append(("公开读取", FAIL, f"返回 HTTP {e.code}", _public_fix()))
        except Exception as e:
            out.append(("公开读取", FAIL, f"读不到：{type(e).__name__} {str(e)[:120]}", _public_fix()))

    # ── 7. 清理 ───────────────────────────────────────────────────────
    try:
        st.delete(probe_key)
        out.append(("清理测试文件", OK, "已删除，删除功能正常", ""))
    except Exception as e:
        out.append(("清理测试文件", WARN, f"没删掉：{str(e)[:120]}",
                    f"手动去桶里删掉 {probe_key} 就行。"))

    out.append(_check_db(db_path))
    return out


def _public_fix():
    return ("最常见的原因：桶没开公开访问。进 Cloudflare → R2 → 你的桶 → Settings → "
            "Public access → 开启 R2.dev subdomain，然后确认 S3_PUBLIC_BASE "
            "填的就是它给出的那个 pub-xxxx.r2.dev 地址。")


def _check_db(db_path):
    import sqlite3
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        n = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
        conn.close()
    except Exception as e:
        return ("数据库", FAIL, f"读不到：{str(e)[:120]}", "")

    on_render = bool(os.environ.get("RENDER"))
    persistent = db_path.startswith("/var/data") or not on_render
    if persistent:
        return ("数据库", OK, f"{n} 条照片记录｜{db_path}", "")
    return ("数据库", WARN,
            f"{n} 条照片记录，但存在临时磁盘上（{db_path}）",
            "重新部署后照片记录会重置回示例（图片文件本身安全地留在 R2 里）。"
            "要彻底解决：换成外部 Postgres，或挂一块持久磁盘并设 LUMINOUS_DB=/var/data/luminous.db。")
