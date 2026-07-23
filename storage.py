"""
可插拔的照片存储后端。

用环境变量 STORAGE_BACKEND 选择：
  local  （默认）—— 存到 static/uploads/。适合自己的服务器、PythonAnywhere。
  s3            —— 存到任何 S3 兼容的对象存储。照片永久保存，服务器重启也不丢。
                   支持 Cloudflare R2 / Backblaze B2 / AWS S3 / 阿里云 OSS / 腾讯云 COS。

s3 模式需要的环境变量：
  S3_BUCKET        存储桶名
  S3_KEY           Access Key ID
  S3_SECRET        Secret Access Key
  S3_ENDPOINT      服务端点（AWS S3 可留空；R2/B2/OSS/COS 必填）
  S3_PUBLIC_BASE   图片的公开访问前缀，例如 https://pub-xxxx.r2.dev
  S3_REGION        区域（可选，默认 auto）
"""
import os
import mimetypes
from urllib.parse import urlparse


def normalize_endpoint(ep: str):
    """把端点规整成账号级地址。

    Cloudflare 在桶页面显示的 S3 API 地址末尾带着桶名，
    形如 https://账号ID.r2.cloudflarestorage.com/桶名 —— 直接拿来用会让路径重复，
    请求就会 404。这里自动把多余的路径去掉。
    返回 (规整后的端点, 提示信息或 None)
    """
    ep = (ep or "").strip().rstrip("/")
    if not ep:
        return None, None
    if "://" not in ep:
        ep = "https://" + ep
    p = urlparse(ep)
    path = p.path.strip("/")
    if path:
        return f"{p.scheme}://{p.netloc}", f"S3_ENDPOINT 末尾多了路径 /{path}，已自动忽略"
    return f"{p.scheme}://{p.netloc}", None


class LocalStorage:
    """存到本地磁盘，由 Flask 的 /uploads/ 路由提供访问。"""

    name = "local"

    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def save(self, fileobj, key, content_type=None):
        path = os.path.join(self.root, key)
        with open(path, "wb") as f:
            fileobj.seek(0)
            f.write(fileobj.read())
        return key

    def url(self, key):
        return f"/uploads/{key}"

    def delete(self, key):
        path = os.path.join(self.root, key)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


class S3Storage:
    """存到 S3 兼容的对象存储。照片与服务器分离，重新部署也不会丢。"""

    name = "s3"

    def __init__(self):
        import boto3
        from botocore.client import Config

        # .strip() 很重要：从网页复制密钥时经常会带上看不见的空格或换行，
        # 那会让签名对不上，服务端直接回 401。
        def env(k, default=""):
            return (os.environ.get(k) or default).strip()

        self.bucket = env("S3_BUCKET")
        self.public_base = env("S3_PUBLIC_BASE").rstrip("/")
        endpoint, self.endpoint_note = normalize_endpoint(env("S3_ENDPOINT"))
        self.endpoint = endpoint

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=env("S3_KEY"),
            aws_secret_access_key=env("S3_SECRET"),
            region_name=env("S3_REGION", "auto"),
            config=Config(signature_version="s3v4"),
        )

    def save(self, fileobj, key, content_type=None):
        fileobj.seek(0)
        ctype = content_type or mimetypes.guess_type(key)[0] or "application/octet-stream"
        self.client.upload_fileobj(
            fileobj, self.bucket, key,
            ExtraArgs={"ContentType": ctype, "CacheControl": "public, max-age=31536000"},
        )
        return key

    def url(self, key):
        if self.public_base:
            return f"{self.public_base}/{key}"
        # 没配公开域名时退回端点直连（需要桶为公开读）
        ep = os.environ.get("S3_ENDPOINT", "").rstrip("/")
        return f"{ep}/{self.bucket}/{key}" if ep else key

    def delete(self, key):
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            pass


_backend = None


def get_storage(local_root=None):
    """返回当前配置的存储后端（单例）。"""
    global _backend
    if _backend is None:
        kind = os.environ.get("STORAGE_BACKEND", "local").lower()
        if kind == "s3":
            _backend = S3Storage()
        else:
            _backend = LocalStorage(local_root or os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "static", "uploads"))
    return _backend


def reset_storage():
    """仅供测试：清掉缓存的后端实例。"""
    global _backend
    _backend = None
