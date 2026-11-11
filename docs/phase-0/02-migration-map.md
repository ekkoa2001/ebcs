# 旧数据到新表的迁移映射

迁移必须可重复、先备份、失败回滚，且不覆盖 `data/sana_data.sqlite3` 原文件。下面的数量是 2026-11-11 审计时的当前库。

## 1. 数量对照的起点

| 来源 | 当前数量 | 目标 |
| --- | --- | --- |
| `state.entries` 中 `开头创意` | 5 | `creative_hooks` |
| `state.entries` 中 `产品出场` | 5 | `product_entries` |
| `state.entries` 中 `完整脚本` | 5 | `scripts` |
| 上述脚本内 `shots` | 随脚本数组统计 | `storyboard_shots` |
| 上述脚本内 `videos` | 0；存在 `videoCount` | `produced_videos` |
| `ad.campaigns` 或旧广告头字段 | 按脚本统计 | `ad_campaigns` |
| `ad.rows` | 按行统计 | `ad_period_records` |
| `archive` 中 `图片素材` | 3 | 内容项目、图片和 `archives` |
| `state.entries` 中 `类型定义` | 0 | 管理端类型表，不进创意表 |
| comments | 1 | `comments` |
| likes | 0 | `comment_likes` |
| events | 4 | `notifications` |
| revisions | 10 | `revisions` |
| log | 36 | `activity_logs` |
| media | 23 | `media_files` 加磁盘文件 |
| users / profiles | 1 / 1 | `users` / `user_profiles` |

## 2. 字段映射

### 账号

| 旧字段 | 新字段 |
| --- | --- |
| `users.username` | `users.username` |
| `users.salt`、`users.password_hash` | 迁移时用 Argon2id 重新哈希，旧 PBKDF2 只在首次登录校验后替换 |
| `users.role` | `roles.name`，值为 `admin`、`editor`、`viewer` |
| `users.active` | `users.active` |
| `profiles.name/avatar/team/tag/joined/must_change/read_cursor` | `user_profiles` 同名列 |

旧记录的 `createdBy` 继续保存用户名。即使用户后来停用，也不改历史作者。

### 创意开头

`kind = 开头创意` 写入 `creative_hooks`。

| 旧字段 | 新字段 |
| --- | --- |
| `id` | `id`，保留原值 |
| `code`、`title`、`content`、`notes` | 同名列 |
| `hook` | `hook_type` |
| `selectionStatus` | `status`，空值记为 `待筛选` |
| `isExample` | `is_example` |
| `created`、`createdTime` | `created_at` |
| `createdBy` | `created_by` |

产品、人群、场景、标签、负责人和截止日期在旧记录中不存在，留空，不发明内容。

### 产品出场

`kind = 产品出场` 写入 `product_entries`。

| 旧字段 | 新字段 |
| --- | --- |
| `parent` | `hook_id`，必须能找到对应钩子 |
| `transition` | `entry_type` |
| `content` | `visual_description` |
| 其余公共字段 | 与钩子相同 |

找不到 `parent` 时该条失败并回滚，不改成孤立记录。

### 完整脚本

`kind = 完整脚本` 写入 `scripts`。

| 旧字段 | 新字段 |
| --- | --- |
| `parent` | `hook_id` |
| `transitionId` | `product_entry_id` |
| `sourceHookContent`、`sourceTransitionContent` | 保留为迁移快照，不覆盖钩子和出场正文 |
| `coverImage` | `cover_media_id`，去掉 `/media/` 前缀 |
| `producedDate`、`usedDate`、`videoCount` | 同名信息列 |
| `selectionStatus` | 不直接当成制作状态。旧数据没有制作状态，迁移为 `草稿`，并在报告中标明 |

### 分镜与成品

`shots` 按数组顺序写入 `storyboard_shots.sort_order`。`name`、`description`、`scale`、`seconds`、`image` 分别对应名称、画面描述、景别、时长和 `media_id`。人物动作、台词和产品信息旧数据没有，留空。

已有 `videos[]` 时，`id`、`title`、`date`、`source` 写入 `produced_videos`。没有数组但 `videoCount > 0` 时，按现有界面规则生成同等数量的历史占位，标题使用“历史视频”，来源留空，并在报告中单列。

### 广告

每个完整脚本：

1. 有 `ad.campaigns` 时，每个批次写入 `ad_campaigns`，`object_type = script`，`object_id = 脚本 id`。
2. 没有批次数组时，用 `ad.launchDate`、`endDate`、`platform`、`currency` 生成一条 `id = legacy` 的批次。
3. `status = ended` 记为投放结束；有开始日且未结束记为正在投放；只有素材日、没有开始日记为准备投放。
4. `ad.rows[]` 写入 `ad_period_records`。`periodStart` 优先，否则用 `date`。`periodEnd` 同样处理。
5. 指标按原数值迁移。空值保持空值，不写成 0。
6. `clicks` 对应新字段 Link Clicks。旧数据没有 Add to Cart、Initiate Checkout、Revenue、Frequency、Video Plays，这些列留空。

### 图片、评价和审计

| 旧数据 | 新数据 |
| --- | --- |
| `archive` 中的图片素材 | 一个已归档的 `brand_content_projects`，其图片写入 `content_assets`，同时写 `archives` |
| `media.id/mime/data` | `media_files`，原图写入 `data/media/originals/{sha256}`，并生成预览和缩略图 |
| `comments` | `comments`，`entity_type` 由所属记录的 `kind` 决定，`entity_id = entry_id` |
| `likes` | `comment_likes` |
| `events` | `notifications`，保留 `batch_id`、`recipient`、`entry_id` |
| `event_reads` 和 `profiles.read_cursor` | 已读状态 |
| `revisions.before_json/after_json` | `revisions`，不拆历史差异 |
| `log` | `activity_logs`。只有时间、操作者和动作；模块、对象、结果、IP、User-Agent 留空 |
| `类型定义` | 类型管理表，不写入钩子或出场 |

`/media/{id}` 继续用原来的 id，前端地址不用改。

## 3. 执行约束

1. 迁移前复制数据库。
2. 写入新库或新表，不在失败时覆盖原库。
3. 报告列出每个目标表的迁移前后数量，以及跳过、失败和历史占位数量。
4. 任一外键无法解析、图片无法解码或数量不平，整次回滚。
5. 完成验证前，旧 `/api/state` 和 `/api/entries/patch` 继续可用。
