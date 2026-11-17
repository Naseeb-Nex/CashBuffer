from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.native_repository import NativeRepository
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
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)
    categories = await ensure_default_categories(repo, user.id)
    return [
        CategoryResponse(
            id=c.id,
            user_id=c.user_id,
            name=c.name,
            parent_id=c.parent_id,
        )
        for c in categories
    ]

@router.post("", response_model=CategoryResponse, summary="Create a new category")
async def create_category(
    payload: CreateCategoryRequest,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)

    if payload.parent_id is not None:
        parent = await repo.get_category_by_id(user.id, payload.parent_id)
        if not parent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent category not found")

    cat = await repo.create_category(
        user_id=user.id,
        name=payload.name.strip(),
        parent_id=payload.parent_id,
    )
    return CategoryResponse(
        id=cat.id,
        user_id=cat.user_id,
        name=cat.name,
        parent_id=cat.parent_id,
    )

@router.delete("/{category_id}", summary="Delete a category")
async def delete_category(
    category_id: int,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)

    success = await repo.delete_category(user.id, category_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return {"status": "success", "deleted_id": category_id}
