from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import Category
from app.services.categorization import ensure_default_categories

router = APIRouter(prefix="/categories", tags=["Categories"])


class CategoryResponse(BaseModel):
    id: int
    user_id: str
    name: str
    parent_id: int | None = None

    model_config = {"from_attributes": True}


class CreateCategoryRequest(BaseModel):
    name: str
    parent_id: int | None = None


@router.get("", response_model=list[CategoryResponse], summary="List user categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    categories = await ensure_default_categories(db, user_id)
    return categories


@router.post("", response_model=CategoryResponse, summary="Create a new category")
async def create_category(
    payload: CreateCategoryRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    if payload.parent_id is not None:
        parent_stmt = select(Category).where(Category.id == payload.parent_id, Category.user_id == user_id)
        parent_res = await db.execute(parent_stmt)
        if not parent_res.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent category not found")

    cat = Category(
        user_id=user_id,
        name=payload.name.strip(),
        parent_id=payload.parent_id,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/{category_id}", summary="Delete a category")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    stmt = delete(Category).where(Category.user_id == user_id, Category.id == category_id)
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return {"status": "deleted", "id": category_id}
