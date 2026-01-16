"""
系統參數設定 API 端點

提供系統參數的查詢與更新操作。
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.system_config import SystemParameter
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.system_config import (
    SystemParameterCreate,
    SystemParameterResponse,
    SystemParameterUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[SystemParameterResponse],
    summary="取得系統參數列表",
)
async def get_system_parameters(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    category: Optional[str] = Query(default=None, description="參數分類"),
    is_active: Optional[bool] = Query(default=None, description="是否啟用"),
):
    """
    取得系統參數列表

    可依分類和啟用狀態篩選。
    """
    statement = select(SystemParameter)

    if category:
        statement = statement.where(SystemParameter.param_category == category)
    if is_active is not None:
        statement = statement.where(SystemParameter.is_active == is_active)

    # 計算總數
    count_statement = select(SystemParameter)
    if category:
        count_statement = count_statement.where(
            SystemParameter.param_category == category
        )
    if is_active is not None:
        count_statement = count_statement.where(SystemParameter.is_active == is_active)
    count_result = await session.execute(count_statement)
    total = len(count_result.all())

    # 分頁
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(
        SystemParameter.param_category, SystemParameter.param_code
    )

    result = await session.execute(statement)
    parameters = result.scalars().all()

    return PaginatedResponse.create(
        items=parameters, total=total, page=page, page_size=page_size
    )


@router.post(
    "",
    response_model=SystemParameterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立系統參數",
)
async def create_system_parameter(
    param_data: SystemParameterCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    建立系統參數

    需要管理員權限。
    """
    # 檢查代碼是否已存在
    statement = select(SystemParameter).where(
        SystemParameter.param_code == param_data.param_code
    )
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="參數代碼已存在")

    parameter = SystemParameter(
        **param_data.model_dump(),
        created_by=current_user.id,
    )
    session.add(parameter)
    await session.commit()
    await session.refresh(parameter)

    return parameter


@router.get(
    "/categories",
    response_model=List[str],
    summary="取得所有參數分類",
)
async def get_parameter_categories(
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    取得所有參數分類清單
    """
    statement = select(SystemParameter.param_category).distinct()
    result = await session.execute(statement)
    categories = [row[0] for row in result.all()]

    return sorted(categories)


@router.get(
    "/category/{category}",
    response_model=List[SystemParameterResponse],
    summary="取得指定分類的參數",
)
async def get_parameters_by_category(
    category: str,
    session: SessionDep,
    current_user: CurrentUser,
    is_active: Optional[bool] = Query(default=True, description="是否啟用"),
):
    """
    取得指定分類的所有參數
    """
    statement = select(SystemParameter).where(
        SystemParameter.param_category == category
    )

    if is_active is not None:
        statement = statement.where(SystemParameter.is_active == is_active)

    statement = statement.order_by(SystemParameter.param_code)

    result = await session.execute(statement)
    parameters = result.scalars().all()

    return parameters


@router.get(
    "/{param_code}",
    response_model=SystemParameterResponse,
    summary="取得單一參數",
)
async def get_system_parameter(
    param_code: str,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    依參數代碼取得單一參數
    """
    statement = select(SystemParameter).where(
        SystemParameter.param_code == param_code
    )
    result = await session.execute(statement)
    parameter = result.scalar_one_or_none()

    if parameter is None:
        raise HTTPException(status_code=404, detail="參數不存在")

    return parameter


@router.put(
    "/{param_code}",
    response_model=SystemParameterResponse,
    summary="更新系統參數",
)
async def update_system_parameter(
    param_code: str,
    param_data: SystemParameterUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    更新系統參數

    只有可編輯的參數才能更新。
    """
    statement = select(SystemParameter).where(
        SystemParameter.param_code == param_code
    )
    result = await session.execute(statement)
    parameter = result.scalar_one_or_none()

    if parameter is None:
        raise HTTPException(status_code=404, detail="參數不存在")

    if not parameter.is_editable:
        raise HTTPException(status_code=400, detail="此參數不可編輯")

    update_data = param_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(parameter, field, value)

    parameter.updated_by = current_user.id
    session.add(parameter)
    await session.commit()
    await session.refresh(parameter)

    return parameter


@router.delete(
    "/{param_code}",
    response_model=SystemParameterResponse,
    summary="刪除系統參數",
)
async def delete_system_parameter(
    param_code: str,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    刪除系統參數

    只有可編輯的參數才能刪除。
    """
    statement = select(SystemParameter).where(
        SystemParameter.param_code == param_code
    )
    result = await session.execute(statement)
    parameter = result.scalar_one_or_none()

    if parameter is None:
        raise HTTPException(status_code=404, detail="參數不存在")

    if not parameter.is_editable:
        raise HTTPException(status_code=400, detail="此參數不可刪除")

    await session.delete(parameter)
    await session.commit()

    return parameter
