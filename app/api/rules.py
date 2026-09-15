from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import Category, VendorRule
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
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    stmt = select(VendorRule).where(VendorRule.user_id == user_id)
    result = await db.execute(stmt)
    rules = result.scalars().all()

    # Load categories for name mapping
    cat_stmt = select(Category).where(Category.user_id == user_id)
    cat_res = await db.execute(cat_stmt)
    cat_map = {c.id: c.name for c in cat_res.scalars().all()}

    output = []
    for r in rules:
        output.append(
            VendorRuleResponse(
                id=r.id,
                user_id=r.user_id,
                vendor_regex=r.vendor_regex,
                default_category_id=r.default_category_id,
                category_name=cat_map.get(r.default_category_id),
            )
        )
    return output


@router.post("", response_model=VendorRuleResponse, summary="Create or update vendor rule")
async def create_rule(
    payload: CreateRuleRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    # Verify category exists and belongs to user
    cat_stmt = select(Category).where(Category.user_id == user_id, Category.id == payload.default_category_id)
    cat_res = await db.execute(cat_stmt)
    category = cat_res.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found for this user",
        )

    rule = await create_or_update_vendor_rule(
        db=db,
        user_id=user_id,
        vendor_pattern=payload.vendor_regex,
        category_id=payload.default_category_id,
        re_evaluate_pending=payload.re_evaluate_pending,
    )
    return VendorRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        vendor_regex=rule.vendor_regex,
        default_category_id=rule.default_category_id,
        category_name=category.name,
    )


@router.delete("/{rule_id}", summary="Delete vendor rule")
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    stmt = delete(VendorRule).where(VendorRule.user_id == user_id, VendorRule.id == rule_id)
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return {"status": "deleted", "id": rule_id}


@router.post("/test", summary="Test if pattern matches a vendor string")
async def test_rule_match(payload: TestRuleRequest):
    matched = matches_pattern(payload.pattern, payload.vendor_text)
    return {
        "pattern": payload.pattern,
        "vendor_text": payload.vendor_text,
        "matched": matched,
    }
