from sqlalchemy import select

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


def allows(role: str, code: str) -> bool:
    with SessionLocal() as db:
        found = db.scalar(select(RolePermission).where(RolePermission.role_name == role, RolePermission.permission_code == code))
    return found is not None
