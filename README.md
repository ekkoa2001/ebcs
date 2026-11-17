# Ekko Brand Content Strategy (EBCS)

EBCS 是用于管理品牌创意、品牌内容、营销方案、售后内容、竞品洞察、品牌
历程与广告复盘的团队工作台。

## 本地运行

安装 Docker Desktop 后，在项目根目录执行：

```powershell
docker compose up -d --build
```

打开 <http://127.0.0.1>。FastAPI 直接调试端口为
<http://127.0.0.1:8875>。

## 架构

- `web/`：当前在线使用的浏览器界面与模块；
- `server/`：FastAPI、权限、业务 API、Alembic 迁移；
- `data/`：本地开发数据与媒体，**不纳入 Git**；
- `docker-compose.yml`：本地 PostgreSQL、Redis、MinIO 与 Nginx；
- `render.yaml`：Render 云端部署蓝图。

## 发布到云端

生产环境使用 GitHub + Render + Supabase + Cloudflare。完整步骤见
[docs/DEPLOY_RENDER_SUPABASE.md](docs/DEPLOY_RENDER_SUPABASE.md)。

> 不要提交 `.env`、数据库连接串、Supabase S3 密钥、本地 SQLite 数据库或
> 用户上传的原图。
