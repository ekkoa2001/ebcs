# 性能优化记录

> 原则：保留现有业务接口、中文文案、权限与路由；每一项独立验证并可通过 Git 回滚。

## 2026-11-15 · 第一项：消除周期性主线程阻塞

### 发现

- `web/assets/js/boot.js` 每 5 秒使用同步 `XMLHttpRequest` 请求 `/api/state`。
- 同步网络请求会冻结浏览器主线程，表现为输入、滚动、弹窗与切换页面短暂停顿。

### 已完成

- 将轮询替换为 `fetch()` 异步请求。
- 新增轻量 `/api/state/version`：日常轮询只获取版本号；仅在版本变化时才请求原有完整 `/api/state` 数据。
- 保留原有 `/api/state`、版本比较和 `entries` 更新逻辑。
- 页面不可见、弹窗打开或已有请求在执行时跳过轮询。
- 会话过期时仍跳转登录页；网络暂时不可用时保留现有页面可操作。

### 验证

- `node --check web/assets/js/boot.js` 通过。
- `git diff --check` 通过。

## 2026-11-15 · 第二项：静态资源缓存

### 已完成

- `server/app/legacy.py` 对静态 JS、CSS、字体和图片响应添加一年 `Cache-Control`。
- API、HTML、登录和私有媒体不使用此缓存策略。
- 已重建并启动 Docker 的 `api` 服务。

### 验证

- `python -m py_compile server/app/legacy.py` 通过。
- Docker `api` 容器已成功重建并运行。

## 2026-11-15 · 第三项：首次进入工作台

### 已完成

- 新增 `/api/bootstrap`，一次返回当前会话（含用户资料、角色与 CSRF）及工作台状态。
- `web/assets/js/app.js` 从连续两次同步请求改为一次 bootstrap 请求，未改变后续模块对 `serverUser`、权限与资料数据的依赖。
- 登录页移除只为入场效果加载的 GSAP，使用 220ms 原生淡入、180ms 离场过渡，并支持 `prefers-reduced-motion`。

### 验证

- `server/tests/test_foundation.py` 已覆盖 bootstrap 的会话、资料与状态结构。

## 架构结论与后续边界

- 当前正在运行的是遗留工作台（`web/` + FastAPI 兼容层），不是 `frontend/` 中尚未接管页面的 Vue 宿主。因此不对未投入运行的 Vue 入口进行“伪懒加载”改动，避免产生无实际收益的复杂度。
- Nginx 现有配置已启用 gzip、静态资源长缓存；HTTPS 配置中已有 HTTP/2。Brotli 需切换到含 Brotli 模块的 Nginx 镜像后再启用，不能在当前标准镜像中伪装为已启用。
- 月 / 周 / 日事件日历尚未实现：现有参考仅定义日期范围选择器，不能替代事件日历的布局规范。
