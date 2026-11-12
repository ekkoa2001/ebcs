# 当前架构状态

更新时间：2026-11-12

## 结论

当前项目处于“V1 界面与业务逻辑运行在 FastAPI 兼容层之上”的过渡状态，不是完整的新架构。

## 当前真实运行链路

```text
浏览器
  → web/ 中的 V1 HTML、CSS、JavaScript
  → FastAPI app.main
  → app.legacy 兼容分发
  → server.py / team_server.py 旧业务处理器
  → 本地默认 SQLite + data/media
```

Docker 环境另行提供 PostgreSQL、Redis 和 MinIO，但并不代表所有业务已迁移。

## 已完成

- V1 页面按 CSS、JavaScript 模块整理，界面保持不变。
- FastAPI 启动入口和旧接口兼容分发。
- Alembic 基础迁移。
- PostgreSQL、Redis、MinIO、Nginx 的 Docker Compose 底座。
- 会话、RBAC、审计、对象存储的部分基础能力。
- V1 视觉基线截图和 Playwright 配置。
- 用户、登录、密码、个人资料、团队、RBAC、会话撤销和结构化审计已迁移到独立服务。
- 老 UI 的身份与账号管理地址已经接入新服务，页面外观和调用方式不变。
- PostgreSQL 建表依赖排序和旧游标兼容问题已修复。
- Docker 环境已通过完整启动验证，首页返回 200。
- 创意钩子已迁移到规范化 `creative_hooks` 表，具备独立 API、权限、乐观锁、归档、恢复、审计和老 UI 双向兼容。

## 尚未完成

- Vue 前端没有承载页面；当前 App.vue 为空。
- creative、content、marketing、analytics、competitors 等新路由尚未实现业务接口。
- V1 数据仍以旧表和旧处理器为主。
- SQLite 到 PostgreSQL 的迁移、核对和回滚流程未完整验收。
- 正式对象存储切换、权限、签名 URL 和全量图片迁移未完整验收。
- README 中规划的新业务模块尚未全部实现。
- 生产密钥、域名、HTTPS、监控、告警和自动备份尚未配置。

## 目录职责

| 目录 | 当前职责 | 处理原则 |
| --- | --- | --- |
| `web/` | V1 生产界面和浏览器逻辑 | 视觉冻结，渐进接新 API |
| `server/` | FastAPI、旧处理器、迁移和后端基础设施 | 逐模块替换兼容层 |
| `frontend/` | 尚未启用的 Vue/Vite 宿主 | 暂不作为生产入口 |
| `data/` | 本地数据库、媒体和备份 | 不提交 Git，独立备份 |
| `deploy/` | Nginx 与部署说明 | 补齐生产配置模板 |
| `tests/` | 视觉回归测试 | 扩展 API、权限和端到端测试 |
| `docs/` | 审计、架构、验收与上线文档 | 作为唯一实施记录 |

## 迁移原则

1. 保持 `web/` 的现有视觉与交互，不做无关重构。
2. 新业务先实现数据库模型、服务层和 `/api/v1`，再接现有页面。
3. 每迁移一个模块，补齐测试后再关闭对应旧处理器分支。
4. SQLite 保留为迁移来源；生产数据以 PostgreSQL 为准。
5. 原图进入私有对象存储；数据库只保存元数据和对象键。
6. 未通过视觉回归、权限测试和数据核对，不得标记模块完成。
