# 阶段 1 验收

阶段 1 只移动了前端代码。DOM、id、class、颜色、布局和现有操作保持原样。

## 模块

页面仍由 `web/index.html`、`web/login.html`、`web/first-password.html` 进入。样式按原层叠顺序拆到 `web/assets/css/`：`tokens.css`、`layout.css`、`components.css`、`dialogs.css`、`pages.css`、`ui-fixes.css`、`team.css`。脚本按原执行顺序拆到 `web/assets/js/` 和 `web/modules/`。GSAP 移到 `web/vendor/gsap.min.js`。

主脚本按原来的先后拆成 `app.js`、`home.js`、`creative/board.js`、`router.js`、`creative/editor.js`、`analytics/metrics.js`、`api.js`、`admin/accounts.js`、`auth.js`、`confirm.js`、`creative/shots.js`、`boot.js`。`toast.js` 是原来的反馈脚本。团队脚本拆成 `admin/team.js`、`content/assets.js`、`home/launch.js`、`admin/permissions.js`。广告周期、管理端和素材选择仍在同一个闭包里，文件是 `analytics/workshop.js`。

## 表、迁移、接口、权限

没有新表，没有迁移，没有新接口。登录、角色和原有接口保持不变。业务样式和脚本仍需登录后访问，`/vendor/gsap.min.js` 仍可在登录前加载。

## 页面

`index.html` 保留原来的结构。开源声明脚本仍留在页面里，供 `oss-licenses` 读取原文。营销方案和竞品洞察在当前 V1 中没有可移动的代码，目录留到阶段 6 和阶段 8。

## 测试与视觉回归

在 `tests/visual` 执行 `npx playwright test`。结果：1 个测试通过。10 张基线全部参与比较，像素差异比例阈值 0.002。视口 1440×900。

## 构建

这一阶段没有打包。页面由现有 Python 服务按文件路径直接提供。

## 手动步骤

1. 启动 `启动团队版.cmd`。
2. 打开 `http://127.0.0.1:8875/`。
3. 登录后依次查看首页、创意开头、产品出场、完整脚本、分镜、脚本详情、广告数据、动态和管理端。

## 已知问题

首页和广告页上的「本周」日期写在视觉基线里。跨周之后，相关截图会超过 0.002，需要按当时界面重截这几张基线。

## 下一阶段

阶段 2：FastAPI、SQLAlchemy、Alembic、Session、CSRF、RBAC、审计和旧接口兼容。当前页面继续可用。阶段 2 尚未开始。
