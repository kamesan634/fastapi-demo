"""
商品組合/套餐管理 API 端點

提供商品組合的 CRUD 操作與價格計算功能。
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.combo import ComboType, ProductCombo, ProductComboItem
from app.kamesan.models.product import Product
from app.kamesan.schemas.combo import (
    ComboCalculateRequest,
    ComboCalculateResponse,
    ComboCreate,
    ComboItemCreate,
    ComboItemResponse,
    ComboItemUpdate,
    ComboResponse,
    ComboSummaryResponse,
    ComboUpdate,
)
from app.kamesan.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter()


async def _build_combo_response(
    session, combo: ProductCombo
) -> ComboResponse:
    """建構組合回應"""
    items_response = []

    for item in combo.items:
        # 取得商品資訊
        stmt = select(Product).where(Product.id == item.product_id)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        product_name = product.name if product else None
        product_code = product.code if product else None
        product_price = product.selling_price if product else Decimal("0")
        subtotal = product_price * item.quantity if product else Decimal("0")

        items_response.append(
            ComboItemResponse(
                id=item.id,
                combo_id=item.combo_id,
                product_id=item.product_id,
                quantity=item.quantity,
                is_required=item.is_required,
                is_default=item.is_default,
                sort_order=item.sort_order,
                notes=item.notes,
                product_name=product_name,
                product_code=product_code,
                product_price=product_price,
                subtotal=subtotal,
            )
        )

    return ComboResponse(
        id=combo.id,
        code=combo.code,
        name=combo.name,
        combo_type=combo.combo_type,
        combo_price=combo.combo_price,
        original_price=combo.original_price,
        min_select_count=combo.min_select_count,
        max_select_count=combo.max_select_count,
        start_date=combo.start_date,
        end_date=combo.end_date,
        description=combo.description,
        image_url=combo.image_url,
        is_active=combo.is_active,
        savings=combo.savings,
        discount_percentage=Decimal(str(combo.discount_percentage)),
        is_valid=combo.is_valid,
        items=items_response,
        item_count=len(items_response),
    )


@router.get(
    "",
    response_model=PaginatedResponse[ComboSummaryResponse],
    summary="取得組合列表",
)
async def get_combos(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    combo_type: Optional[ComboType] = Query(default=None, description="組合類型"),
    is_active: Optional[bool] = Query(default=None, description="是否啟用"),
    valid_only: bool = Query(default=False, description="僅顯示有效組合"),
    keyword: Optional[str] = Query(default=None, description="關鍵字搜尋"),
):
    """取得商品組合列表"""
    stmt = select(ProductCombo).where(ProductCombo.is_deleted == False)

    if combo_type:
        stmt = stmt.where(ProductCombo.combo_type == combo_type)

    if is_active is not None:
        stmt = stmt.where(ProductCombo.is_active == is_active)

    if keyword:
        stmt = stmt.where(
            (ProductCombo.code.contains(keyword))
            | (ProductCombo.name.contains(keyword))
        )

    # 計算總數
    count_result = await session.execute(stmt)
    all_combos = count_result.scalars().all()

    # 過濾有效組合
    if valid_only:
        all_combos = [c for c in all_combos if c.is_valid]

    total = len(all_combos)

    # 分頁
    offset = (page - 1) * page_size
    combos = all_combos[offset : offset + page_size]

    # 建構回應
    items = []
    for combo in combos:
        items.append(
            ComboSummaryResponse(
                id=combo.id,
                code=combo.code,
                name=combo.name,
                combo_type=combo.combo_type,
                combo_price=combo.combo_price,
                original_price=combo.original_price,
                savings=combo.savings,
                is_active=combo.is_active,
                is_valid=combo.is_valid,
                item_count=len(combo.items),
            )
        )

    return PaginatedResponse.create(
        items=items, total=total, page=page, page_size=page_size
    )


@router.post(
    "",
    response_model=ComboResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立組合",
)
async def create_combo(
    combo_data: ComboCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立商品組合"""
    # 檢查組合編號是否已存在
    stmt = select(ProductCombo).where(
        ProductCombo.code == combo_data.code,
        ProductCombo.is_deleted == False,
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail=f"組合編號 '{combo_data.code}' 已存在"
        )

    # 驗證所有商品存在
    for item in combo_data.items:
        stmt = select(Product).where(
            Product.id == item.product_id, Product.is_deleted == False
        )
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=404, detail=f"商品 ID {item.product_id} 不存在"
            )

    # 建立組合
    combo = ProductCombo(
        code=combo_data.code,
        name=combo_data.name,
        combo_type=combo_data.combo_type,
        combo_price=combo_data.combo_price,
        original_price=combo_data.original_price,
        min_select_count=combo_data.min_select_count,
        max_select_count=combo_data.max_select_count,
        start_date=combo_data.start_date,
        end_date=combo_data.end_date,
        description=combo_data.description,
        image_url=combo_data.image_url,
        created_by=current_user.id,
    )
    session.add(combo)
    await session.flush()

    # 建立組合項目
    for item_data in combo_data.items:
        item = ProductComboItem(
            combo_id=combo.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            is_required=item_data.is_required,
            is_default=item_data.is_default,
            sort_order=item_data.sort_order,
            notes=item_data.notes,
        )
        session.add(item)

    await session.commit()
    await session.refresh(combo)

    return await _build_combo_response(session, combo)


