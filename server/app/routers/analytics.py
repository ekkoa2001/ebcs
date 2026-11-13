from fastapi import APIRouter, HTTPException, Query, Request
from datetime import date, timedelta
from sqlalchemy import text
from app.database import SessionLocal
from app.dependencies import require_permission, require_session
from app.routers.resource_helpers import bind_resource

router = APIRouter(prefix="/api/v1", tags=["analytics"])
bind_resource(router, "/analytics/campaigns", "ad_campaigns", "广告投放")
bind_resource(router, "/analytics/periods", "ad_period_records", "投放周期")


@router.get("/analytics/compass")
def compass(request: Request, start: str = Query(""), end: str = Query("")):
    current = require_session(request); require_permission(current, "content.read")
    where, params = [], {}
    if start: where.append("r.period_start >= :start"); params["start"] = start
    if end: where.append("r.period_end <= :end"); params["end"] = end
    clause = " WHERE " + " AND ".join(where) if where else ""
    sql = """SELECT COUNT(DISTINCT r.campaign_id) campaigns, COUNT(DISTINCT c.object_id) materials,
        COALESCE(SUM(r.spend),0) spend, COALESCE(SUM(r.impressions),0) impressions,
        COALESCE(SUM(r.link_clicks),0) link_clicks, COALESCE(SUM(r.lpv),0) lpv,
        COALESCE(SUM(r.purchases),0) purchases, COALESCE(SUM(r.revenue),0) revenue
        FROM ad_period_records r JOIN ad_campaigns c ON c.id=r.campaign_id""" + clause
    with SessionLocal() as db: result = dict(db.execute(text(sql), params).first()._mapping)
    result["cvr"] = round(float(result["purchases"]) / float(result["lpv"]) * 100, 2) if result["lpv"] else None
    result["roas"] = round(float(result["revenue"]) / float(result["spend"]), 2) if result["spend"] else None
    result["ctr"] = round(float(result["link_clicks"]) / float(result["impressions"]) * 100, 2) if result["impressions"] else None
    return result


@router.get("/analytics/ranking")
def ranking(request:Request, start:str="", end:str=""):
    current=require_session(request); require_permission(current,"content.read")
    filters=[]; params={}
    if start: filters.append("r.period_start>=:start"); params["start"]=start
    if end: filters.append("r.period_end<=:end"); params["end"]=end
    clause=" WHERE "+" AND ".join(filters) if filters else ""
    sql="""SELECT c.object_type,c.object_id,c.material_code,c.platform,c.currency,
      SUM(r.spend) spend,SUM(r.impressions) impressions,SUM(r.link_clicks) link_clicks,SUM(r.lpv) lpv,
      SUM(r.purchases) purchases,SUM(r.revenue) revenue
      FROM ad_campaigns c JOIN ad_period_records r ON r.campaign_id=c.id"""+clause+" GROUP BY c.object_type,c.object_id,c.material_code,c.platform,c.currency ORDER BY purchases DESC,revenue DESC"
    with SessionLocal() as db: rows=[dict(x._mapping) for x in db.execute(text(sql),params).all()]
    for x in rows:
        x["cvr"]=round(float(x["purchases"])/float(x["lpv"])*100,2) if x["lpv"] else None
        x["cpa"]=round(float(x["spend"])/float(x["purchases"]),2) if x["purchases"] else None
        x["roas"]=round(float(x["revenue"])/float(x["spend"]),2) if x["spend"] else None
    return rows


def period_summary(db,start,end,platform="",currency=""):
    filters=["r.period_start>=:start","r.period_end<=:end"]; params={"start":start,"end":end}
    if platform: filters.append("r.platform=:platform"); params["platform"]=platform
    if currency: filters.append("r.currency=:currency"); params["currency"]=currency
    rows=[dict(x._mapping) for x in db.execute(text("SELECT r.* FROM ad_period_records r WHERE "+" AND ".join(filters)),params).all()]
    groups={}
    for row in rows:
        key=(row.get("platform") or "未标注",row.get("currency") or "未标注")
        target=groups.setdefault(key,{"platform":key[0],"currency":key[1],"records":0,"spend":0.0,"impressions":0.0,"linkClicks":0.0,"lpv":0.0,"purchases":0.0,"revenue":0.0})
        target["records"]+=1
        for source,dest in (("spend","spend"),("impressions","impressions"),("link_clicks","linkClicks"),("lpv","lpv"),("purchases","purchases"),("revenue","revenue")):
            target[dest]+=float(row.get(source) or 0)
    for target in groups.values():
        target["cpm"]=round(target["spend"]/target["impressions"]*1000,2) if target["impressions"] else None
        target["ctr"]=round(target["linkClicks"]/target["impressions"]*100,2) if target["impressions"] else None
        target["cvr"]=round(target["purchases"]/target["lpv"]*100,2) if target["lpv"] else None
        target["cpa"]=round(target["spend"]/target["purchases"],2) if target["purchases"] else None
        target["roas"]=round(target["revenue"]/target["spend"],2) if target["spend"] else None
    return list(groups.values())


@router.get("/analytics/comparison")
def comparison(request:Request,start:str,end:str,platform:str="",currency:str=""):
    current=require_session(request); require_permission(current,"content.read")
    try: first=date.fromisoformat(start); last=date.fromisoformat(end)
    except ValueError: raise HTTPException(400,"日期格式无效")
    if last<first: raise HTTPException(400,"结束日期不能早于开始日期")
    days=(last-first).days+1; previous_end=first-timedelta(days=1); previous_start=previous_end-timedelta(days=days-1)
    with SessionLocal() as db:
        current_rows=period_summary(db,start,end,platform,currency)
        previous_rows=period_summary(db,previous_start.isoformat(),previous_end.isoformat(),platform,currency)
    return {"current":{"start":start,"end":end,"groups":current_rows},"previous":{"start":previous_start.isoformat(),"end":previous_end.isoformat(),"groups":previous_rows},"rule":"只统计完整落在范围内的素材周期，不按日拆分；不同币种不合计。"}
