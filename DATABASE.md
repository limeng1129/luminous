# 让照片记录永久保存（免费 Postgres）

照片文件已经存在 R2 里了，但记标题、点赞数的数据库还在 Render 的临时磁盘上——
重新部署一次，画廊就会重置回 28 张示例（你传的照片文件还安全地躺在 R2，只是网站"忘了"它们）。

接一个免费的外部 Postgres 就能彻底解决。**代码已经支持，你只要拿一个连接字符串填进 Render。**
本地开发不受影响：没设 `DATABASE_URL` 时程序自动用 SQLite，你本地什么都不用装。

---

## 用 Neon（推荐，免费额度不过期，注册最快）

1. 打开 https://neon.tech → **Sign up**（可以用 GitHub 账号直接登录）
2. 登录后它会让你建一个项目：名字填 `luminous`，区域选离你近的（比如 Singapore / Frankfurt），
   点 **Create project**
3. 建好后页面上会直接给你一段 **Connection string**，形如：
   ```
   postgresql://用户名:密码@ep-xxxx-xxxx-pooler.区域.aws.neon.tech/neondb?sslmode=require
   ```
   **点复制按钮把它整段复制下来。** 如果有 "Pooled connection" 的选项，优先选它。
4. 回 Render → 你的服务 → **Environment** → **Add Environment Variable**：

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | 刚复制的那一整段 |

5. 点 **Save Changes**。Render 会自动重新部署，几分钟后就好了。

---

## 或者用 Supabase

1. 打开 https://supabase.com → 注册 → **New project**
2. 设一个数据库密码（**记下来**，等下要用）
3. 项目建好后进 **Project Settings → Database → Connection string → URI**
4. 复制那段字符串，把里面的 `[YOUR-PASSWORD]` 换成你刚设的密码
5. 同样填进 Render 的 `DATABASE_URL`

---

## 怎么确认成功了

部署完成后打开 `你的网址/health/storage`，看「数据库」那一行：

- ✅ 显示 **Postgres @ ...｜数据永久保存，重新部署不会丢** → 成功了
- ❌ 显示连不上 → 多半是连接字符串没复制全，或密码没替换。整段重新复制一次

成功之后，你上传的照片就真正稳了：**文件在 R2，记录在 Postgres，两边都不会因为重新部署而丢失。**

---

## 说明几点

- **原来的 28 张示例照片会重新生成一次**（新数据库是空的），这是正常的。
- **切换前上传的照片记录会丢**（文件还在 R2 里）。如果那些照片你想留，切换后重新发布一下即可。
- 本地跑 `python app.py` 时不用管这个，没设 `DATABASE_URL` 就自动用 SQLite。
