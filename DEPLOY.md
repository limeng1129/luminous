# 部署到线上（GitHub → Render）

照着做,大约 10 分钟就能拿到一个能在线访问的真实网址(形如 `luminous-xxxx.onrender.com`,自带 HTTPS)。

**你需要两个免费账号(都用邮箱注册即可):**
- GitHub → https://github.com/signup
- Render → https://render.com （建议注册时选「Sign up with GitHub」,后面能少一步授权)

项目里已经放好了 `render.yaml`,Render 会自动读取它,不用你手动填任何构建命令。

---

## 第一步 · 把代码放上 GitHub

**方式一(不用装任何工具,推荐)**
1. 打开 https://github.com/new
2. Repository name 填 `luminous`,选 **Public**,点 **Create repository**
3. 在新页面点 **uploading an existing file** 这行链接
4. 把 `luminous` 文件夹里的**所有文件**(app.py、seed.py、requirements.txt、render.yaml、static、templates 等)**全选拖进去**
   - 注意:拖的是文件夹**里面的内容**,不是 luminous 这个文件夹本身
5. 点 **Commit changes**

**方式二(会用 git 的话更快)**
```bash
cd luminous
git init
git add .
git commit -m "Luminous photo site"
git branch -M main
git remote add origin https://github.com/你的用户名/luminous.git
git push -u origin main
```

---

## 第二步 · 在 Render 上一键部署

1. 登录 https://dashboard.render.com
2. 右上角 **New +** → 选 **Blueprint**
3. 选中你刚建的 `luminous` 仓库,点 **Connect**
   （如果第一次用,会让你授权 Render 访问 GitHub,点同意)
4. Render 自动读到 `render.yaml`,显示一个名为 **luminous** 的服务。直接点 **Apply / Create**
5. 等 3–5 分钟,状态变成 **Live** 就好了

> 也可以不走 Blueprint:**New +** → **Web Service** → 选仓库 → 它会自动识别成 Python 应用,
> 默认命令就是对的(`pip install -r requirements.txt` 和 `gunicorn app:app`)→ 拉到底选 **Free** → **Create**。

---

## 第三步 · 打开你的网站

服务页面顶部会有一个网址,像 `https://luminous-xxxx.onrender.com` —— 这就是你的站,发给谁都能访问。
以后每次你把代码推到 GitHub,Render 会自动重新部署。

---

## 几个要知道的点

- **首次打开会慢十几到六十秒**:免费实例闲置 15 分钟会休眠,有人访问时再唤醒。想一直保持在线,把服务升级到 Starter($7/月)。
- **上传的照片在免费版会被清空**:免费实例重启/重新部署后,磁盘会重置——示例图会自动重新生成,但访客上传的照片会没。要长期保存照片:
  1. 把实例升级到付费,在服务里 **Settings → Disks** 挂一块磁盘(比如挂到 `/var/data`)
  2. 在 **Environment** 里加两个变量:`LUMINOUS_UPLOAD_DIR=/var/data/uploads`、`LUMINOUS_DB=/var/data/luminous.db`
  （项目已支持这两个变量,加上就会把照片和数据库存到持久磁盘)
- **绑定自己的域名**:服务的 **Settings → Custom Domains → Add** 里填你的域名,它会给你一条 CNAME 记录,去域名商那边加上即可,HTTPS 自动配。

---

## 一键部署按钮(可选)

代码推上 GitHub 后,把下面链接里的 `你的用户名` 换成你的,存进 README 就有个按钮,点一下直接进 Render 部署页:

```
https://render.com/deploy?repo=https://github.com/你的用户名/luminous
```