@router.get(
    "/{combo_id}",
    response_model=ComboResponse,
    summary="取得單一組合",
)
async def get_combo(
    combo_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得單一組合詳情"""
    stmt = select(ProductCombo).where(
        ProductCombo.id == combo_id,
        ProductCombo.is_deleted == False,
    )
    result = await session.execute(stmt)
    combo = result.scalar_one_or_none()

    if not combo:
        raise HTTPException(status_code=404, detail="組合不存在")

    return await _build_combo_response(session, combo)


@router.put(
    "/{combo_id}",
    response_model=ComboResponse,
    summary="更新組合",
)
async def update_combo(
    combo_id: int,
    combo_data: ComboUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新組合"""
    stmt = select(ProductCombo).where(
        ProductCombo.id == combo_id,
        ProductCombo.is_deleted == False,
    )
    result = await session.execute(stmt)
    combo = result.scalar_one_or_none()

    if not combo:
        raise HTTPException(status_code=404, detail="組合不存在")

    update_data = combo_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(combo, field, value)

    combo.updated_by = current_user.id
    session.add(combo)
    await session.commit()
    await session.refresh(combo)

    return await _build_combo_response(session, combo)


@router.delete(
    "/{combo_id}",
    response_model=MessageResponse,
    summary="刪除組合",
)
async def delete_combo(
    combo_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除組合（軟刪除）"""
    stmt = select(ProductCombo).where(
        ProductCombo.id == combo_id,
        ProductCombo.is_deleted == False,
    )
    result = await session.execute(stmt)
    combo = result.scalar_one_or_none()

    if not combo:
        raise HTTPException(status_code=404, detail="組合不存在")

    combo.is_deleted = True
    combo.updated_by = current_user.id
    session.add(combo)
    await session.commit()

    return MessageResponse(message="組合已刪除")


# ==========================================
# 組合項目管理
# ==========================================
@router.post(
    "/{combo_id}/items",
    response_model=ComboItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增組合項目",
)
async def add_combo_item(
    combo_id: int,
    item_data: ComboItemCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """新增組合項目"""
    # 驗證組合存在
    stmt = select(ProductCombo).where(
        ProductCombo.id == combo_id,
        ProductCombo.is_deleted == False,
    )
    result = await session.execute(stmt)
    combo = result.scalar_one_or_none()
    if not combo:
        raise HTTPException(status_code=404, detail="組合不存在")

    # 驗證商品存在
    stmt = select(Product).where(
        Product.id == item_data.product_id, Product.is_deleted == False
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 建立項目
    item = ProductComboItem(
        combo_id=combo_id,
        **item_data.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    return ComboItemResponse(
        id=item.id,
        combo_id=item.combo_id,
        product_id=item.product_id,
        quantity=item.quantity,
        is_required=item.is_required,
        is_default=item.is_default,
        sort_order=item.sort_order,
        notes=item.notes,
        product_name=product.name,
        product_code=product.code,
        product_price=product.selling_price,
        subtotal=product.selling_price * item.quantity,
    )


@router.put(
    "/items/{item_id}",
    response_model=ComboItemResponse,
    summary="更新組合項目",
)
async def update_combo_item(
    item_id: int,
    item_data: ComboItemUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新組合項目"""
    stmt = select(ProductComboItem).where(ProductComboItem.id == item_id)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="組合項目不存在")

    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    session.add(item)
    await session.commit()
    await session.refresh(item)

    # 取得商品資訊
    stmt = select(Product).where(Product.id == item.product_id)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()

    return ComboItemResponse(
        id=item.id,
        combo_id=item.combo_id,
        product_id=item.product_id,
        quantity=item.quantity,
        is_required=item.is_required,
        is_default=item.is_default,
        sort_order=item.sort_order,
        notes=item.notes,
        product_name=product.name if product else None,
        product_code=product.code if product else None,
        product_price=product.selling_price if product else Decimal("0"),
        subtotal=product.selling_price * item.quantity if product else Decimal("0"),
    )


@router.delete(
    "/items/{item_id}",
    response_model=MessageResponse,
    summary="刪除組合項目",
)
async def delete_combo_item(
    item_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除組合項目"""
    stmt = select(ProductComboItem).where(ProductComboItem.id == item_id)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="組合項目不存在")

    await session.delete(item)
    await session.commit()

    return MessageResponse(message="組合項目已刪除")


# ==========================================
# 組合計算
# ==========================================
@router.post(
    "/calculate",
    response_model=ComboCalculateResponse,
    summary="計算組合價格",
)
async def calculate_combo_price(
    request: ComboCalculateRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    計算組合價格

    對於固定組合，直接回傳組合價格
    對於自選組合，根據選擇的商品計算
    """
    stmt = select(ProductCombo).where(
        ProductCombo.id == request.combo_id,
        ProductCombo.is_deleted == False,
    )
    result = await session.execute(stmt)
    combo = result.scalar_one_or_none()

    if not combo:
        raise HTTPException(status_code=404, detail="組合不存在")

    selected_items = []

    if combo.combo_type == ComboType.FIXED:
        # 固定組合：使用所有項目
        for item in combo.items:
            stmt = select(Product).where(Product.id == item.product_id)
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()

            selected_items.append(
                ComboItemResponse(
                    id=item.id,
                    combo_id=item.combo_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    is_required=item.is_required,
                    is_default=item.is_default,
                    sort_order=item.sort_order,
                    notes=item.notes,
                    product_name=product.name if product else None,
                    product_code=product.code if product else None,
                    product_price=product.selling_price if product else Decimal("0"),
                    subtotal=(
                        product.selling_price * item.quantity
                        if product
                        else Decimal("0")
                    ),
                )
            )
    else:
        # 自選組合：使用選擇的商品
        if not request.selections:
            raise HTTPException(status_code=400, detail="自選組合需要提供選擇的商品")

        # 驗證選擇數量
        if combo.min_select_count and len(request.selections) < combo.min_select_count:
            raise HTTPException(
                status_code=400,
                detail=f"至少需要選擇 {combo.min_select_count} 項商品",
            )
        if combo.max_select_count and len(request.selections) > combo.max_select_count:
            raise HTTPException(
                status_code=400,
                detail=f"最多只能選擇 {combo.max_select_count} 項商品",
            )

        for selection in request.selections:
            stmt = select(Product).where(
                Product.id == selection.product_id, Product.is_deleted == False
            )
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"商品 ID {selection.product_id} 不存在",
                )

            selected_items.append(
                ComboItemResponse(
                    id=0,
                    combo_id=combo.id,
                    product_id=selection.product_id,
                    quantity=selection.quantity,
                    is_required=False,
                    is_default=False,
                    sort_order=0,
                    notes=None,
                    product_name=product.name,
                    product_code=product.code,
                    product_price=product.selling_price,
                    subtotal=product.selling_price * selection.quantity,
                )
            )

    return ComboCalculateResponse(
        combo_id=combo.id,
        combo_name=combo.name,
        combo_price=combo.combo_price,
        original_price=combo.original_price,
        savings=combo.savings,
        discount_percentage=Decimal(str(combo.discount_percentage)),
        is_valid=combo.is_valid,
        selected_items=selected_items,
    )
