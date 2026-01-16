"""
商品規格管理 API 端點

提供商品規格定義與變體的 CRUD 操作，以及批次產生變體功能。
"""

from itertools import product as itertools_product
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.product import Product
from app.kamesan.models.variant import ProductSpecification, ProductVariant
from app.kamesan.schemas.common import MessageResponse, PaginatedResponse
from app.kamesan.schemas.variant import (
    BulkOperationResponse,
    BulkVariantCreateRequest,
    GenerateVariantsRequest,
    GenerateVariantsResponse,
    SpecificationCreate,
    SpecificationResponse,
    SpecificationUpdate,
    VariantCreate,
    VariantResponse,
    VariantSummaryResponse,
    VariantUpdate,
)

router = APIRouter()


# ==========================================
# 規格定義 API
# ==========================================
@router.get(
    "/products/{product_id}/specifications",
    response_model=List[SpecificationResponse],
    summary="取得商品規格定義列表",
)
async def get_specifications(
    product_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得指定商品的規格定義列表"""
    # 驗證商品存在
    stmt = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 取得規格列表
    stmt = (
        select(ProductSpecification)
        .where(
            ProductSpecification.product_id == product_id,
            ProductSpecification.is_deleted == False,
        )
        .order_by(ProductSpecification.sort_order)
    )
    result = await session.execute(stmt)
    specifications = result.scalars().all()

    return specifications


@router.post(
    "/products/{product_id}/specifications",
    response_model=SpecificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立商品規格定義",
)
async def create_specification(
    product_id: int,
    spec_data: SpecificationCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立商品規格定義"""
    # 驗證商品存在
    stmt = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 檢查規格名稱是否已存在
    stmt = select(ProductSpecification).where(
        ProductSpecification.product_id == product_id,
        ProductSpecification.name == spec_data.name,
        ProductSpecification.is_deleted == False,
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"規格名稱 '{spec_data.name}' 已存在")

    specification = ProductSpecification(
        product_id=product_id,
        **spec_data.model_dump(),
        created_by=current_user.id,
    )
    session.add(specification)
    await session.commit()
    await session.refresh(specification)

    return specification


@router.put(
    "/specifications/{spec_id}",
    response_model=SpecificationResponse,
    summary="更新規格定義",
)
async def update_specification(
    spec_id: int,
    spec_data: SpecificationUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新規格定義"""
    stmt = select(ProductSpecification).where(
        ProductSpecification.id == spec_id,
        ProductSpecification.is_deleted == False,
    )
    result = await session.execute(stmt)
    specification = result.scalar_one_or_none()

    if not specification:
        raise HTTPException(status_code=404, detail="規格定義不存在")

    update_data = spec_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(specification, field, value)

    specification.updated_by = current_user.id
    session.add(specification)
    await session.commit()
    await session.refresh(specification)

    return specification


@router.delete(
    "/specifications/{spec_id}",
    response_model=MessageResponse,
    summary="刪除規格定義",
)
async def delete_specification(
    spec_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除規格定義（軟刪除）"""
    stmt = select(ProductSpecification).where(
        ProductSpecification.id == spec_id,
        ProductSpecification.is_deleted == False,
    )
    result = await session.execute(stmt)
    specification = result.scalar_one_or_none()

    if not specification:
        raise HTTPException(status_code=404, detail="規格定義不存在")

    specification.is_deleted = True
    specification.updated_by = current_user.id
    session.add(specification)
    await session.commit()

    return MessageResponse(message="規格定義已刪除")


# ==========================================
# 規格變體 API
# ==========================================
@router.get(
    "/products/{product_id}/variants",
    response_model=PaginatedResponse[VariantResponse],
    summary="取得商品變體列表",
)
async def get_variants(
    product_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None, description="是否啟用"),
):
    """取得指定商品的變體列表"""
    # 驗證商品存在
    stmt = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 建立查詢
    stmt = select(ProductVariant).where(
        ProductVariant.product_id == product_id,
        ProductVariant.is_deleted == False,
    )

    if is_active is not None:
        stmt = stmt.where(ProductVariant.is_active == is_active)

    # 計算總數
    count_result = await session.execute(stmt)
    total = len(count_result.all())

    # 分頁查詢
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(ProductVariant.id)
    result = await session.execute(stmt)
    variants = result.scalars().all()

    # 填充有效價格
    response_variants = []
    for variant in variants:
        variant_data = VariantResponse.model_validate(variant)
        variant_data.effective_cost_price = (
            variant.cost_price if variant.cost_price else product.cost_price
        )
        variant_data.effective_selling_price = (
            variant.selling_price if variant.selling_price else product.selling_price
        )
        variant_data.variant_name = "-".join(str(v) for v in variant.variant_options.values())
        response_variants.append(variant_data)

    return PaginatedResponse.create(
        items=response_variants, total=total, page=page, page_size=page_size
    )


@router.post(
    "/products/{product_id}/variants",
    response_model=VariantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立商品變體",
)
async def create_variant(
    product_id: int,
    variant_data: VariantCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立商品變體"""
    # 驗證商品存在
    stmt = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 檢查 SKU 是否已存在
    stmt = select(ProductVariant).where(ProductVariant.sku == variant_data.sku)
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"SKU '{variant_data.sku}' 已存在")

    # 檢查條碼是否已存在
    if variant_data.barcode:
        stmt = select(ProductVariant).where(
            ProductVariant.barcode == variant_data.barcode
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail=f"條碼 '{variant_data.barcode}' 已存在"
            )

    variant = ProductVariant(
        product_id=product_id,
        **variant_data.model_dump(),
        created_by=current_user.id,
    )
    session.add(variant)
    await session.commit()
    await session.refresh(variant)

    return variant


@router.get(
    "/variants/{variant_id}",
    response_model=VariantResponse,
    summary="取得單一變體",
)
async def get_variant(
    variant_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得單一變體詳情"""
    stmt = select(ProductVariant).where(
        ProductVariant.id == variant_id,
        ProductVariant.is_deleted == False,
    )
    result = await session.execute(stmt)
    variant = result.scalar_one_or_none()

    if not variant:
        raise HTTPException(status_code=404, detail="變體不存在")

    return variant


@router.put(
    "/variants/{variant_id}",
    response_model=VariantResponse,
    summary="更新變體",
)
async def update_variant(
    variant_id: int,
    variant_data: VariantUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新變體"""
    stmt = select(ProductVariant).where(
        ProductVariant.id == variant_id,
        ProductVariant.is_deleted == False,
    )
    result = await session.execute(stmt)
    variant = result.scalar_one_or_none()

    if not variant:
        raise HTTPException(status_code=404, detail="變體不存在")

    # 檢查 SKU 唯一性
    if variant_data.sku and variant_data.sku != variant.sku:
        stmt = select(ProductVariant).where(ProductVariant.sku == variant_data.sku)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"SKU '{variant_data.sku}' 已存在")

    # 檢查條碼唯一性
    if variant_data.barcode and variant_data.barcode != variant.barcode:
        stmt = select(ProductVariant).where(
            ProductVariant.barcode == variant_data.barcode
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail=f"條碼 '{variant_data.barcode}' 已存在"
            )

    update_data = variant_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(variant, field, value)

    variant.updated_by = current_user.id
    session.add(variant)
    await session.commit()
    await session.refresh(variant)

    return variant


@router.delete(
    "/variants/{variant_id}",
    response_model=MessageResponse,
    summary="刪除變體",
)
async def delete_variant(
    variant_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除變體（軟刪除）"""
    stmt = select(ProductVariant).where(
        ProductVariant.id == variant_id,
        ProductVariant.is_deleted == False,
    )
    result = await session.execute(stmt)
    variant = result.scalar_one_or_none()

    if not variant:
        raise HTTPException(status_code=404, detail="變體不存在")

    variant.is_deleted = True
    variant.updated_by = current_user.id
    session.add(variant)
    await session.commit()

    return MessageResponse(message="變體已刪除")


# ==========================================
# 批次操作 API
# ==========================================
@router.post(
    "/products/{product_id}/variants/generate",
    response_model=GenerateVariantsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="批次產生變體",
)
async def generate_variants(
    product_id: int,
    request: GenerateVariantsRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    根據規格定義批次產生所有變體組合

    例如：
    - 規格1: 顏色 [白色, 黑色]
    - 規格2: 尺寸 [S, M, L]

    將產生 2 x 3 = 6 個變體
    """
    # 驗證商品存在
    stmt = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    sku_prefix = request.sku_prefix or product.code

    # 建立規格定義
    created_specs = []
    for idx, spec_data in enumerate(request.specifications):
        # 檢查規格名稱是否已存在
        stmt = select(ProductSpecification).where(
            ProductSpecification.product_id == product_id,
            ProductSpecification.name == spec_data.name,
            ProductSpecification.is_deleted == False,
        )
        result = await session.execute(stmt)
        existing_spec = result.scalar_one_or_none()

        if existing_spec:
            # 更新現有規格
            existing_spec.options = spec_data.options
            existing_spec.sort_order = spec_data.sort_order
            existing_spec.updated_by = current_user.id
            session.add(existing_spec)
            created_specs.append(existing_spec)
        else:
            # 建立新規格
            spec = ProductSpecification(
                product_id=product_id,
                name=spec_data.name,
                options=spec_data.options,
                sort_order=idx,
                created_by=current_user.id,
            )
            session.add(spec)
            created_specs.append(spec)

    await session.flush()

    # 產生所有變體組合
    spec_options = [(spec.name, spec.options) for spec in created_specs]
    option_combinations = list(
        itertools_product(*[options for _, options in spec_options])
    )

    created_variants = []
    for idx, combination in enumerate(option_combinations):
        # 建立規格組合字典
        variant_options = {}
        sku_parts = [sku_prefix]
        for i, (spec_name, _) in enumerate(spec_options):
            variant_options[spec_name] = combination[i]
            # 簡化 SKU 中的選項值
            sku_parts.append(combination[i][:3].upper())

        sku = "-".join(sku_parts)

        # 檢查 SKU 是否已存在
        stmt = select(ProductVariant).where(ProductVariant.sku == sku)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            # SKU 已存在，加上序號
            sku = f"{sku}-{idx+1}"

        variant = ProductVariant(
            product_id=product_id,
            sku=sku,
            variant_options=variant_options,
            cost_price=request.base_cost_price,
            selling_price=request.base_selling_price,
            created_by=current_user.id,
        )
        session.add(variant)
        created_variants.append(variant)

    await session.commit()

    # 準備回應
    variants_response = []
    for variant in created_variants:
        await session.refresh(variant)
        variants_response.append(
            VariantSummaryResponse(
                id=variant.id,
                sku=variant.sku,
                variant_options=variant.variant_options,
                selling_price=variant.selling_price,
                stock_quantity=variant.stock_quantity,
                is_active=variant.is_active,
            )
        )

    return GenerateVariantsResponse(
        specifications_created=len(created_specs),
        variants_created=len(created_variants),
        variants=variants_response,
    )


@router.post(
    "/products/{product_id}/variants/bulk",
    response_model=BulkOperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="批次建立變體",
)
async def bulk_create_variants(
    product_id: int,
    request: BulkVariantCreateRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """批次建立多個變體"""
    # 驗證商品存在
    stmt = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    success_count = 0
    failed_count = 0
    errors = []

    for variant_data in request.variants:
        try:
            # 檢查 SKU 是否已存在
            stmt = select(ProductVariant).where(ProductVariant.sku == variant_data.sku)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                failed_count += 1
                errors.append(f"SKU '{variant_data.sku}' 已存在")
                continue

            # 檢查條碼是否已存在
            if variant_data.barcode:
                stmt = select(ProductVariant).where(
                    ProductVariant.barcode == variant_data.barcode
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    failed_count += 1
                    errors.append(f"條碼 '{variant_data.barcode}' 已存在")
                    continue

            variant = ProductVariant(
                product_id=product_id,
                **variant_data.model_dump(),
                created_by=current_user.id,
            )
            session.add(variant)
            success_count += 1

        except Exception as e:
            failed_count += 1
            errors.append(f"建立變體 '{variant_data.sku}' 失敗: {str(e)}")

    await session.commit()

    return BulkOperationResponse(
        success_count=success_count,
        failed_count=failed_count,
        errors=errors,
    )


@router.get(
    "/variants/barcode/{barcode}",
    response_model=VariantResponse,
    summary="依條碼查詢變體",
)
async def get_variant_by_barcode(
    barcode: str,
    session: SessionDep,
    current_user: CurrentUser,
):
    """依條碼查詢變體"""
    stmt = select(ProductVariant).where(
        ProductVariant.barcode == barcode,
        ProductVariant.is_deleted == False,
    )
    result = await session.execute(stmt)
    variant = result.scalar_one_or_none()

    if not variant:
        raise HTTPException(status_code=404, detail="變體不存在")

    return variant


@router.get(
    "/variants/sku/{sku}",
    response_model=VariantResponse,
    summary="依 SKU 查詢變體",
)
async def get_variant_by_sku(
    sku: str,
    session: SessionDep,
    current_user: CurrentUser,
):
    """依 SKU 查詢變體"""
    stmt = select(ProductVariant).where(
        ProductVariant.sku == sku,
        ProductVariant.is_deleted == False,
    )
    result = await session.execute(stmt)
    variant = result.scalar_one_or_none()

    if not variant:
        raise HTTPException(status_code=404, detail="變體不存在")

    return variant
