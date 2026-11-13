from fastapi import APIRouter
from app.routers.resource_helpers import bind_resource

router = APIRouter(prefix="/api/v1", tags=["marketing"])
bind_resource(router, "/marketing/plans", "marketing_plans", "营销方案")
bind_resource(router, "/marketing/lifecycle-plans", "lifecycle_plans", "生命周期方案")
bind_resource(router, "/marketing/stages", "marketing_plan_stages", "方案阶段")
bind_resource(router, "/marketing/lifecycle", "lifecycle_nodes", "客户生命周期")
