from app.domain.ingress_schemas import (
    IngressConfigResponse,
    IngressStatusResponse,
    IngressTriggerResponse,
    UpdateIngressConfigRequest,
)


class IngressControlService:
    """Business logic for web-controlled ingress configuration, scheduling, and sync triggers."""

    def __init__(self, repo):
        self.repo = repo

    async def get_config(
        self, idp_user_id: str, provider: str = "gmail"
    ) -> IngressConfigResponse:
        user_id, household_id = await self.repo.get_or_create_user_and_household(idp_user_id)
        config = await self.repo.get_or_create_config(
            household_id=household_id, user_id=user_id, provider=provider
        )
        return IngressConfigResponse(**config)

    async def update_config(
        self, idp_user_id: str, request: UpdateIngressConfigRequest
    ) -> IngressConfigResponse:
        user_id, household_id = await self.repo.get_or_create_user_and_household(idp_user_id)
        config = await self.repo.update_config(
            household_id=household_id,
            user_id=user_id,
            provider=request.provider,
            interval_minutes=request.interval_minutes,
            is_enabled=request.is_enabled,
        )
        return IngressConfigResponse(**config)

    async def trigger_sync(
        self, idp_user_id: str, provider: str = "gmail"
    ) -> IngressTriggerResponse:
        user_id, household_id = await self.repo.get_or_create_user_and_household(idp_user_id)
        config = await self.repo.trigger_sync(
            household_id=household_id, user_id=user_id, provider=provider
        )
        cfg_resp = IngressConfigResponse(**config)
        return IngressTriggerResponse(
            message="Sync triggered successfully",
            next_run_at=cfg_resp.next_run_at,
            status=cfg_resp.status,
            config=cfg_resp,
        )

    async def get_status(
        self, idp_user_id: str, provider: str = "gmail"
    ) -> IngressStatusResponse:
        user_id, household_id = await self.repo.get_or_create_user_and_household(idp_user_id)
        status_data = await self.repo.get_status(
            household_id=household_id, user_id=user_id, provider=provider
        )
        return IngressStatusResponse(**status_data)
