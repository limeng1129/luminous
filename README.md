# 流光 · Luminous

一个把生活、旅行、爱情等瞬间「留在光里」的图片分享网站。
深色影院感界面 + 瀑布流画廊 + 真实的照片上传与本地存储。

前端 = 原生 HTML / CSS / JS(无框架),后端 = Flask + SQLite。
照片保存在**你自己运行的这台机器上**,不上传任何第三方。

---

## 快速开始

需要 Python 3.9 以上。

```bash
# 1. 进入项目目录
cd luminous

# 2.（可选但推荐)创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Windows 用 .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动
python app.py
```

然后浏览器打开 **http://127.0.0.1:5000**

> 第一次运行会自动生成 28 张示例照片并建好数据库,大约一两秒。
> 之后你可以随时用界面右上角的「分享」上传自己的照片,或把示例照片删掉。

---

## 功能一览

- **瀑布流画廊** —— 悬停照片会抬起、微倾,并透出所属分类的光晕
- **四个章节** —— 生活 / 旅行 / 爱情 / 自然,各有身份色,点击平滑筛选
- **搜索** —— 按标题、地点关键词实时过滤
- **影院感灯箱** —— 点开放大,支持左右箭头 / ESC / 键盘操作、点赞、删除
- **上传自己的照片** —— 点击选择本地图片或**拖拽进来**,也支持粘贴图片链接;写一句话、选章节即可发布
- **点赞** —— 保存在数据库;你点过的赞记在本地浏览器,换机器不会丢失服务器计数
- **删除** —— 在灯箱里删除照片,同时移除服务器上的图片文件
- **完全响应式** —— 手机、平板、桌面都适配;支持「减弱动态效果」的系统偏好

---

## 项目结构

```
luminous/
├── app.py                # Flask 后端 + REST API
├── seed.py               # 首次运行生成示例照片
├── requirements.txt
├── luminous.db           # SQLite 数据库(首次运行自动生成)
├── static/
│   ├── css/style.css     # 全部样式(设计系统)
│   ├── js/app.js         # 前端逻辑
│   └── uploads/          # 上传 & 生成的照片都存这里
└── templates/
    ├── index.html        # 画廊主页
    └── about.html        # 关于页
```

## API

| 方法   | 路径                      | 作用                          |
|--------|---------------------------|-------------------------------|
| GET    | `/api/photos?cat=&q=`     | 照片列表(可按分类 / 关键词过滤) |
| POST   | `/api/photos`             | 上传照片(文件或链接)          |
| POST   | `/api/photos/<id>/like`   | 点赞 / 取消赞                 |
| DELETE | `/api/photos/<id>`        | 删除照片                      |
| GET    | `/api/stats`              | 统计数据                      |

---

## 常见改动

**换成你自己的照片**:直接用界面的「分享」上传,或把 `static/uploads/` 里的示例图删掉重新传。

**改分类 / 颜色**:同时改两处 —— 后端 `app.py` 里的 `CATEGORIES`,和前端 `static/js/app.js` 里的 `CATS`(两边的键要一致)。分类色也在这两处。

**改文案 / 标题**:主页文字在 `templates/index.html`,示例照片的句子在 `seed.py` 的 `SEED_PHOTOS`。

**从头再来**:删掉 `luminous.db` 和 `static/uploads/` 里的图片,再启动即可重新生成示例。

---

## 想更进一步?

这套结构可以平滑扩展:加用户登录与个人主页、评论、标签、图片压缩与缩略图、
换成 PostgreSQL、或部署到服务器(用 gunicorn + nginx)。需要的话告诉我方向。

---

# 上线部署 —— 让别人能通过网址访问

下面三条路都验证可行。**账号注册、买域名、DNS 解析这几步需要你自己操作**(要实名和付款),其余配置我已经在项目里准备好了。

> ⚠️ 一个关键点:这个站会保存用户上传的照片。很多**免费**平台的磁盘是"临时"的——重启或重新部署后上传的照片会被清空(示例图会自动重新生成,但你传的会没)。所以下面每条路我都标了照片能不能长期保存。

## 路线 A ·（推荐,最快免费上线且照片不丢) PythonAnywhere

免费、自带真实网址 `你的用户名.pythonanywhere.com`、**磁盘持久**(上传的照片会一直保存)、不需要信用卡。最适合先把站快速挂上去。

1. 注册 https://www.pythonanywhere.com （免费 Beginner 账户)
2. 进 **Files**,把项目上传上去(或开一个 **Bash console** 执行
   `git clone 你的仓库地址`),让代码在 `/home/你的用户名/luminous`
