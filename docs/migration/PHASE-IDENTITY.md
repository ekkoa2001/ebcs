# 身份、权限、会话与审计迁移

完成日期：2026-11-12

## 已迁移

- `/api/v1/auth/login`
- `/api/v1/auth/logout`
- `/api/v1/auth/password`
- `/api/v1/auth/session`
- `/api/v1/users`
- `/api/v1/users/{username}`
- `/api/v1/users/me/profile`
- `/api/v1/admin/activity-logs`

## 老 UI 兼容地址

以下地址保留不变，但已经由新 Service 和 Router 响应：

- `/api/login`
- `/api/logout`
- `/api/password`
- `/api/session`
- `/api/users`
- `/api/users/create`
- `/api/users/update`
- `/api/team`
- `/api/team/update`
- `/api/profile`
- `/api/log`

## 安全行为

- 登录使用 IP 与账号两级失败限制。
- 登录成功创建 HttpOnly、SameSite=Strict Cookie。
- 生产 HTTPS 模式启用 Secure Cookie。
- 写操作执行同源与 CSRF 校验。
- 权限由后端 RBAC 校验，不依赖前端隐藏按钮。
- 旧 PBKDF2 密码在成功登录时自动升级为 Argon2。
- 新用户及重置后的密码使用 Argon2。
- 新用户首次登录必须修改初始密码。
- 停用账号、角色变更和密码重置立即撤销该用户全部会话。
- 禁止停用或降权当前管理员。
- 系统至少保留一个启用的管理员。
- 登录、退出、资料、团队、账号和密码操作写入结构化审计日志。

## UI 影响

无布局与视觉修改。老页面继续调用原路径，兼容路由转入新服务。

## 自动测试

- 老登录和 CSRF 兼容
- 新登录与会话接口
- RBAC 拒绝只读用户
- 用户创建与冲突处理
- 停用用户后会话撤销
- 新审计日志兼容老 UI
- 匿名与登录页面渲染
- PostgreSQL 兼容层和迁移依赖

当前结果：`13 passed`

## 暂时保留的旧依赖

- 页面、静态资源和非身份业务仍通过 `app.legacy`。
- 内容状态、评论、动态和归档仍主要由 `team_server.py` 处理。
- 完成对应模块迁移后再删除旧分支，不提前破坏老 UI。
