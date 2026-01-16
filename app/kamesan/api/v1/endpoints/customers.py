"""
客戶管理 API 端點

提供客戶的 CRUD 操作與點數管理功能。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.customer import Customer, PointsLog, PointsLogType
from app.kamesan.schemas.common import MessageResponse, PaginatedResponse
from app.kamesan.schemas.customer import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    PointsAdjustRequest,
    PointsLogResponse,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CustomerResponse], summary="取得客戶列表")
async def get_customers(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    """取得客戶列表"""
    statement = select(Customer).options(selectinload(Customer.level))
    statement = statement.where(Customer.is_deleted == False)

    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            (Customer.code.ilike(search_pattern))
            | (Customer.name.ilike(search_pattern))
            | (Customer.phone.ilike(search_pattern))
        )

    if is_active is not None:
        statement = statement.where(Customer.is_active == is_active)

    count_result = await session.execute(
        select(Customer).where(Customer.is_deleted == False)
    )
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Customer.id.desc())

    result = await session.execute(statement)
    customers = result.scalars().all()

    return PaginatedResponse.create(items=customers, total=total, page=page, page_size=page_size)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED, summary="建立客戶")
async def create_customer(
    customer_data: CustomerCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立客戶"""
    statement = select(Customer).where(Customer.code == customer_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="會員編號已存在")

    customer = Customer(**customer_data.model_dump(), created_by=current_user.id)
    session.add(customer)
    await session.commit()
    await session.refresh(customer)

    return customer


@router.get("/{customer_id}", response_model=CustomerResponse, summary="取得單一客戶")
async def get_customer(customer_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一客戶"""
    statement = (
        select(Customer)
        .options(selectinload(Customer.level))
        .where(Customer.id == customer_id, Customer.is_deleted == False)
    )
    result = await session.execute(statement)
    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(status_code=404, detail="客戶不存在")

    return customer


@router.put("/{customer_id}", response_model=CustomerResponse, summary="更新客戶")
async def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新客戶"""
    statement = select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)
    result = await session.execute(statement)
    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(status_code=404, detail="客戶不存在")

    update_data = customer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    customer.updated_by = current_user.id
    session.add(customer)
    await session.commit()
    await session.refresh(customer)

    return customer


@router.delete("/{customer_id}", response_model=CustomerResponse, summary="刪除客戶")
async def delete_customer(customer_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除客戶"""
    statement = select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)
    result = await session.execute(statement)
    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(status_code=404, detail="客戶不存在")

    customer.soft_delete()
    customer.updated_by = current_user.id
    session.add(customer)
    await session.commit()

    return customer


# ==========================================
# 點數管理 API
# ==========================================
@router.post(
    "/{customer_id}/points/adjust",
    response_model=MessageResponse,
    summary="調整客戶點數",
)
async def adjust_customer_points(
    customer_id: int,
    adjust_data: PointsAdjustRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    調整客戶點數

    支援類型：
    - BONUS: 活動贈點
    - ADJUST: 手動調整
    - EXPIRE: 過期扣除

    參數：
        customer_id: 客戶 ID
        adjust_data: 點數調整資料
        session: 資料庫 Session
        current_user: 當前登入使用者

    回傳值：
        MessageResponse: 操作結果

    例外：
        404: 客戶不存在
        400: 點數類型無效或點數不足
    """
    # 查詢客戶
    statement = select(Customer).where(
        Customer.id == customer_id, Customer.is_deleted == False
    )
    result = await session.execute(statement)
    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(status_code=404, detail="客戶不存在")

    # 驗證異動類型
    valid_types = [
        PointsLogType.BONUS.value,
        PointsLogType.ADJUST.value,
        PointsLogType.EXPIRE.value,
    ]
    if adjust_data.type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"無效的異動類型，允許的類型: {', '.join(valid_types)}",
        )

    # 檢查點數是否足夠（如果是扣除）
    if adjust_data.points < 0 and customer.points + adjust_data.points < 0:
        raise HTTPException(status_code=400, detail="點數不足")

    # 更新客戶點數
    customer.points += adjust_data.points
    new_balance = customer.points

    # 建立點數異動記錄
    points_log = PointsLog(
        customer_id=customer_id,
        type=PointsLogType(adjust_data.type),
        points=adjust_data.points,
        balance=new_balance,
        description=adjust_data.description,
        expire_date=adjust_data.expire_date,
        created_by=current_user.id,
    )

    session.add(customer)
    session.add(points_log)
    await session.commit()

    action = "增加" if adjust_data.points > 0 else "扣除"
    return MessageResponse(
        message=f"點數{action}成功，目前餘額: {new_balance} 點"
    )


@router.get(
    "/{customer_id}/points/logs",
    response_model=PaginatedResponse[PointsLogResponse],
    summary="取得客戶點數異動記錄",
)
async def get_customer_points_logs(
    customer_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    type: Optional[str] = Query(default=None, description="篩選異動類型"),
):
    """
    取得客戶點數異動記錄

    參數：
        customer_id: 客戶 ID
        session: 資料庫 Session
        current_user: 當前登入使用者
        page: 頁碼
        page_size: 每頁筆數
        type: 篩選異動類型

    回傳值：
        PaginatedResponse: 分頁點數異動記錄

    例外：
        404: 客戶不存在
    """
    # 確認客戶存在
    customer_check = select(Customer).where(
        Customer.id == customer_id, Customer.is_deleted == False
    )
    customer_result = await session.execute(customer_check)
    if customer_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="客戶不存在")

    # 查詢點數異動記錄
    statement = select(PointsLog).where(PointsLog.customer_id == customer_id)

    if type:
        statement = statement.where(PointsLog.type == type)

    # 計算總數
    count_result = await session.execute(statement)
    total = len(count_result.all())

    # 分頁查詢
    offset = (page - 1) * page_size
    statement = (
        statement.offset(offset).limit(page_size).order_by(PointsLog.id.desc())
    )

    result = await session.execute(statement)
    logs = result.scalars().all()

    return PaginatedResponse.create(items=logs, total=total, page=page, page_size=page_size)