3. Bash console 里安装依赖:
   ```bash
   cd ~/luminous
   pip install --user -r requirements.txt
   ```
4. 进 **Web** 标签 → **Add a new web app** → 选 **Manual configuration** → **Python 3.10**
5. 在 Web 页面里把 **Source code** 设为 `/home/你的用户名/luminous`
6. 点开它给的 **WSGI configuration file**,清空,换成:
   ```python
   import sys
   path = '/home/你的用户名/luminous'
   if path not in sys.path:
       sys.path.insert(0, path)
   from wsgi import application
   ```
7. 回 Web 页面点绿色的 **Reload**。打开 `https://你的用户名.pythonanywhere.com` 就是你的站。

想用**自己的域名**(如 `myphotos.com`):PythonAnywhere 的自定义域名需要升级到 Hacker 套餐(约 $5/月)。免费账户就用它给的子域名。

## 路线 B ·（GitHub 一键) Render

连 GitHub 仓库自动部署,免费子域名 `luminous-xxxx.onrender.com`,自带 HTTPS,**支持绑自己的域名**(免费也能绑)。项目里已经放了 `render.yaml`。

1. 把项目推到一个 GitHub 仓库
2. 注册 https://render.com → **New +** → **Web Service** → 连你的仓库
3. Render 会读 `render.yaml` 自动配置,点 **Create**。几分钟后给你一个网址
4. 绑自己的域名:服务的 **Settings → Custom Domains** 里添加,按提示去域名商加一条 CNAME 记录

⚠️ 免费实例:闲置会休眠(首次打开慢十几秒),且磁盘临时——上传的照片重启会丢。要长期保存照片,把实例升级到付费(Starter $7/月)并按 `render.yaml` 注释里的说明挂一块磁盘。

## 路线 C ·（自己的域名 + 完全掌控,也最适合面向国内) 云服务器

买一台轻量服务器 + 一个域名,最稳、最快、最像"真正的网站"。国内用阿里云/腾讯云轻量应用服务器(约 ¥24–60/月),海外用香港/新加坡节点。

**1. 上传代码并安装**(服务器用 Ubuntu,以你的用户名和路径为准)
```bash
sudo apt update && sudo apt install -y python3-venv nginx
cd ~ && git clone 你的仓库 luminous && cd luminous
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. 用 systemd 常驻运行**(新建 `/etc/systemd/system/luminous.service`)
```ini
[Unit]
Description=Luminous
After=network.target

[Service]
User=你的用户名
WorkingDirectory=/home/你的用户名/luminous
ExecStart=/home/你的用户名/luminous/.venv/bin/gunicorn wsgi:app --workers 2 --bind 127.0.0.1:8000 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now luminous
```

**3. Nginx 反向代理**(新建 `/etc/nginx/sites-available/luminous`)
```nginx
server {
    listen 80;
    server_name 你的域名.com www.你的域名.com;
    client_max_body_size 15M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    # 上传的图片直接由 nginx 提供,更快
    location /uploads/ {
        alias /home/你的用户名/luminous/static/uploads/;
    }
}
```
```bash
sudo ln -s /etc/nginx/sites-available/luminous /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**4. 域名解析**:在域名商把一条 **A 记录**指向你服务器的公网 IP。

**5. 免费 HTTPS**:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 你的域名.com -d www.你的域名.com
```

照片长期保存:天然就在服务器磁盘上,不会丢。

---

## 关于域名

- **免费子域名**:路线 A/B 直接给你一个 `xxx.pythonanywhere.com` / `xxx.onrender.com`,是真实、永久、能分享的 HTTPS 网址。
- **自己的域名**(如 `myphotos.com`):在域名商买(阿里云/腾讯云约 ¥30–60/年,或海外 Namecheap/Cloudflare),再按上面对应路线绑定。

## 面向中国大陆访问的两个提醒

1. **ICP 备案**:如果域名指向的是**中国大陆境内**的服务器(阿里云/腾讯云大陆节点),按规定需要先做 ICP 备案(在服务商控制台申请,通常几天到两三周)。用**香港/新加坡等境外**服务器或境外平台则不需要备案,但大陆访问速度看节点(港/新/日一般可接受)。
2. **字体加载**:页面用了 Google Fonts。大陆访问 Google 字体可能慢或加载不出(会退回系统字体,不影响功能,只是字体没那么好看)。要面向大陆用户,可把两个 HTML 文件里字体链接的 `fonts.googleapis.com` / `fonts.gstatic.com` 换成国内镜像(如 `fonts.loli.net` / `gstatic.loli.net`),或改为自托管字体。需要的话我可以帮你改好。
