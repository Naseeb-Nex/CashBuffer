from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.categorization import create_or_update_vendor_rule, matches_pattern

router = APIRouter(prefix="/rules", tags=["Rules"])

class VendorRuleResponse(BaseModel):
    id: int
    user_id: str
    vendor_regex: str
    default_category_id: int
    category_name: str | None = None

    model_config = {"from_attributes": True}

class CreateRuleRequest(BaseModel):
    vendor_regex: str
    default_category_id: int
    re_evaluate_pending: bool = True

class TestRuleRequest(BaseModel):
    pattern: str
    vendor_text: str

@router.get("", response_model=list[VendorRuleResponse], summary="List all vendor rules")
async def list_rules(
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)

    rules = await repo.get_vendor_rules(user.id)
    categories = await repo.get_categories(user.id)
    cat_map = {c.id: c.name for c in categories}

    return [
        VendorRuleResponse(
            id=r.id,
            user_id=r.user_id,
            vendor_regex=r.vendor_regex,
            default_category_id=r.default_category_id,
            category_name=cat_map.get(r.default_category_id),
        )
        for r in rules
    ]

@router.post("", response_model=VendorRuleResponse, summary="Create or update vendor rule")
async def create_rule(
    payload: CreateRuleRequest,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)

    cat = await repo.get_category_by_id(user.id, payload.default_category_id)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Referenced category does not exist",
        )

    rule = await create_or_update_vendor_rule(
        repo=repo,
        user_id=user.id,
        vendor_pattern=payload.vendor_regex,
        category_id=payload.default_category_id,
        re_evaluate_pending=payload.re_evaluate_pending,
    )

    return VendorRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        vendor_regex=rule.vendor_regex,
        default_category_id=rule.default_category_id,
        category_name=cat.name,
    )

@router.delete("/{rule_id}", summary="Delete a vendor rule")
async def delete_rule(
    rule_id: int,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)

    success = await repo.delete_vendor_rule(user.id, rule_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return {"status": "success", "deleted_id": rule_id}

@router.post("/test", summary="Test vendor rule matching logic")
async def test_rule(payload: TestRuleRequest):
    matched = matches_pattern(payload.pattern, payload.vendor_text)
    return {"pattern": payload.pattern, "vendor_text": payload.vendor_text, "matched": matched}
