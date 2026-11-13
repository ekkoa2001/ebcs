from fastapi import APIRouter
from app.routers.resource_helpers import bind_resource

router = APIRouter(prefix="/api/v1", tags=["competitors"])
bind_resource(router, "/competitors", "competitor_insights", "竞品洞察")
