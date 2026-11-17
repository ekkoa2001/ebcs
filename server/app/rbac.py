from sqlalchemy import select, text

from app.database import SessionLocal
from app.models.foundation import Permission, Role, RolePermission

PERMISSIONS = {
    "content.read": "查看内容",
    "content.create": "新建内容",
    "content.update_own": "修改自己的内容",
    "content.update_any": "修改他人内容",
    "content.archive": "归档",
    "content.restore": "恢复归档",
    "ad.update": "修改广告数据",
    "comment.create": "发表评价",
    "comment.delete_own": "删除自己的评价",
    "comment.delete_any": "删除他人评价",
    "comment.like": "点赞",
    "profile.update_self": "修改自己的资料",
    "team.update": "修改成员团队和岗位",
    "user.manage": "管理账号",
    "audit.read": "查看审计",
    "admin.access": "进入管理端",
}

GRANTS = {
    "admin": list(PERMISSIONS),
    "editor": [
        "content.read", "content.create", "content.update_own", "comment.create", "comment.delete_own",
        "comment.like", "profile.update_self",
    ],
    "viewer": ["content.read", "profile.update_self"],
}

LABELS = {"admin": "管理员", "editor": "操作者", "viewer": "只读"}


def seed_business_examples(db):
    """Install the visible examples once, without touching team-authored records."""
    now = "2026-11-16T09:00:00+00:00"
    content_rows = [
        ("sample_brand_01", "【预览示例】独立站首页 Banner", "品牌推广", "品牌推广图", "Sana", "ClearLove7", "首页首屏的品牌主张与核心卖点，突出轻量、清晰与可信赖的品牌体验。", "ekko"),
        ("sample_brand_02", "【预览示例】新品首发主视觉", "品牌推广", "新品发布图", "Sana", "ClearLove7", "用于新品上线首周的社媒主视觉，强调新品亮点与购买动机。", "Mia"),
        ("sample_brand_03", "【预览示例】用户真实场景", "品牌推广", "品牌 UGC 图", "Sana", "ClearLove7", "用真实用户使用场景建立信任，适配社媒种草与落地页口碑区。", "Sana"),
        ("sample_brand_04", "【预览示例】产品卖点长图", "产品内容", "产品卖点图", "Sana", "ClearLove7", "将核心功能拆成易读卖点，适合电商详情页和广告落地页。", "ekko"),
        ("sample_brand_05", "【预览示例】使用场景展示", "产品内容", "产品场景图", "Sana", "ClearLove7", "以通勤、办公和居家场景展现产品如何融入日常生活。", "Mia"),
        ("sample_brand_06", "【预览示例】产品详情重点图", "产品内容", "产品详情图", "Sana", "ClearLove7", "围绕规格、材质和体验细节编排，帮助用户快速理解产品。", "Sana"),
        ("sample_brand_07", "【预览示例】节日活动主图", "营销内容", "节日／大促图", "Sana", "ClearLove7", "为季节性活动预留统一视觉与优惠信息的展示位置。", "ekko"),
        ("sample_brand_08", "【预览示例】EDM 欢迎邮件配图", "营销内容", "EDM 营销图", "Sana", "ClearLove7", "新用户欢迎邮件的头图，承接注册后的第一印象。", "Mia"),
        ("sample_brand_09", "【预览示例】SEO 文章封面", "渠道内容", "SEO 文章配图", "Sana", "ClearLove7", "用于搜索内容的文章封面，兼顾信息识别与品牌一致性。", "Sana"),
        ("sample_after_01", "【预览示例】首次使用指南", "售后内容", "使用教程方案", "Sana", "ClearLove7", "以三步完成首次使用，降低新用户上手门槛。", "ekko"),
        ("sample_after_02", "【预览示例】日常保养清单", "售后内容", "产品保养方案", "Sana", "ClearLove7", "按周期整理清洁与保养动作，延长产品的最佳使用状态。", "Mia"),
        ("sample_after_03", "【预览示例】常见问题解答", "售后内容", "常见问题方案", "Sana", "ClearLove7", "集中回答高频问题，让客户自助找到清晰答案。", "Sana"),
        ("sample_after_04", "【预览示例】故障排查步骤", "售后内容", "故障排查方案", "Sana", "ClearLove7", "通过症状、判断和解决步骤快速定位常见故障。", "ekko"),
        ("sample_after_05", "【预览示例】配件安装说明", "售后内容", "配件说明方案", "Sana", "ClearLove7", "明确配件用途、安装顺序和注意事项，减少售后咨询。", "Mia"),
        ("sample_after_06", "【预览示例】售后服务流程", "售后内容", "售后流程方案", "Sana", "ClearLove7", "展示提交、处理、反馈各阶段，让客户知道下一步该做什么。", "Sana"),
        ("sample_after_07", "【预览示例】客户关怀回访", "售后内容", "客户关怀方案", "Sana", "ClearLove7", "在购买后的关键节点提供关怀与复购建议。", "ekko"),
        ("sample_after_08", "【预览示例】快速开箱图解", "售后内容", "使用教程方案", "Sana", "ClearLove7", "开箱后即可完成的图解说明，适合随包裹发送。", "Mia"),
        ("sample_after_09", "【预览示例】问题反馈入口", "售后内容", "常见问题方案", "Sana", "ClearLove7", "汇总反馈渠道与所需信息，缩短问题处理时间。", "Sana"),
    ]
    for identifier, name, group, kind, brand, product, description, owner in content_rows:
        db.execute(text("""
            INSERT INTO brand_content_projects
            (id,name,content_group,content_type,brand,product,owner,status,description,is_example,created_by,created_at,updated_at)
            VALUES (:id,:name,:group,:kind,:brand,:product,:owner,'已通过',:description,1,'ekko',:now,:now)
            ON CONFLICT (id) DO NOTHING
        """), {"id": identifier, "name": name, "group": group, "kind": kind, "brand": brand, "product": product, "owner": owner, "description": description, "now": now})
    plans = [
        ("sample_plan_01", "【预览示例】新品首发整合方案", "新品上线首月的渠道协同与转化节奏。", "待执行"),
        ("sample_plan_02", "【预览示例】年末礼赠活动", "以礼赠场景提升节日购买转化。", "执行中"),
        ("sample_plan_03", "【预览示例】老客复购计划", "围绕售后节点设计复购沟通。", "草稿"),
        ("sample_plan_04", "【预览示例】内容种草月", "通过真实场景内容积累品牌信任。", "已结束"),
        ("sample_plan_05", "【预览示例】SEO 增长专题", "建设覆盖产品决策问题的搜索内容。", "待执行"),
        ("sample_plan_06", "【预览示例】夏季场景推广", "聚焦户外与通勤的季节性使用需求。", "已复盘"),
        ("sample_plan_07", "【预览示例】新用户欢迎旅程", "连接注册、首购和首次使用的完整体验。", "执行中"),
    ]
    for identifier, name, goal, status in plans:
        db.execute(text("""
            INSERT INTO marketing_plans (id,name,goal,product,owner,status,created_by,created_at,updated_at)
            VALUES (:id,:name,:goal,'ClearLove7','ekko',:status,'ekko',:now,:now)
            ON CONFLICT (id) DO NOTHING
        """), {"id": identifier, "name": name, "goal": goal, "status": status, "now": now})
    insights = [
        ("sample_insight_01", "Northstar", "【预览示例】产品页信息结构", "竞品产品内容", "产品卖点分区清晰，适合复刻成移动端阅读节奏。"),
        ("sample_insight_02", "Northstar", "【预览示例】独立站首屏观察", "竞品独立站", "首屏聚焦单一主张，行动按钮层级明确。"),
        ("sample_insight_03", "Luma", "【预览示例】节日促销策略", "竞品营销策略", "通过限时权益和场景化礼赠强化购买理由。"),
        ("sample_insight_04", "Luma", "【预览示例】短视频广告素材", "竞品广告素材", "前三秒先呈现使用结果，再补充功能证据。"),
        ("sample_insight_05", "Morrow", "【预览示例】欢迎邮件节奏", "竞品 EDM", "邮件分阶段建立信任，避免一次堆叠过多卖点。"),
        ("sample_insight_06", "Morrow", "【预览示例】搜索内容主题", "竞品 SEO Blog", "围绕用户问题布局内容，承接产品页转化。"),
        ("sample_insight_07", "Northstar", "【预览示例】评价展示方式", "竞品产品内容", "在详情页靠近购买按钮的位置展示高质量评价。"),
    ]
    for identifier, competitor, title, kind, takeaway in insights:
        db.execute(text("""
            INSERT INTO competitor_insights (id,competitor,title,insight_type,product,takeaway,owner,created_by,created_at,updated_at)
            VALUES (:id,:competitor,:title,:kind,'ClearLove7',:takeaway,'ekko','ekko',:now,:now)
            ON CONFLICT (id) DO NOTHING
        """), {"id": identifier, "competitor": competitor, "title": title, "kind": kind, "takeaway": takeaway, "now": now})
    db.execute(text("""
        INSERT INTO products (id,name,brand,owner,status,description,created_by,created_at,updated_at)
        VALUES ('sample_product_clearlove7','ClearLove7','Sana','ekko','在售','团队当前使用的示例产品主档。','ekko',:now,:now)
        ON CONFLICT (id) DO NOTHING
    """), {"now": now})
    milestones = [
        ('sample_milestone_01', '2026-10-08', '品牌定位', '已完成', '明确品牌核心主张', '完成受众、价值主张与视觉关键词的一轮共创。', '形成轻量、清晰、可信赖的品牌表达框架。'),
        ('sample_milestone_02', '2026-10-22', '产品开发', '已完成', '完成首版产品卖点梳理', '将功能语言转译为用户可感知的使用结果。', '产品详情页与广告卖点形成统一口径。'),
        ('sample_milestone_03', '2026-11-05', '内容建设', '进行中', '搭建独立站首屏内容资产', '围绕首页 Banner、UGC 与产品场景持续补齐素材。', '待补充更多真实用户场景素材。'),
        ('sample_milestone_04', '2026-11-16', '营销投放', '草稿', '规划首轮新品推广节奏', '拟定内容发布、邮件触达与广告测试的协作顺序。', ''),
    ]
    for identifier, date, category, status, title, description, outcome in milestones:
        db.execute(text("""
            INSERT INTO brand_milestones
            (id,milestone_date,category,status,title,owner,product,related_item,description,outcome,created_by,created_at,updated_at)
            VALUES (:id,:date,:category,:status,:title,'ekko','ClearLove7','',:description,:outcome,'ekko',:now,:now)
            ON CONFLICT (id) DO NOTHING
        """), {"id": identifier, "date": date, "category": category, "status": status, "title": title, "description": description, "outcome": outcome, "now": now})
    db.execute(text("""
        INSERT INTO after_sales_emails
        (id,project_id,title,preview_text,body,sort_order,created_by,created_at,updated_at)
        VALUES ('sample_after_email_01','sample_after_01','欢迎开始使用 ClearLove7','三步完成首次使用。','你好，欢迎开始使用 ClearLove7。请按图文指南完成首次设置；如遇问题，随时联系我们。',1,'ekko',:now,:now)
        ON CONFLICT (id) DO NOTHING
    """), {"now": now})
    for identifier, actor, content in (
        ("sample_brand_01", "Sana", "首屏信息聚焦，品牌主张与按钮层级都很清晰。"),
        ("sample_after_01", "Mia", "三步说明易懂，建议在第二步补充一个常见误操作提醒。"),
    ):
        exists = db.execute(text("SELECT 1 FROM comments WHERE entity_type='brand_content' AND entity_id=:id LIMIT 1"), {"id": identifier}).first()
        if not exists:
            db.execute(text("INSERT INTO comments (entry_id,actor,time,content,entity_type,entity_id) VALUES (:entry_id,:actor,:time,:content,'brand_content',:entity_id)"), {"entry_id": identifier, "entity_id": identifier, "actor": actor, "time": "2026-11-16T10:00:00+00:00", "content": content})


def seed():
    with SessionLocal() as db:
        for name, label in LABELS.items():
            if db.get(Role, name) is None:
                db.add(Role(name=name, label=label))
        for code, description in PERMISSIONS.items():
            if db.get(Permission, code) is None:
                db.add(Permission(code=code, description=description))
        db.commit()
        existing = {(row.role_name, row.permission_code) for row in db.scalars(select(RolePermission))}
        for role, codes in GRANTS.items():
            for code in codes:
                if (role, code) not in existing:
                    db.add(RolePermission(role_name=role, permission_code=code))
        db.commit()
        # Visible business samples are authored data, not system configuration.
        # Re-inserting them on every startup made removed examples reappear and
        # prevented a clean production workspace from staying clean.
        db.commit()


def allows(role: str, code: str) -> bool:
    with SessionLocal() as db:
        found = db.scalar(select(RolePermission).where(RolePermission.role_name == role, RolePermission.permission_code == code))
    return found is not None
