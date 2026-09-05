from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.transformations import router as transformations_router
from app.api.v1.feature_selection import router as feature_selection_router
from app.api.v1.experiments import router as experiments_router
from app.api.v1.models import router as models_router
from app.api.v1.deployments import router as deployments_router
from app.api.v1.predict import router as predict_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(datasets_router)
api_v1_router.include_router(transformations_router)
api_v1_router.include_router(feature_selection_router)
api_v1_router.include_router(experiments_router)
api_v1_router.include_router(models_router)
api_v1_router.include_router(deployments_router)
api_v1_router.include_router(predict_router)
