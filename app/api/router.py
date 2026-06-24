from fastapi import APIRouter

from app.api.routes.administrative_divisions import router as administrative_divisions_router
from app.api.routes.code_dicts import router as code_dicts_router
from app.api.routes.farms import router as farms_router
from app.api.routes.health import router as health_router
from app.api.routes.planting_plans import router as planting_plans_router
from app.api.routes.rice_varieties import router as rice_varieties_router
from app.api.routes.review_requests import router as review_requests_router
from app.api.routes.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(administrative_divisions_router, tags=["administrative-divisions"])
api_router.include_router(code_dicts_router, tags=["code-dicts"])
api_router.include_router(farms_router, tags=["farms"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(planting_plans_router, tags=["planting-plans"])
api_router.include_router(rice_varieties_router, tags=["rice-varieties"])
api_router.include_router(review_requests_router, tags=["review-requests"])
api_router.include_router(tasks_router, tags=["tasks"])
