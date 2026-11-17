# EBCS 上线：GitHub + Render + Supabase + Cloudflare

此方案保留现有前端、FastAPI 接口、数据库字段、图片上传与权限功能。Render
只运行应用；Supabase 承载 PostgreSQL 和图片对象存储；Cloudflare 管理
`ekkobcs.dpdns.org` 的 DNS 与 HTTPS。

## 1. 推送代码前的安全规则

- 不提交 `.env`、Supabase 数据库密码、S3 access key / secret。
- 不提交 `data/sana_data.sqlite3`、`data/media/`、Docker 数据卷。
- `.env.example` 仅是字段模板，不能填真实凭据再提交。

## 2. Supabase（创建云端数据源）

1. 在 **Connect** 中选择 **Session pooler**，复制连接串。Render 的免费
   容器通常需要这个 IPv4 兼容连接方式，而不是默认 Direct connection。
2. 将连接串用于 Render 的 `DATABASE_URL`。本项目使用 SQLAlchemy，因此
   将开头替换为 `postgresql+psycopg://`，并确保尾部含
   `sslmode=require`。
3. 在 **Storage → Configuration → S3** 启用 S3 协议，创建一组 S3 access
   key / secret。把页面提供的 S3 endpoint、region、key、secret 填入
   Render 同名变量。密钥只保存在 Render，不放 GitHub。
4. 创建私有 bucket `ebcs-media`；如果 S3 key 拥有创建 bucket 权限，应用
   首次启动也会自动创建它。

## 3. Render（运行应用）

1. 登录 Render，选择 **New → Blueprint**，连接 GitHub 私有仓库
   `ekkoa2001/ebcs`。
2. Render 会读取根目录 `render.yaml`，确认 Web Service 名称为 `ebcs`。
3. 在部署前填入下列 Secret 环境变量：
   `DATABASE_URL`、`S3_ENDPOINT`、`S3_ACCESS_KEY`、`S3_SECRET_KEY`、
   `S3_REGION`。
4. 首次部署成功后，打开 Render 提供的 `onrender.com` 地址，完成登录与
   上传检查。首次连云端数据库时应用会自动执行 Alembic 建表迁移。
5. 免费实例会在无访问一段时间后休眠；首次唤醒可能需要约一分钟。正式
   生产可升级实例以避免冷启动。

## 4. 迁移本机业务数据和图片

首次云端建表不等于复制本机数据。应先做两份只读备份：

```powershell
docker compose exec -T postgres pg_dump -U ekko -d ekko --format=custom --file=/tmp/ebcs-before-cloud.dump
docker compose exec -T minio mc ls local/ekko-media
```

在提供 Supabase 的临时连接信息后，再执行一次性数据与媒体迁移，并逐项
校验：成员、项目、样板内容、评论、操作日志和图片预览。迁移完成后再把
云端正式域名切给团队使用。不要将上述备份或连接串推送到 GitHub。

## 5. Cloudflare（绑定正式域名）

1. 在 Render 服务 **Settings → Custom Domains** 添加
   `ekkobcs.dpdns.org`。
2. Render 会给出精确的 CNAME 目标。到 Cloudflare DNS 创建对应 CNAME；
   是否开启代理遵循 Render 页面提示。
3. 等 Render 显示证书已签发后，访问
   `https://ekkobcs.dpdns.org`，再将 Cloudflare SSL/TLS 设为 **Full
   (strict)**。
4. 最后在 Render 环境变量中确认 `EKKO_ALLOWED_HOSTS` 包含
   `ekkobcs.dpdns.org`，否则应用会拒绝未知 Host。

## 发布验收

- 登录、创建成员、权限控制可用；
- 品牌内容、营销方案、售后内容、竞品洞察、品牌历程均可读写；
- 上传后原图与 Web 预览均可打开；
- 新增、编辑、删除、恢复产生正确 Toast 和操作日志；
- 重新部署后数据仍在 Supabase，图片仍在 `ebcs-media`。
