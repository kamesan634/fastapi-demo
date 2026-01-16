"""
商品標籤列印 API

提供商品標籤列印功能。

功能：
- F03-007: 商品標籤列印
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, Response
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.product import Category, Product, Unit
from app.kamesan.models.store import Store
from app.kamesan.schemas.product_label import (
    LabelData,
    LabelFormat,
    LabelPreviewResponse,
    LabelPrintByCategory,
    LabelPrintRequest,
    LabelPrintResponse,
    LabelSize,
    OutputFormat,
)

router = APIRouter()


def generate_html_label(label: LabelData, size: LabelSize, format_type: LabelFormat) -> str:
    """生成單一標籤的 HTML"""
    # 根據尺寸設定寬高
    sizes = {
        LabelSize.SMALL: ("30mm", "20mm", "8px", "10px"),
        LabelSize.MEDIUM: ("50mm", "30mm", "10px", "12px"),
        LabelSize.LARGE: ("70mm", "50mm", "12px", "16px"),
        LabelSize.CUSTOM: ("60mm", "40mm", "11px", "14px"),
    }
    width, height, small_font, large_font = sizes.get(size, sizes[LabelSize.MEDIUM])

    barcode_html = ""
    if label.barcode:
        # 使用 Code128 條碼字型顯示（實際應用中可使用 JS 條碼庫）
        barcode_html = f'<div class="barcode">*{label.barcode}*</div>'

    if format_type == LabelFormat.PRICE_TAG:
        return f"""
        <div class="label price-tag" style="width:{width};height:{height};">
            <div class="product-name" style="font-size:{small_font};">{label.product_name}</div>
            <div class="price" style="font-size:24px;font-weight:bold;">${label.price}</div>
            {barcode_html}
        </div>
        """
    elif format_type == LabelFormat.BARCODE_ONLY:
        return f"""
        <div class="label barcode-only" style="width:{width};height:{height};">
            {barcode_html}
            <div class="code" style="font-size:{small_font};">{label.product_code}</div>
        </div>
        """
    elif format_type == LabelFormat.SHELF_LABEL:
        location = label.shelf_location or "---"
        return f"""
        <div class="label shelf-label" style="width:{width};height:{height};">
            <div class="location" style="font-size:{small_font};">位置: {location}</div>
            <div class="product-name" style="font-size:{large_font};">{label.product_name}</div>
            <div class="price" style="font-size:{large_font};font-weight:bold;">${label.price}</div>
            <div class="code" style="font-size:{small_font};">{label.product_code}</div>
        </div>
        """
    else:  # STANDARD
        return f"""
        <div class="label standard" style="width:{width};height:{height};">
            <div class="product-name" style="font-size:{large_font};">{label.product_name}</div>
            <div class="product-code" style="font-size:{small_font};">{label.product_code}</div>
            <div class="price" style="font-size:{large_font};font-weight:bold;">${label.price}</div>
            {barcode_html}
        </div>
        """


def generate_zpl_label(label: LabelData) -> str:
    """生成 ZPL 格式標籤（Zebra 印表機）"""
    barcode_zpl = ""
    if label.barcode:
        barcode_zpl = f"^BY2^BC,80,Y,N,N^FD{label.barcode}^FS"

    return f"""
