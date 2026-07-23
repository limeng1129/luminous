# 照片存到哪里 —— 三种方案

免费版 Render 的磁盘是临时的：**重新部署或休眠唤醒后，访客上传的照片会被清空**（示例图会自动重新生成）。
想让照片长期保存，选下面任意一种。项目已经全部支持，只需要加几个环境变量，代码一行都不用改。

---

## 方案一 · Cloudflare R2（推荐，免费 10GB，最适合你的情况）

对象存储才是给网站存图片用的东西：不限流、全球 CDN 加速、链接永久有效。
R2 的免费额度是 **10GB 存储 + 流量不额外收费**，对个人相册来说非常够用，而且**不需要绑信用卡也能开**。

**1. 开通并建桶**
1. 注册 https://dash.cloudflare.com
2. 左侧 **R2** → **Create bucket**，名字填 `luminous-photos`
3. 进桶 → **Settings** → **Public access** → 开启 **R2.dev subdomain**
   会得到一个公开地址，形如 `https://pub-xxxxxxxx.r2.dev` —— 记下来

**2. 拿密钥**
R2 首页 → **Manage R2 API Tokens** → **Create API Token** → 权限选 **Object Read & Write**
记下 **Access Key ID**、**Secret Access Key**，以及页面上的 **Endpoint**
（形如 `https://<账号ID>.r2.cloudflarestorage.com`）

**3. 在 Render 里填环境变量**
进你的服务 → **Environment** → **Add Environment Variable**，加这 6 条：

| Key | Value |
|---|---|
| `STORAGE_BACKEND` | `s3` |
| `S3_BUCKET` | `luminous-photos` |
| `S3_KEY` | 你的 Access Key ID |
| `S3_SECRET` | 你的 Secret Access Key |
| `S3_ENDPOINT` | `https://<账号ID>.r2.cloudflarestorage.com` |
| `S3_PUBLIC_BASE` | `https://pub-xxxxxxxx.r2.dev` |

保存后 Render 会自动重新部署。之后上传的照片就永久存在 R2 里了。

> 同样的 6 个变量也适用于 **Backblaze B2**（免费 10GB）、**AWS S3**、**阿里云 OSS**、**腾讯云 COS**，
> 只是 `S3_ENDPOINT` 换成对应服务商的端点。AWS S3 可以把 `S3_ENDPOINT` 留空。

---

## 方案二 · OneDrive（只适合放你自己已有的照片）

你可以把 OneDrive 里已有的照片，通过**分享链接**放进网站——不需要密钥，不用配置。

1. 在 OneDrive 里选中照片 → **共享** → 权限改成 **拥有链接的任何人都可查看** → 复制链接
2. 在网站点「分享」→ 把链接粘进**「图片链接」**框 → 写标题、选章节 → 发布

后端会自动把分享链接转成能直接显示的直链（个人版走微软的 shares 接口，企业版加 `download=1`）。

**但请注意它的局限**，这是我建议你只拿它当补充的原因：
- OneDrive 是给文件同步设计的，不是给网页访问设计的。访问量一大**会被微软限流**，图片就加载不出来
- 你在 OneDrive 里**移动或改名**这张照片，网站上的链接就会失效
- 加载速度明显慢于对象存储（没有 CDN）
- 网站的「上传」功能**没法写入** OneDrive——那需要 OAuth 授权和定期刷新令牌，对个人站点来说维护成本不值得

一句话：**拿它展示你已有的照片可以，别拿它当网站的存储后端。**

---

## 方案三 · iCloud —— 做不到

Apple 没有开放给第三方服务器读写 iCloud Drive 的通用接口。
CloudKit 只服务于苹果生态内的 App，需要 99 美元/年的开发者账号，且不适合这种网页场景。
iCloud 共享相册的网页链接是动态渲染的，也拿不到稳定的图片直链。

**结论：iCloud 这条路走不通**，不是配置问题，是接口层面就没有。你的 iCloud 空间没法给网站用。

---

## 顺带一提：数据库也可以一起持久化

照片存到 R2 之后，还剩 `luminous.db`（记标题、点赞数）在临时磁盘上。要它也不丢，两个办法：

- **简单**：Render 服务升级到 Starter（$7/月）→ **Settings → Disks** 挂 1GB 磁盘到 `/var/data`
  → 环境变量加 `LUMINOUS_DB=/var/data/luminous.db`
- **免费**：Render 免费送 PostgreSQL 实例，但需要把代码从 SQLite 换成 Postgres（改动不大，需要的话我可以帮你改）

只用 R2 不动数据库也能用，只是重新部署后照片记录会重置（照片文件本身还安全地留在 R2 里）。

---

# 配好之后怎么检查

项目内置了存储自检，**直接在浏览器打开**：

```
https://你的网址.onrender.com/health/storage
```

它会真的往你的 R2 里写一个测试文件、从公开地址读回来核对内容、再删掉，
所以结果反映的是真实状态。每一项都会给出通过 / 警告 / 失败，失败的会直接告诉你怎么修。

想在本地检查，把环境变量设好后运行：`python check_storage.py`

**可选：给自检页加把锁。** 在 Render 的环境变量里加一条 `HEALTH_TOKEN`，值随便设一个密码，
之后访问就要带上 `?token=你设的值`，别人打不开。不加也不会泄露密钥（密钥始终是打码显示的）。
