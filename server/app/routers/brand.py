from fastapi import APIRouter

from app.routers.resource_helpers import bind_resource


router = APIRouter(prefix="/api/v1", tags=["brand"])
bind_resource(router, "/products", "products", "产品")
bind_resource(router, "/brand/milestones", "brand_milestones", "品牌历程")