^XA
^FO20,20^A0N,30,30^FD{label.product_name[:20]}^FS
^FO20,60^A0N,20,20^FD{label.product_code}^FS
^FO20,90^A0N,40,40^FD${label.price}^FS
^FO20,140{barcode_zpl}
^XZ
"""


@router.post("/labels/print", response_model=LabelPrintResponse)
async def print_labels(
    request: LabelPrintRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> LabelPrintResponse:
    """
    生成標籤列印資料

    根據指定的商品列表生成標籤資料。
    """
    labels: List[LabelData] = []

    # 取得門市資訊（如果有指定）
    store_name = None
    if request.store_id:
        store = await session.get(Store, request.store_id)
        if store:
            store_name = store.name

    for item in request.items:
        # 取得商品資料
        product = await session.get(Product, item.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"商品 ID {item.product_id} 不存在",
            )

        # 取得關聯資料
        unit_name = None
        if product.unit_id:
            unit = await session.get(Unit, product.unit_id)
            if unit:
                unit_name = unit.name

        category_name = None
        if product.category_id:
            category = await session.get(Category, product.category_id)
            if category:
                category_name = category.name

        # 決定價格
        price = item.custom_price if item.custom_price is not None else product.selling_price

        # 生成指定數量的標籤
        for _ in range(item.quantity):
            label_data = LabelData(
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                barcode=product.barcode if request.include_barcode else None,
                price=price if request.include_price else Decimal("0"),
                unit_name=unit_name,
                category_name=category_name,
                store_name=store_name,
            )
            labels.append(label_data)

    return LabelPrintResponse(
        labels=labels,
        total_count=len(labels),
        label_format=request.label_format,
        label_size=request.label_size,
        output_format=request.output_format,
    )


@router.post("/labels/preview", response_class=HTMLResponse)
async def preview_labels(
    request: LabelPrintRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> HTMLResponse:
    """
    預覽標籤（HTML 格式）

    生成可在瀏覽器中預覽並列印的 HTML 頁面。
    """
    # 先取得標籤資料
    labels_response = await print_labels(request, session, current_user)
    labels = labels_response.labels

    # 生成 HTML
    labels_html = "\n".join(
        generate_html_label(label, request.label_size, request.label_format)
        for label in labels
    )

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>商品標籤列印</title>
    <style>
        @media print {{
            body {{ margin: 0; }}
            .no-print {{ display: none; }}
        }}
        body {{
            font-family: Arial, sans-serif;
            padding: 10px;
        }}
        .label {{
            border: 1px solid #333;
            padding: 5px;
            margin: 5px;
            display: inline-block;
            text-align: center;
            box-sizing: border-box;
            vertical-align: top;
            overflow: hidden;
        }}
        .product-name {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .price {{
            color: #d00;
        }}
        .barcode {{
            font-family: 'Libre Barcode 128', monospace;
            font-size: 24px;
        }}
        .code {{
            color: #666;
        }}
        .print-button {{
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }}
        .print-button:hover {{
            background: #0056b3;
        }}
        .info {{
            margin-bottom: 20px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <button class="print-button no-print" onclick="window.print()">列印標籤</button>
    <div class="info no-print">
        <strong>標籤數量：</strong> {len(labels)} 張 |
        <strong>格式：</strong> {request.label_format.value} |
        <strong>尺寸：</strong> {request.label_size.value}
    </div>
    <div class="labels-container">
        {labels_html}
    </div>
</body>
</html>
"""

    return HTMLResponse(content=html_content)


@router.post("/labels/zpl")
async def generate_zpl_labels(
    request: LabelPrintRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Response:
    """
    生成 ZPL 格式標籤

    用於 Zebra 標籤印表機。
    """
    # 先取得標籤資料
    labels_response = await print_labels(request, session, current_user)
    labels = labels_response.labels

    # 生成 ZPL
    zpl_content = "\n".join(generate_zpl_label(label) for label in labels)

    return Response(
        content=zpl_content,
        media_type="application/x-zpl",
        headers={"Content-Disposition": "attachment; filename=labels.zpl"},
    )


@router.post("/labels/by-category", response_model=LabelPrintResponse)
async def print_labels_by_category(
    request: LabelPrintByCategory,
    session: SessionDep,
    current_user: CurrentUser,
) -> LabelPrintResponse:
    """
    依類別列印標籤

    列印指定類別下所有商品的標籤。
    """
    # 驗證類別存在
    category = await session.get(Category, request.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="類別不存在",
        )

    # 查詢類別下的商品
    query = select(Product).where(
        Product.category_id == request.category_id,
        Product.is_deleted == False,
    )
    if not request.include_inactive:
        query = query.where(Product.is_active == True)

    result = await session.execute(query)
    products = result.scalars().all()

    if not products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="該類別下沒有商品",
        )

    # 轉換為標籤列印請求
    from app.kamesan.schemas.product_label import LabelPrintItem

    items = [
        LabelPrintItem(product_id=p.id, quantity=request.quantity_per_product)
        for p in products
    ]

    label_request = LabelPrintRequest(
        items=items,
        label_format=request.label_format,
        label_size=request.label_size,
        output_format=request.output_format,
    )

    return await print_labels(label_request, session, current_user)


@router.get("/labels/products")
async def get_products_for_labels(
    session: SessionDep,
    current_user: CurrentUser,
    category_id: Optional[int] = Query(None, description="類別 ID"),
    search: Optional[str] = Query(None, max_length=50, description="搜尋關鍵字"),
    limit: int = Query(50, ge=1, le=200, description="回傳數量"),
) -> List[dict]:
    """
    取得可列印標籤的商品列表

    用於前端選擇要列印標籤的商品。
    """
    query = select(Product).where(
        Product.is_deleted == False,
        Product.is_active == True,
    )

    if category_id:
        query = query.where(Product.category_id == category_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Product.code.ilike(search_pattern))
            | (Product.name.ilike(search_pattern))
            | (Product.barcode.ilike(search_pattern))
        )

    query = query.limit(limit)

    result = await session.execute(query)
    products = result.scalars().all()

    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "barcode": p.barcode,
            "selling_price": float(p.selling_price),
        }
        for p in products
    ]
