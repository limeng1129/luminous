"""
把 OneDrive / SharePoint 的「分享链接」转成可以直接放进 <img> 的直链。

用法：在网站的「图片链接」框里粘贴 OneDrive 分享链接即可，后端会自动转换。

支持两种：
1) 个人版 OneDrive 短链  https://1drv.ms/i/s!AxxxxYYY
   走微软公开的 shares API（把链接 base64 编码后拼进去），不需要登录、不需要密钥。
2) 企业版 / 学校版 SharePoint 链接  https://xxx-my.sharepoint.com/:i:/g/personal/...
   加上 download=1 参数取直链。

注意：分享权限必须设成「拥有链接的任何人都可查看」，否则匿名访问会被拒绝。
"""
import base64
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

ONEDRIVE_HOSTS = ("1drv.ms", "onedrive.live.com")


def is_onedrive_link(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host.endswith(ONEDRIVE_HOSTS) or host.endswith("sharepoint.com")


def to_direct_link(url: str) -> str:
    """把分享链接转成直链；不是 OneDrive 链接就原样返回。"""
    if not url:
        return url
    try:
        parsed = urlparse(url)
    except Exception:
        return url
    host = (parsed.hostname or "").lower()

    # 个人版 OneDrive：base64url 编码后走 shares API
    if host.endswith(ONEDRIVE_HOSTS):
        b64 = base64.b64encode(url.encode("utf-8")).decode("ascii")
        token = "u!" + b64.rstrip("=").replace("/", "_").replace("+", "-")
        return f"https://api.onedrive.com/v1.0/shares/{token}/root/content"

    # 企业版 / 学校版 SharePoint：加 download=1
    if host.endswith("sharepoint.com"):
        q = parse_qs(parsed.query)
        q["download"] = ["1"]
        return urlunparse(parsed._replace(
            query=urlencode({k: v[0] for k, v in q.items()})))

    return url


if __name__ == "__main__":
    demo = "https://1drv.ms/i/s!AmpleShareToken123"
    print("原链接:", demo)
    print("直链  :", to_direct_link(demo))
