# V1 审计与功能清单

审计对象是基线 `b15e69b` 上正在运行的 V1，地址 `http://127.0.0.1:8875/`。没有改页面、没有拆文件、没有新增业务模块。

## 1. 文件

| 路径 | 作用 |
| --- | --- |
| `web/index.html` | 主界面。内含样式、页面结构和全部列表、详情、分镜、广告表单逻辑 |
| `web/login.html` | 登录页与 GSAP |
| `web/first-password.html` | 首次改密页 |
| `web/workshop.js` | 团队协作、广告周期、分镜关联、视频登记、管理端弹窗 |
| `web/workshop.css` | 上述界面的补充样式 |
| `web/team-client.js` | 图片素材、动态入口、个人资料、权限隐藏 |
| `web/ui-fixes.css` | 登录后注入的视觉修正 |
| `web/gsap.min.js` | 登录页动画 |
| `server/server.py` | 会话、用户、整包 `state`、操作日志 |
| `server/team_server.py` | 团队表、评价、动态、归档、媒体、冲突校验 |
| `server/initialize.py` | 空库时创建管理员并导入 `data/demo.json` |
| `server/backup.py` | SQLite 在线备份到 `data/backups` |
| `data/sana_data.sqlite3` | 当前库 |
| `data/demo.json` | 首次初始化示例 |

启动入口仍是根目录的 `启动团队版.cmd` 和 `start.ps1`。

## 2. 当前库

`state` 只有一行，`version = 13`。`entries` 是一个 JSON 数组，现有 15 条，全部带 `isExample = true`。

| 表 | 行数 | 用途 |
| --- | --- | --- |
| state | 1 | 版本号和全部业务记录 |
| users | 1 | `ekko`，角色 `admin`，启用 |
| profiles | 1 | 显示名、团队、岗位、头像、是否强制改密、动态已读游标 |
| media | 23 | 图片 SHA-256、MIME、BLOB |
| comments | 1 | 评价 |
| likes | 0 | 评价点赞 |
| events | 4 | 团队动态 |
| event_reads | 0 | 单条动态已读 |
| revisions | 10 | 修改前后 JSON |
| archive | 3 | 已归档图片素材 |
| log | 36 | 操作记录 |

活跃记录种类：开头创意 5、产品出场 5、完整脚本 5。图片素材不在 `state.entries` 中，3 条只存在于 `archive`。当前完整脚本没有 `videos` 数组，但有 `videoCount`。

## 3. 记录字段

开头创意：`id`、`kind`、`code`、`title`、`content`、`hook`、`notes`、`images`、`selectionStatus`、`isExample`、`created`、`createdTime`、`createdBy`。

产品出场在此基础上增加 `transition`、`parent`。`parent` 指向开头创意。

完整脚本再增加 `transitionId`、`sourceHookContent`、`sourceTransitionContent`、`producedDate`、`usedDate`、`videoCount`、`coverImage`、`shots`、`ad`。封面和分镜图使用 `/media/{id}`。

分镜元素：`name`、`description`、`scale`、`seconds`、`image`。

广告对象 `ad`：`materialDate`、`launchDate`、`endDate`、`platform`、`currency`、`rows`，也可带 `campaigns`。周期行至少有 `id`、`date` 或 `periodStart`/`periodEnd`、`platform`、`currency`、`batch`、`campaignId`、`materialId`，以及 `spend`、`impressions`、`clicks`、`lpv`、`purchases`、`cpm`、`ctr`、`cpa`、`roas`、`view3`、`view50`。

归档图片素材另有 `category`、`generationPlatform`、`brand`、`product`、`generatedAt`、`authorName`。

类型定义使用 `kind = 类型定义`，保存在同一个 `entries` 数组里。当前库没有这类活跃记录。

## 4. 已核对的现有功能

登录页、首页、创意开头、产品出场、完整脚本、横向分镜、广告数据和两个浮层都已用 Playwright 打开并截图。

- 登录、退出、首次改密页面。密码使用 PBKDF2-SHA256，60 万次迭代。改密要求至少 12 位。
- 角色为 `admin`、`editor`、`viewer`。界面文案对应管理员、操作者、只读。
- 个人资料、头像、团队、岗位。在线人数按两分钟内会话去重。
- 团队动态、未读数、单条已读和全部已读。
- 创意开头、产品出场、完整脚本的列表、搜索、类型筛选、筛选状态、预览示例筛选和分页。
- 完整脚本封面、详情弹窗和卡片内横向分镜。
- 视频登记入口。源文件位置只记录文字，不上传文件。
- 广告投放批次、周期记录、罗盘、跨边界排除和环比。
- 评价、删除自己的评价、管理员删除任意评价、点赞和取消点赞。
- 修订记录、整包版本冲突、作者不可更改。
- 归档与管理员恢复。操作者不能直接删除记录。
- 操作记录、类型管理、JSON 导出和导入。
- 图片素材库入口。当前活跃列表为空，历史上传在归档中。

## 5. 基线截图

| 文件 | 画面 |
| --- | --- |
| `screenshots/01-login.png` | 登录页 |
| `screenshots/02-home.png` | 首页 |
| `screenshots/03-hooks.png` | 创意开头列表 |
| `screenshots/04-entries.png` | 产品出场列表 |
| `screenshots/05-scripts.png` | 完整脚本列表 |
| `screenshots/06-script-detail.png` | 完整脚本详情 |
| `screenshots/07-storyboard.png` | 横向分镜 |
| `screenshots/08-ads.png` | 广告数据 |
| `screenshots/09-activity.png` | 动态 |
| `screenshots/10-admin.png` | 管理端 |

视口为 1440×900。登录页在 GSAP 动画后截取。动态是顶部浮层，管理端是当前弹窗，都不是独立路由。

像素对比在 `tests/visual`。服务开在 `http://127.0.0.1:8875` 时，于该目录执行 `npx playwright test`。对比对象是上面 10 张基线，允许的像素差异比例是 0.002。超过这个比例，测试失败。

## 6. 对后续升级有影响的现状

- 所有业务记录仍在 `state.entries` 一个字段里。
- 关联是字符串 `id`，不是外键。
- 图片原件在 `media.data` BLOB 中，地址已经是 `/media/{id}`。
- 示例数据和正式数据靠 `isExample` 区分，当前活跃记录都是示例。
- 广告既有单日 `date`，也有 `periodStart`/`periodEnd`。迁移必须两种都接收。
- 操作日志只有时间、操作者和动作，没有模块、对象、结果、IP、User-Agent。
- 自动化像素对比已建立，脚本在 `tests/visual`，基线仍是本目录的 10 张截图。
