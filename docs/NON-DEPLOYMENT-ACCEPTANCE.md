# 非上线功能验收记录

日期：2026-11-13

## 自动验证

- 后端/API：`docker compose exec -T api pytest -q`
- 浏览器烟雾测试：`cd tests/visual && npx playwright test business-smoke.spec.ts`
- JavaScript 语法：`node --check web/modules/upgrade/business.js` 与 `node --check web/modules/analytics/workshop.js`
- 服务健康：`docker compose ps` 中 API、Nginx、PostgreSQL、Redis、MinIO 均为 Up。

## 手动验收入口

- 工作台：`http://127.0.0.1/`
- API 文档：`http://127.0.0.1/api/docs`
- 默认本地管理员：`ekko`（密码以当前本地环境为准）。

## 页面检查顺序

1. 首页：真实数量、待办、最新内容和动态。
2. 品牌创意：钩子、产品出场、完整脚本、分镜、成品和广告数据。
3. 品牌内容：五组固定分类、详情字段、横向图片轨道、审核和最终稿。
4. 营销方案：方案详情、执行阶段、九类生命周期节点。
5. 广告数据：素材周期、罗盘、排行和周期比较。
6. 竞品洞察：六类洞察及截图素材。
7. 管理端：成员、权限、操作记录、归档中心和标签。

## 保留原则

视觉继续以 V1 为基线；新增能力复用原卡片、筛选、弹窗、按钮、横向轨道、状态色和 Hover，不引入另一套布局或设计系统。
