from fastapi import APIRouter, Depends, Query

from app.api.auth import get_current_user
from app.domain.ingress_schemas import (
    IngressConfigResponse,
    IngressStatusResponse,
    IngressTriggerResponse,
    UpdateIngressConfigRequest,
)
from app.infrastructure.persistence.db_pool import get_db_pool
from app.infrastructure.persistence.ingress_repository import (
    InMemoryIngressRepository,
    PsycopgIngressRepository,
)
from app.services.ingress_control_service import IngressControlService

router = APIRouter(prefix="/ingress", tags=["Ingress"])

_default_in_memory_repo = InMemoryIngressRepository()

async def get_ingress_repository():
    pool = await get_db_pool()
    if pool is not None:
        return PsycopgIngressRepository(pool)
    return _default_in_memory_repo

async def get_ingress_service(
    repo=Depends(get_ingress_repository),
) -> IngressControlService:
    return IngressControlService(repo=repo)

@router.get(
    "/config",
    response_model=IngressConfigResponse,
    summary="Get current ingress configuration",
)
async def get_ingress_config(
    provider: str = Query("gmail", description="Ingress provider"),
    user_id: str = Depends(get_current_user),
    service: IngressControlService = Depends(get_ingress_service),
):
    return await service.get_config(idp_user_id=user_id, provider=provider)

@router.patch(
    "/config",
    response_model=IngressConfigResponse,
    summary="Update ingress configuration",
)
async def update_ingress_config(
    payload: UpdateIngressConfigRequest,
    user_id: str = Depends(get_current_user),
    service: IngressControlService = Depends(get_ingress_service),
):
    return await service.update_config(idp_user_id=user_id, request=payload)

@router.post(
    "/trigger",
    response_model=IngressTriggerResponse,
    summary="Trigger immediate ingress sync",
)
async def trigger_ingress_sync(
    provider: str = Query("gmail", description="Ingress provider"),
    user_id: str = Depends(get_current_user),
    service: IngressControlService = Depends(get_ingress_service),
):
    return await service.trigger_sync(idp_user_id=user_id, provider=provider)

@router.get(
    "/status",
    response_model=IngressStatusResponse,
    summary="Get ingress sync checkpoint and status",
)
async def get_ingress_status(
    provider: str = Query("gmail", description="Ingress provider"),
    user_id: str = Depends(get_current_user),
    service: IngressControlService = Depends(get_ingress_service),
):
    return await service.get_status(idp_user_id=user_id, provider=provider)
