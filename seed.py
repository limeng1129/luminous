"""
首次运行时生成一批示例照片（本地生成，不依赖网络），并写入数据库。
生成的是按分类着色的抽象光影图 —— 之后你用真实照片替换即可。
"""
import io
import os
import random
import datetime
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from storage import get_storage
from db import get_db

# (分类, 宽, 高, 标题, 地点·时间, 初始喜欢数)
SEED_PHOTOS = [
    ("life",   640, 820, "周末早晨，咖啡在窗边慢慢凉",     "家 · 三月",       128),
    ("life",   820, 600, "楼下面包店，刚出炉的可颂",       "转角 · 清晨",     86),
    ("life",   700, 700, "它睡在午后的沙发上",             "客厅 · 周日",     203),
    ("life",   640, 800, "阳台的多肉又胖了一圈",           "阳台 · 立夏",     64),
    ("life",   820, 560, "一个人的火锅也很热闹",           "厨房 · 深夜",     97),
    ("life",   640, 840, "深夜书桌，只留一盏灯",           "书房 · 凌晨一点", 151),
    ("life",   820, 600, "洗好的衬衫在阳光里晃",           "窗台 · 午后",     73),
    ("travel", 900, 600, "清晨六点，山脊还裹着雾",         "黄山 · 去年秋",   312),
    ("travel", 640, 820, "海边小镇，蓝色的门",             "圣托里尼 · 六月", 188),
    ("travel", 820, 560, "火车穿过稻田，光一格格扫过",     "越后 · 初夏",     142),
    ("travel", 640, 800, "古城巷子，转角遇见一只猫",       "丽江 · 十月",     167),
    ("travel", 900, 600, "雪山脚下的湖，静得像镜子",       "贝加尔 · 冬",     276),
    ("travel", 640, 820, "陌生城市的地铁，回家的人群",     "东京 · 傍晚",     98),
    ("travel", 820, 600, "沙漠的夜，星星低得能碰到",       "敦煌 · 八月",     254),
    ("love",   640, 840, "你转身那刻，风刚好停",           "江边 · 黄昏",     421),
    ("love",   820, 560, "十指相扣，走过整条街",           "老城 · 春末",     333),
    ("love",   700, 700, "分你一半的耳机",                 "地铁 · 周五",     210),
    ("love",   640, 820, "第一次一起做饭，厨房乱成一团",   "出租屋 · 冬夜",   265),
    ("love",   820, 600, "你睡着了，我舍不得关灯",         "家 · 深夜",       298),
    ("love",   640, 800, "雨天共一把伞，肩膀都湿了",       "街口 · 梅雨",     187),
    ("love",   820, 560, "蜡烛前，你许了什么愿",           "小屋 · 生日",     244),
    ("nature", 640, 820, "春天第一片新叶",                 "公园 · 三月",     112),
    ("nature", 820, 600, "雨后森林，空气是绿色的",         "林间 · 谷雨",     176),
    ("nature", 900, 600, "海浪反复，把石头磨圆",           "礁石 · 傍晚",     143),
    ("nature", 640, 840, "银杏落了一地金黄",               "街道 · 深秋",     231),
    ("nature", 820, 560, "山顶的云海，翻涌不停",           "峰顶 · 拂晓",     289),
    ("nature", 640, 800, "溪水很凉，脚趾都醒了",           "山谷 · 盛夏",     88),
    ("nature", 900, 600, "夕阳把麦田染成蜜色",             "田野 · 立秋",     194),
]

# 每个分类的双色渐变（深 → 亮）
PALETTE = {
    "life":   ("#2a1e12", "#e0a94e"),
    "travel": ("#123330", "#57c9c0"),
    "love":   ("#331420", "#ef8aa0"),
    "nature": ("#182a14", "#93c06d"),
}


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def vertical_gradient(w, h, top, bottom):
    strip = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        strip.putpixel(
            (0, y),
            tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)),
        )
    return strip.resize((w, h))


def glow_blob(w, h, color, cx, cy, r):
    layer = Image.new("RGB", (w, h), (0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    return layer.filter(ImageFilter.GaussianBlur(r * 0.55))


def make_image(w, h, dark_hex, light_hex, seed):
    rnd = random.Random(seed)
    top = hex2rgb(dark_hex)
    light = hex2rgb(light_hex)
    bottom = tuple(int(c * 0.68) for c in light)  # 收暗一点，避免荧光感

    img = vertical_gradient(w, h, top, bottom)

    for _ in range(rnd.randint(2, 3)):
        cx = rnd.randint(0, w)
        cy = rnd.randint(0, h)
        r = rnd.randint(int(min(w, h) * 0.30), int(min(w, h) * 0.60))
        col = tuple(min(255, int(c * rnd.uniform(0.45, 0.85))) for c in light)
        img = ImageChops.screen(img, glow_blob(w, h, col, cx, cy, r))

    # 细腻颗粒
    noise = Image.effect_noise((w, h), 22).convert("L").convert("RGB")
    img = Image.blend(img, noise, 0.05)

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    buf.seek(0)
    return buf


def seed_if_empty(upload_dir):
    """库里没有照片时生成一批示例。加锁保证多进程只播一次。"""
    with get_db() as conn:
        conn.lock_for_seeding()
        n = conn.execute("SELECT COUNT(*) AS n FROM photos").fetchone()["n"]
        if n > 0:
            return

        os.makedirs(upload_dir, exist_ok=True)
        now = datetime.datetime.now().isoformat(timespec="seconds")
        for i, (cat, w, h, title, sub, likes) in enumerate(SEED_PHOTOS):
            dark, light = PALETTE[cat]
            fn = f"seed_{i:02d}.jpg"
            buf = make_image(w, h, dark, light, seed=i * 7 + 3)
            get_storage(upload_dir).save(buf, fn, "image/jpeg")
            conn.execute(
                """INSERT INTO photos
                   (category, filename, url, title, subtitle, width, height, likes, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (cat, fn, None, title, sub, w, h, likes, now),
            )
        print(f"  已生成 {len(SEED_PHOTOS)} 张示例照片。")
