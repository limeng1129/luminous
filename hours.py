"""
此刻 —— 一天二十四小时的光。

要知道一张照片属于哪个钟点，按可靠程度依次尝试：

  1. EXIF 里的拍摄时间     手机和相机自带，最准
  2. 说明里的时间词        「清晨」「傍晚」「深夜」
  3. 认不出就留空          不用亮度去猜 —— 一张中午的室内暗照
                          会被误判成夜里，那是假数据

留空的照片不会出现在时辰视图里。宁可少，不可错。
"""
import re

# 时间词 -> 代表钟点。取该时段中间偏典型的那个小时。
WORDS = [
    (("凌晨", "半夜"), 3),
    (("清晨", "黎明", "拂晓", "日出", "破晓"), 6),
    (("早晨", "早上", "一早"), 8),
    (("上午",), 10),
    (("中午", "正午", "晌午"), 12),
    (("午后", "下午"), 15),
    (("傍晚", "黄昏", "日落", "夕阳", "落日", "薄暮"), 18),
    (("入夜", "晚上", "夜里", "夜晚", "晚间"), 21),
    (("深夜", "午夜"), 23),
]

# 每个钟点的说法，显示用
LABELS = {
    0: "午夜", 1: "凌晨", 2: "凌晨", 3: "凌晨", 4: "破晓", 5: "破晓",
    6: "清晨", 7: "清晨", 8: "早晨", 9: "上午", 10: "上午", 11: "上午",
    12: "正午", 13: "午后", 14: "午后", 15: "午后", 16: "下午", 17: "傍晚",
    18: "黄昏", 19: "入夜", 20: "夜里", 21: "夜里", 22: "深夜", 23: "深夜",
}


def hour_from_exif(fileobj):
    """从 EXIF 读拍摄时间。没有就返回 None。"""
    try:
        from PIL import Image
        fileobj.seek(0)
        im = Image.open(fileobj)
        exif = im.getexif()
        if not exif:
            return None
        # DateTimeOriginal(36867) 在 Exif 子 IFD 里；DateTime(306) 在主 IFD
        raw = None
        try:
            sub = exif.get_ifd(0x8769)
            raw = sub.get(36867) or sub.get(36868)
        except Exception:
            pass
        raw = raw or exif.get(306)
        if not raw:
            return None
        m = re.search(r"\b(\d{1,2}):(\d{2}):(\d{2})", str(raw))
        if not m:
            return None
        h = int(m.group(1))
        return h if 0 <= h <= 23 else None
    except Exception:
        return None


def hour_from_text(*texts):
    """从说明文字里认时间词。"""
    blob = " ".join(str(t) for t in texts if t)
    if not blob:
        return None
    for words, hour in WORDS:
        for w in words:
            if w in blob:
                return hour
    # 「六点」「18:30」这类也认
    m = re.search(r"(\d{1,2})\s*[:：]\s*\d{2}", blob)
    if m and 0 <= int(m.group(1)) <= 23:
        return int(m.group(1))
    m = re.search(r"([一二三四五六七八九十]|\d{1,2})\s*点", blob)
    if m:
        cn = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
              "七": 7, "八": 8, "九": 9, "十": 10}
        v = cn.get(m.group(1))
        if v is None:
            try:
                v = int(m.group(1))
            except ValueError:
                v = None
        if v is not None and 0 <= v <= 23:
            # 「六点」配合上下文判断早晚
            if v < 12 and any(w in blob for w in ("晚", "夜", "傍")):
                v += 12
            return v
    return None


def detect_hour(fileobj=None, *texts):
    """返回 (钟点, 来源)。认不出返回 (None, None)。"""
    if fileobj is not None:
        h = hour_from_exif(fileobj)
        if h is not None:
            return h, "exif"
    h = hour_from_text(*texts)
    if h is not None:
        return h, "text"
    return None, None


def _mix(colors):
    """把一组颜色平均成一个。"""
    if not colors:
        return None
    rs = gs = bs = 0
    for c in colors:
        c = (c or "#808080").lstrip("#")
        if len(c) != 6:
            c = "808080"
        rs += int(c[0:2], 16)
        gs += int(c[2:4], 16)
        bs += int(c[4:6], 16)
    n = len(colors)
    return f"#{rs//n:02x}{gs//n:02x}{bs//n:02x}"


def hour_data(photos):
    """按钟点归拢照片，算出每个钟点的代表色。"""
    buckets = [{"hour": h, "label": LABELS[h], "photos": [], "rgb": None}
               for h in range(24)]
    unknown = 0
    for p in photos:
        h = p.get("hour")
        if h is None or not (0 <= h <= 23):
            unknown += 1
            continue
        buckets[h]["photos"].append({
            "id": p["id"], "src": p["src"], "title": p["title"],
            "subtitle": p.get("subtitle") or "", "rgb": p.get("rgb") or "#808080",
        })

    for b in buckets:
        b["count"] = len(b["photos"])
        b["rgb"] = _mix([x["rgb"] for x in b["photos"]])

    known = sum(b["count"] for b in buckets)
    peak = max(buckets, key=lambda b: b["count"]) if known else None
    return {
        "buckets": buckets,
        "known": known,
        "unknown": unknown,
        "peak": {"hour": peak["hour"], "label": peak["label"], "count": peak["count"]}
        if peak and peak["count"] else None,
    }
