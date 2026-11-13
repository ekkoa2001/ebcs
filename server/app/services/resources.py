import secrets
import json
from datetime import datetime, timezone

from sqlalchemy import text

from app.database import SessionLocal


class ResourceError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


CONFIG = {
    "team_tasks": {"id": "str", "prefix": "task", "title": "title", "owner": "created_by", "soft": True, "required": ("title",)},
    "scripts": {"id": "str", "prefix": "script", "title": "title", "owner": "created_by", "soft": True,
        "required": ("hook_id", "product_entry_id", "title")},
    "storyboard_shots": {"id": "str", "prefix": "shot", "title": "name", "required": ("script_id",)},
    "produced_videos": {"id": "str", "prefix": "video", "title": "name", "required": ("script_id", "name")},
    "brand_content_projects": {"id": "str", "prefix": "content", "title": "name", "owner": "created_by", "soft": True, "required": ("name", "content_group", "content_type")},
    "content_assets": {"id": "str", "prefix": "asset", "title": "role", "owner": "uploader", "required": ("project_id", "media_id")},
    "marketing_plans": {"id": "str", "prefix": "plan", "title": "name", "owner": "created_by", "soft": True, "required": ("name",)},
    "lifecycle_plans": {"id": "str", "prefix": "lifecycle", "title": "name", "owner": "created_by", "soft": True, "required": ("name",)},
    "marketing_plan_stages": {"id": "str", "prefix": "stage", "title": "name", "required": ("plan_id", "name")},
    "lifecycle_nodes": {"id": "str", "prefix": "life", "title": "node_type", "required": ("plan_id", "node_type")},
    "ad_campaigns": {"id": "str", "prefix": "campaign", "title": "material_code", "required": ("object_type", "object_id")},
    "ad_period_records": {"id": "str", "prefix": "period", "title": "material_code", "required": ("campaign_id", "period_start", "period_end")},
    "competitor_insights": {"id": "str", "prefix": "insight", "title": "title", "owner": "created_by", "soft": True, "required": ("competitor", "title", "insight_type")},
}


def stamp(): return datetime.now(timezone.utc).isoformat()


def emit_event(db, actor, kind, identifier, title, at=None):
    at = at or stamp(); batch = secrets.token_hex(8)
    db.execute(text("INSERT INTO notifications(actor,time,kind,entry_id,title,batch_id,recipient) VALUES(:actor,:time,:kind,:id,:title,:batch,'')"), {"actor":actor,"time":at,"kind":kind,"id":identifier,"title":title,"batch":batch})
    db.execute(text("INSERT INTO events(actor,time,kind,entry_id,title,batch_id,recipient) VALUES(:actor,:time,:kind,:id,:title,:batch,'')"), {"actor":actor,"time":at,"kind":kind,"id":identifier,"title":title,"batch":batch})


def config(name):
    if name not in CONFIG: raise ResourceError(404, "资源不存在")
    return CONFIG[name]


