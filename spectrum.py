"""
光谱 —— 把每张照片压缩成它的「一道光」。

对每张照片提取三个值：
  rgb   主色（十六进制）—— 用中位切分量化取最主要的一块颜色
  light 明度 0–100      —— 用人眼感知加权，不是简单平均
  warm  冷暖 -100–100   —— 红多为暖，蓝多为冷

这三个值让照片可以按「时间 / 冷暖 / 明暗」重新排列，
排出来的那条光带，就是这些照片共同的样子。
"""
import io

from db import get_db


def _luminance(r, g, b):
    """人眼对绿色最敏感、蓝色最不敏感，所以加权而非平均。"""
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 * 100


def analyze_image(fileobj):
    """返回 (rgb十六进制, 明度0-100, 冷暖-100~100)。失败时返回中性值。"""
    try:
        from PIL import Image
        fileobj.seek(0)
        im = Image.open(fileobj)
        im = im.convert("RGB")
        im.thumbnail((90, 90))

        # 量化成几块主要颜色，取占比最大的那块作为主色
        q = im.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
        palette = q.getpalette()
        counts = q.getcolors() or []
        if counts:
            counts.sort(reverse=True)          # [(像素数, 调色板序号), ...]
            idx = counts[0][1]
            r, g, b = palette[idx * 3: idx * 3 + 3]
        else:
            r = g = b = 128

        # 明度用整张图的平均，比主色更能代表「这张照片有多亮」
        px = list(im.getdata())
        n = max(1, len(px))
        ar = sum(p[0] for p in px) / n
        ag = sum(p[1] for p in px) / n
        ab = sum(p[2] for p in px) / n

        light = round(_luminance(ar, ag, ab))
        warm = round(max(-100, min(100, (ar - ab) / 255 * 200)))
        return f"#{r:02x}{g:02x}{b:02x}", light, warm
    except Exception:
        return "#808080", 50, 0


def analyze_stored(src, upload_dir):
    """给已经存好的照片补算颜色。src 可能是本地路径或对象存储的公开地址。"""
    try:
        if src.startswith("/uploads/"):
            import os
            path = os.path.join(upload_dir, src.rsplit("/", 1)[-1])
            with open(path, "rb") as f:
                return analyze_image(io.BytesIO(f.read()))
        if src.startswith("http"):
            import urllib.request
            req = urllib.request.Request(src, headers={"User-Agent": "luminous"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return analyze_image(io.BytesIO(r.read()))
    except Exception:
        pass
    return None


def save_colors(photo_id, rgb, light, warm):
    with get_db() as c:
        c.execute("UPDATE photos SET rgb=?, light=?, warm=? WHERE id=?",
                  (rgb, light, warm, photo_id))


def spectrum_data(photos):
    """把照片列表整理成光带需要的数据，并算好三种排法的顺序。"""
    items = []
    for p in photos:
        items.append({
            "id": p["id"],
            "src": p["src"],
            "title": p["title"],
            "subtitle": p.get("subtitle") or "",
            "rgb": p.get("rgb") or "#808080",
            "light": p.get("light") if p.get("light") is not None else 50,
            "warm": p.get("warm") if p.get("warm") is not None else 0,
            "created_at": p.get("created_at") or "",
        })

    def order_by(key, reverse=False):
        idx = sorted(range(len(items)), key=lambda i: items[i][key], reverse=reverse)
        return idx

    return {
        "items": items,
        "orders": {
            # 时间：按 id 从早到晚
            "time": sorted(range(len(items)), key=lambda i: items[i]["id"]),
            # 冷暖：从最冷排到最暖
            "warm": order_by("warm"),
            # 明暗：从最暗排到最亮
            "light": order_by("light"),
        },
    }


def count_missing():
    """还有多少张照片没算过颜色。"""
    with get_db() as c:
        r = c.execute("SELECT COUNT(*) AS n FROM photos WHERE rgb IS NULL").fetchone()
    return r["n"]
