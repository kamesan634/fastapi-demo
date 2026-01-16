"""
編號規則管理 API 端點

提供編號規則的 CRUD 操作與編號預覽功能。
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.settings import DocumentType, NumberingRule
from app.kamesan.schemas.common import MessageResponse, PaginatedResponse
from app.kamesan.schemas.numbering import (
    NumberingRuleCreate,
    NumberingRuleResponse,
    NumberingRuleUpdate,
    NumberPreviewResponse,
)
from app.kamesan.services.numbering import NumberingService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[NumberingRuleResponse],
    summary="取得編號規則列表",
)
async def get_numbering_rules(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    document_type: Optional[DocumentType] = Query(default=None, description="單據類型"),
    is_active: Optional[bool] = Query(default=None, description="是否啟用"),
):
    """取得編號規則列表"""
    statement = select(NumberingRule)

    if document_type is not None:
        statement = statement.where(NumberingRule.document_type == document_type)

    if is_active is not None:
        statement = statement.where(NumberingRule.is_active == is_active)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(NumberingRule.id)

    result = await session.execute(statement)
    rules = result.scalars().all()

    return PaginatedResponse.create(
        items=rules, total=total, page=page, page_size=page_size
    )


@router.post(
    "",
    response_model=NumberingRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立編號規則",
)
async def create_numbering_rule(
    rule_data: NumberingRuleCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立編號規則"""
    # 檢查單據類型是否已存在
    statement = select(NumberingRule).where(
        NumberingRule.document_type == rule_data.document_type
    )
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail=f"單據類型 {rule_data.document_type} 的編號規則已存在"
        )

    rule = NumberingRule(
        **rule_data.model_dump(),
        created_by=current_user.id,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)

    return rule


@router.get(
    "/{rule_id}",
    response_model=NumberingRuleResponse,
    summary="取得單一編號規則",
)
async def get_numbering_rule(
    rule_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得單一編號規則"""
    statement = select(NumberingRule).where(NumberingRule.id == rule_id)
    result = await session.execute(statement)
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(status_code=404, detail="編號規則不存在")

    return rule


@router.put(
    "/{rule_id}",
    response_model=NumberingRuleResponse,
    summary="更新編號規則",
)
async def update_numbering_rule(
    rule_id: int,
    rule_data: NumberingRuleUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新編號規則"""
    statement = select(NumberingRule).where(NumberingRule.id == rule_id)
    result = await session.execute(statement)
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(status_code=404, detail="編號規則不存在")

    update_data = rule_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    rule.updated_by = current_user.id
    session.add(rule)
    await session.commit()
    await session.refresh(rule)

    return rule


@router.delete(
    "/{rule_id}",
    response_model=MessageResponse,
    summary="刪除編號規則",
)
async def delete_numbering_rule(
    rule_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除編號規則"""
    statement = select(NumberingRule).where(NumberingRule.id == rule_id)
    result = await session.execute(statement)
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(status_code=404, detail="編號規則不存在")

    await session.delete(rule)
    await session.commit()

    return MessageResponse(message="編號規則已刪除")


@router.get(
    "/preview/{document_type}",
    response_model=NumberPreviewResponse,
    summary="預覽編號",
)
async def preview_number(
    document_type: DocumentType,
    session: SessionDep,
    current_user: CurrentUser,
):
    """預覽指定單據類型的下一個編號"""
    service = NumberingService(session)
    sample_number, next_number = await service.preview_next_number(document_type)

    return NumberPreviewResponse(
        document_type=document_type,
        sample_number=sample_number,
        next_number=next_number,
    )


@router.post(
    "/init-defaults",
    response_model=MessageResponse,
    summary="初始化預設編號規則",
)
async def init_default_rules(
    session: SessionDep,
    current_user: CurrentUser,
):
    """初始化系統預設的編號規則"""
    default_rules = [
        {
            "document_type": DocumentType.SALES_ORDER,
            "prefix": "SO",
            "date_format": "YYYYMMDD",
            "sequence_digits": 4,
            "reset_period": "DAILY",
        },
        {
            "document_type": DocumentType.PURCHASE_ORDER,
            "prefix": "PO",
            "date_format": "YYYYMM",
            "sequence_digits": 5,
            "reset_period": "MONTHLY",
        },
        {
            "document_type": DocumentType.GOODS_RECEIPT,
            "prefix": "GR",
            "date_format": "YYYYMMDD",
            "sequence_digits": 4,
            "reset_period": "DAILY",
        },
        {
            "document_type": DocumentType.SALES_RETURN,
            "prefix": "RT",
            "date_format": "YYYYMMDD",
            "sequence_digits": 4,
            "reset_period": "DAILY",
        },
        {
            "document_type": DocumentType.PURCHASE_RETURN,
            "prefix": "PR",
            "date_format": "YYYYMMDD",
            "sequence_digits": 4,
            "reset_period": "DAILY",
        },
        {
            "document_type": DocumentType.STOCK_COUNT,
            "prefix": "SC",
            "date_format": "YYYYMMDD",
            "sequence_digits": 3,
            "reset_period": "DAILY",
        },
        {
            "document_type": DocumentType.STOCK_TRANSFER,
            "prefix": "TR",
            "date_format": "YYYYMMDD",
            "sequence_digits": 4,
            "reset_period": "DAILY",
        },
    ]

    created_count = 0
    for rule_data in default_rules:
        # 檢查是否已存在
        statement = select(NumberingRule).where(
            NumberingRule.document_type == rule_data["document_type"]
        )
        result = await session.execute(statement)
        if result.scalar_one_or_none():
            continue

        from app.kamesan.models.settings import DateFormat, ResetPeriod

        rule = NumberingRule(
            document_type=rule_data["document_type"],
            prefix=rule_data["prefix"],
            date_format=DateFormat(rule_data["date_format"]),
            sequence_digits=rule_data["sequence_digits"],
            reset_period=ResetPeriod(rule_data["reset_period"]),
            created_by=current_user.id,
        )
        session.add(rule)
        created_count += 1

    await session.commit()

    return MessageResponse(message=f"已建立 {created_count} 筆預設編號規則")