def columns(db, table):
    dialect = db.bind.dialect.name
    if dialect == "sqlite":
        return [x[1] for x in db.execute(text(f"PRAGMA table_info({table})")).all()]
    return list(db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:table ORDER BY ordinal_position"), {"table": table}).scalars())


def serialize(row): return dict(row._mapping)


def list_rows(table, page=1, page_size=20, search="", include_archived=False, filters=None):
    cfg = config(table); where, params = [], {}
    with SessionLocal() as db:
        cols = columns(db, table)
        if cfg.get("soft") and not include_archived: where.append("deleted_at IS NULL")
        if search:
            searchable = [x for x in (cfg.get("title"), "code", "description", "notes", "product") if x in cols]
            if searchable:
                where.append("(" + " OR ".join(f"LOWER(COALESCE({x},'')) LIKE :search" for x in searchable) + ")"); params["search"] = f"%{search.lower()}%"
        for key, value in (filters or {}).items():
            if value not in (None, "") and key in cols: where.append(f"{key} = :f_{key}"); params[f"f_{key}"] = value
        clause = " WHERE " + " AND ".join(where) if where else ""
        total = db.execute(text(f"SELECT COUNT(*) FROM {table}{clause}"), params).scalar_one()
        order = "updated_at DESC" if "updated_at" in cols else "id DESC"
        params.update({"limit": page_size, "offset": (page - 1) * page_size})
        rows = db.execute(text(f"SELECT * FROM {table}{clause} ORDER BY {order} LIMIT :limit OFFSET :offset"), params).all()
        return {"page": page, "pageSize": page_size, "total": total, "items": [serialize(x) for x in rows]}


def get_row(table, identifier, include_archived=False):
    cfg = config(table)
    with SessionLocal() as db:
        suffix = " AND deleted_at IS NULL" if cfg.get("soft") and not include_archived else ""
        row = db.execute(text(f"SELECT * FROM {table} WHERE id=:id{suffix}"), {"id": identifier}).first()
        if not row: raise ResourceError(404, "记录不存在")
        return serialize(row)


def clean_payload(cols, body):
    blocked = {"id", "created_at", "updated_at", "deleted_at", "version", "created_by"}
    return {k: v for k, v in body.items() if k in cols and k not in blocked}


def normalize(table, values):
    allowed_status={"scripts":{"草稿","待制作","制作中","已产出","已投放","已复盘"},"brand_content_projects":{"草稿","制作中","待审核","待修改","已通过","已发布"},"marketing_plans":{"草稿","待执行","执行中","已结束","已复盘"},"ad_campaigns":{"准备投放","正在投放","投放结束"},"team_tasks":{"待处理","进行中","已完成","已取消"}}
    if table in allowed_status and values.get("status") and values["status"] not in allowed_status[table]: raise ResourceError(400,"状态无效")
    if table == "brand_content_projects":
        groups={"品牌推广":{"品牌推广图","品牌UGC图","新品发布图"},"产品内容":{"产品详情图","产品卖点图","产品场景图"},"营销内容":{"EDM营销图","折扣营销图","节日／大促活动图"},"渠道内容":{"独立站Banner","SEO文章配图"},"售后内容":{"使用教程图","产品保养图","常见问题图","故障排查图","配件说明图","售后流程图","客户关怀图"}}
        group,kind=values.get("content_group"),values.get("content_type")
        if group and group not in groups: raise ResourceError(400,"品牌内容分组无效")
        if group and kind and kind not in groups[group]: raise ResourceError(400,"内容类型与分组不匹配")
    if table == "ad_campaigns":
        start, end = values.get("start_date"), values.get("end_date")
        if start and end:
            try: values["duration_days"] = (datetime.fromisoformat(end)-datetime.fromisoformat(start)).days+1
            except ValueError: raise ResourceError(400,"投放日期格式无效")
            if values["duration_days"] < 1: raise ResourceError(400,"结束日期不能早于开始日期")
    if table == "ad_period_records":
        start, end = values.get("period_start"), values.get("period_end")
        if start and end:
            try:
                if datetime.fromisoformat(end) < datetime.fromisoformat(start): raise ResourceError(400,"周期结束日期不能早于开始日期")
            except ValueError: raise ResourceError(400,"周期日期格式无效")
        numeric=("spend","impressions","link_clicks","lpv","add_to_cart","initiate_checkout","purchases","revenue","frequency","video_plays","view3","view50")
        for key in numeric:
            if key in values and values[key] is not None:
                try: values[key]=float(values[key])
                except (TypeError,ValueError): raise ResourceError(400,f"{key} 必须为数字")
                if values[key] < 0: raise ResourceError(400,f"{key} 不能为负数")
        for key in ("view3","view50"):
            if values.get(key) is not None and values[key] > 100: raise ResourceError(400,f"{key} 百分比不能超过 100")
    return values


def create_row(table, actor, body):
    cfg = config(table); now = stamp()
    with SessionLocal() as db:
        cols = columns(db, table); values = normalize(table, clean_payload(cols, body))
        for field in cfg.get("required", ()):
            if not values.get(field): raise ResourceError(400, f"缺少字段：{field}")
        values["id"] = f"{cfg['prefix']}_{secrets.token_hex(16)}"
        if "created_by" in cols: values["created_by"] = actor
        if "owner" in cols and not values.get("owner"): values["owner"] = actor
        if "created_at" in cols: values["created_at"] = now
        if "updated_at" in cols: values["updated_at"] = now
        if "version" in cols: values["version"] = 1
        names = list(values); db.execute(text(f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join(':'+x for x in names)})"), values)
        db.execute(text("INSERT INTO revisions(actor,time,entry_id,before_json,after_json) VALUES(:actor,:time,:id,:before,:after)"), {"actor":actor,"time":now,"id":values["id"],"before":"null","after":json.dumps(values,ensure_ascii=False,default=str)})
        emit_event(db,actor,table,values["id"],str(values.get(cfg.get("title"),"")),now)
        db.commit()
    return get_row(table, values["id"], True)


def update_row(table, actor, can_update_any, identifier, body):
    cfg = config(table)
    with SessionLocal() as db:
        cols = columns(db, table)
        row = db.execute(text(f"SELECT * FROM {table} WHERE id=:id"), {"id": identifier}).first()
        if not row: raise ResourceError(404, "记录不存在")
        current = serialize(row); owner_col = cfg.get("owner")
        if owner_col and not can_update_any and str(current.get(owner_col, "")).casefold() != actor.casefold(): raise ResourceError(403, "不能修改其他成员的内容")
        if "version" in cols and body.get("version") is not None and body["version"] != current.get("version"): raise ResourceError(409, "内容已被其他成员修改，请刷新")
        values = normalize(table, clean_payload(cols, body))
        if "updated_at" in cols: values["updated_at"] = stamp()
        if "version" in cols: values["version"] = int(current.get("version") or 0) + 1
        if not values: return current
        values["_id"] = identifier
        db.execute(text(f"UPDATE {table} SET " + ",".join(f"{k}=:{k}" for k in values if k != "_id") + " WHERE id=:_id"), values)
        after={**current,**{k:v for k,v in values.items() if k!="_id"}}
        db.execute(text("INSERT INTO revisions(actor,time,entry_id,before_json,after_json) VALUES(:actor,:time,:id,:before,:after)"), {"actor":actor,"time":stamp(),"id":identifier,"before":json.dumps(current,ensure_ascii=False,default=str),"after":json.dumps(after,ensure_ascii=False,default=str)})
        db.commit()
    return get_row(table, identifier, True)


def archive_row(table, identifier, restore=False, actor="", reason=""):
    cfg = config(table)
    with SessionLocal() as db:
        if cfg.get("soft"):
            value = None if restore else stamp()
            before=db.execute(text(f"SELECT * FROM {table} WHERE id=:id"),{"id":identifier}).first()
            result = db.execute(text(f"UPDATE {table} SET deleted_at=:value, updated_at=:now, version=version+1 WHERE id=:id"), {"value": value, "now": stamp(), "id": identifier})
            if before and not restore:
                import json
                db.execute(text("INSERT INTO archives(entry_id,entity_type,content_json,actor,time,reason) VALUES(:entry,:type,:content,:actor,:time,:reason)"),{"entry":identifier,"type":table,"content":json.dumps(dict(before._mapping),ensure_ascii=False),"actor":actor,"time":value,"reason":reason})
        elif restore: raise ResourceError(400, "此资源不支持恢复")
        else: result = db.execute(text(f"DELETE FROM {table} WHERE id=:id"), {"id": identifier})
        if not result.rowcount: raise ResourceError(404, "记录不存在")
        db.commit()
    return {"ok": True}
