# 当前架构状态

更新时间：2026-11-13

## 结论

项目采用“冻结 V1 视觉 + 渐进式新架构”的运行方式。浏览器继续使用 `web/` 中已经验收的 V1 HTML/CSS/JavaScript；业务数据、权限和文件由 FastAPI、PostgreSQL、Redis 与 MinIO 承载。部署上线工作按要求暂缓。

```text
Browser / V1 UI
  -> Nginx (local port 80)
  -> FastAPI /api/v1 + legacy compatibility routes
  -> service layer / RBAC / audit / optimistic locking
  -> PostgreSQL + Redis + MinIO
  -> frozen SQLite is migration source only in Docker mode
```

## 已完成的非上线能力

- 身份：登录、退出、首次改密、资料、账号启停、角色权限、会话撤销、Redis 会话、CSRF、Argon2id 自动升级。
- 品牌创意：钩子、产品出场、完整脚本、外键关系、封面、分镜、成品、广告数据双向兼容；旧 UI 保存会同步规范化表，新 API 修改会回写旧 UI。
- 品牌内容：五个固定分组及固定内容类型、项目字段、状态、图片轨道、批量上传、排序、审核、最终稿、原图查看。
- 营销方案：方案、执行阶段、客户生命周期方案及九类节点。
- 广告数据：多对象投放、素材周期、服务端指标汇总、平台/币种隔离、排行和完整等长周期比较。
- 竞品洞察：六类洞察、素材、借鉴、复刻、验证、负责人、评价。
- 协作：首页真实统计、个人待办、动态、通知、评价、回复、点赞、标签、负责人、截止日期。
- 管理：账号、RBAC、结构化操作记录、标签、类型接口、规范化归档恢复与永久删除确认。
- 图片：真实解码、25 MB 限制、SHA-256 去重、原图不改写保存、WebP 预览/缩略图、元数据、历史路径修复、孤立对象检查。
- OpenAPI：`/api/docs` 和 `/api/openapi.json`。

## 数据兼容边界

- `state.entries` 暂时保留，供冻结的 V1 创意页面使用。
- 钩子、产品出场、脚本、分镜、成品和广告数据已有双向桥接。
- 品牌内容、营销、生命周期、竞品、待办直接使用规范化 `/api/v1`。
- Docker 运行时主数据是 PostgreSQL；SQLite 只读挂载作为迁移源，避免双写损坏。

## 暂缓事项

仅以下上线工作未执行：正式域名、HTTPS 证书、生产密钥轮换、云端数据库/对象存储、监控告警、CI/CD 和正式发布。
