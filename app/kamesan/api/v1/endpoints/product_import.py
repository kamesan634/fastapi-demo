"""
商品匯入匯出 API 端點

提供商品的批次匯入與匯出功能。
"""

import csv
import io
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.product import Category, Product, TaxType, Unit
from app.kamesan.models.supplier import Supplier
from app.kamesan.schemas.product_import import (
    ExportFormat,
    ExportRequest,
    ImportMode,
    ImportRequest,
    ImportResult,
    ImportStatus,
    ImportTemplateResponse,
    ImportValidationResult,
    ProductImportPreview,
    TemplateField,
    ValidationError,
)

router = APIRouter()


# 範本欄位定義
TEMPLATE_FIELDS = [
    TemplateField(
        field_name="code",
        display_name="商品編號",
        required=False,
        data_type="文字",
        description="唯一值，新增時可空白自動產生",
        example="PRD001",
    ),
    TemplateField(
        field_name="name",
        display_name="商品名稱",
        required=True,
        data_type="文字",
        description="必填，1-100字元",
        example="經典白色T-Shirt",
    ),
    TemplateField(
        field_name="barcode",
        display_name="商品條碼",
        required=False,
        data_type="文字",
        description="唯一值，支援EAN-13/UPC",
        example="4710088012345",
    ),
    TemplateField(
        field_name="category_code",
        display_name="分類代碼",
        required=True,
        data_type="文字",
        description="必須為系統已存在分類",
        example="CAT001",
    ),
    TemplateField(
        field_name="unit_code",
        display_name="計量單位",
        required=True,
        data_type="文字",
        description="必須為系統已存在單位",
        example="PCS",
    ),
    TemplateField(
        field_name="cost_price",
        display_name="成本價",
        required=True,
        data_type="數值",
        description="必填，正數",
        example="150.00",
    ),
    TemplateField(
        field_name="selling_price",
        display_name="標準售價",
        required=True,
        data_type="數值",
        description="必填，正數",
        example="299.00",
    ),
    TemplateField(
        field_name="min_stock",
        display_name="安全庫存",
        required=False,
        data_type="整數",
        description="正整數，預設0",
        example="50",
    ),
    TemplateField(
        field_name="supplier_code",
        display_name="供應商代碼",
        required=False,
        data_type="文字",
        description="必須為系統已存在供應商",
        example="SUP001",
    ),
    TemplateField(
        field_name="status",
        display_name="狀態",
        required=False,
        data_type="文字",
        description="ACTIVE/INACTIVE，預設ACTIVE",
        example="ACTIVE",
    ),
]


@router.get(
    "/products/import/template",
    response_model=ImportTemplateResponse,
    summary="取得匯入範本說明",
)
async def get_import_template(
    current_user: CurrentUser,
):
    """取得商品匯入範本的欄位說明"""
    return ImportTemplateResponse(
        fields=TEMPLATE_FIELDS,
        notes=[
            "請使用 UTF-8 編碼的 CSV 檔案",
            "第一列為標題列，從第二列開始為資料",
            "商品編號在新增時可留空，系統會自動產生",
            "分類代碼、計量單位、供應商代碼必須為系統已存在的資料",
            "數值欄位請勿包含千分位符號",
        ],
    )


@router.get(
    "/products/import/template/download",
    summary="下載匯入範本",
)
async def download_import_template(
    current_user: CurrentUser,
):
    """下載 CSV 格式的匯入範本"""
    output = io.StringIO()
    writer = csv.writer(output)

    # 寫入標題列
    headers = [f.field_name for f in TEMPLATE_FIELDS]
    writer.writerow(headers)

    # 寫入範例資料
    example_row = [f.example for f in TEMPLATE_FIELDS]
    writer.writerow(example_row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=product_import_template.csv"
        },
    )


@router.post(
    "/products/import/validate",
    response_model=ImportValidationResult,
    summary="驗證匯入檔案",
)
async def validate_import_file(
    file: UploadFile = File(...),
    mode: ImportMode = Query(default=ImportMode.UPSERT),
    session: SessionDep = None,
    current_user: CurrentUser = None,
):
    """
    驗證匯入檔案並回傳驗證結果

    檢核項目：
    - 必填欄位
    - 資料格式
    - 重複值
    - 關聯資料存在性
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="僅支援 CSV 格式檔案")

    content = await file.read()
    try:
        text_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text_content = content.decode("big5")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="檔案編碼格式錯誤，請使用 UTF-8 編碼")

    reader = csv.DictReader(io.StringIO(text_content))

    errors: List[ValidationError] = []
    preview: List[ProductImportPreview] = []
    insert_count = 0
    update_count = 0
    skip_count = 0

    # 預先載入關聯資料
    categories = {}
    units = {}
    suppliers = {}
    existing_codes = set()
    existing_barcodes = set()

    # 載入分類
    stmt = select(Category).where(Category.is_deleted == False)
    result = await session.execute(stmt)
    for cat in result.scalars().all():
        categories[cat.code] = cat.id

    # 載入單位
    stmt = select(Unit)
    result = await session.execute(stmt)
    for unit in result.scalars().all():
        units[unit.code] = unit.id

    # 載入供應商
    stmt = select(Supplier).where(Supplier.is_deleted == False)
    result = await session.execute(stmt)
    for sup in result.scalars().all():
        suppliers[sup.code] = sup.id

    # 載入現有商品編號和條碼
    stmt = select(Product.code, Product.barcode).where(Product.is_deleted == False)
    result = await session.execute(stmt)
    for row in result.all():
        existing_codes.add(row[0])
        if row[1]:
            existing_barcodes.add(row[1])

    row_number = 1
    for row in reader:
        row_number += 1
        row_errors = []
        has_error = False

        # 驗證必填欄位
        name = row.get("name", "").strip()
        if not name:
            row_errors.append("商品名稱為必填欄位")
            errors.append(
                ValidationError(row_number=row_number, field="name", error="商品名稱為必填欄位")
            )
            has_error = True

        category_code = row.get("category_code", "").strip()
        if not category_code:
            row_errors.append("分類代碼為必填欄位")
            errors.append(
                ValidationError(
                    row_number=row_number, field="category_code", error="分類代碼為必填欄位"
                )
            )
            has_error = True
        elif category_code not in categories:
            row_errors.append(f"分類代碼 '{category_code}' 不存在")
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field="category_code",
                    error=f"分類代碼 '{category_code}' 不存在",
                )
            )
            has_error = True

        unit_code = row.get("unit_code", "").strip()
        if not unit_code:
            row_errors.append("計量單位為必填欄位")
            errors.append(
                ValidationError(
                    row_number=row_number, field="unit_code", error="計量單位為必填欄位"
                )
            )
            has_error = True
        elif unit_code not in units:
            row_errors.append(f"計量單位 '{unit_code}' 不存在")
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field="unit_code",
                    error=f"計量單位 '{unit_code}' 不存在",
                )
            )
            has_error = True

        # 驗證數值欄位
        cost_price = row.get("cost_price", "").strip()
        if not cost_price:
            row_errors.append("成本價為必填欄位")
            errors.append(
                ValidationError(
                    row_number=row_number, field="cost_price", error="成本價為必填欄位"
                )
            )
            has_error = True
        else:
            try:
                cost_val = Decimal(cost_price)
                if cost_val < 0:
                    raise ValueError()
            except (InvalidOperation, ValueError):
                row_errors.append("成本價必須為正數")
                errors.append(
                    ValidationError(
                        row_number=row_number, field="cost_price", error="成本價必須為正數"
                    )
                )
                has_error = True

        selling_price = row.get("selling_price", "").strip()
        if not selling_price:
            row_errors.append("標準售價為必填欄位")
            errors.append(
                ValidationError(
                    row_number=row_number, field="selling_price", error="標準售價為必填欄位"
                )
            )
            has_error = True
        else:
            try:
                sell_val = Decimal(selling_price)
                if sell_val < 0:
                    raise ValueError()
            except (InvalidOperation, ValueError):
                row_errors.append("標準售價必須為正數")
                errors.append(
                    ValidationError(
                        row_number=row_number, field="selling_price", error="標準售價必須為正數"
                    )
                )
                has_error = True

        # 驗證供應商
        supplier_code = row.get("supplier_code", "").strip()
        if supplier_code and supplier_code not in suppliers:
            row_errors.append(f"供應商代碼 '{supplier_code}' 不存在")
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field="supplier_code",
                    error=f"供應商代碼 '{supplier_code}' 不存在",
                )
            )
            has_error = True

        # 驗證商品編號與條碼唯一性
        code = row.get("code", "").strip()
        barcode = row.get("barcode", "").strip()

        is_update = code and code in existing_codes
        action = "更新" if is_update else "新增"

        if mode == ImportMode.INSERT and is_update:
            row_errors.append(f"商品編號 '{code}' 已存在，INSERT 模式不允許更新")
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field="code",
                    error=f"商品編號 '{code}' 已存在",
                )
            )
            has_error = True
            skip_count += 1
        elif mode == ImportMode.UPDATE and not is_update:
            row_errors.append(f"商品編號 '{code}' 不存在，UPDATE 模式不允許新增")
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field="code",
                    error=f"商品編號不存在",
                )
            )
            has_error = True
            skip_count += 1
        else:
            if is_update:
                update_count += 1
            else:
                insert_count += 1

        # 條碼唯一性檢查
        if barcode and not is_update and barcode in existing_barcodes:
            row_errors.append(f"條碼 '{barcode}' 已被使用")
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field="barcode",
                    error=f"條碼 '{barcode}' 已被使用",
                )
            )
            has_error = True

        # 加入預覽
        preview.append(
            ProductImportPreview(
                row_number=row_number,
                code=code if code else "(自動產生)",
                name=name,
                category_code=category_code,
                unit_code=unit_code,
                cost_price=Decimal(cost_price) if cost_price else Decimal("0"),
                selling_price=Decimal(selling_price) if selling_price else Decimal("0"),
                action=action,
                has_error=has_error,
                errors=row_errors,
            )
        )

    total_rows = row_number - 1
    valid_rows = total_rows - len(set(e.row_number for e in errors))

    return ImportValidationResult(
        total_rows=total_rows,
        valid_rows=valid_rows,
        error_rows=total_rows - valid_rows,
        insert_count=insert_count,
        update_count=update_count,
        skip_count=skip_count,
        errors=errors,
        preview=preview[:100],  # 只回傳前100筆預覽
    )


@router.post(
    "/products/import",
    response_model=ImportResult,
    summary="執行商品匯入",
)
async def import_products(
    file: UploadFile = File(...),
    mode: ImportMode = Query(default=ImportMode.UPSERT),
    skip_errors: bool = Query(default=False, description="是否跳過錯誤資料"),
    auto_generate_code: bool = Query(default=True, description="是否自動產生商品編號"),
    session: SessionDep = None,
    current_user: CurrentUser = None,
):
    """
    執行商品批次匯入

    匯入模式：
    - insert: 僅新增，遇到已存在商品編號則跳過
    - update: 僅更新，遇到不存在商品編號則跳過
    - upsert: 新增或更新，存在則更新，不存在則新增
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="僅支援 CSV 格式檔案")

    content = await file.read()
    try:
        text_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text_content = content.decode("big5")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="檔案編碼格式錯誤")

    reader = csv.DictReader(io.StringIO(text_content))

    # 預先載入關聯資料
    categories = {}
    units = {}
    suppliers = {}

    stmt = select(Category).where(Category.is_deleted == False)
    result = await session.execute(stmt)
    for cat in result.scalars().all():
        categories[cat.code] = cat.id

    stmt = select(Unit)
    result = await session.execute(stmt)
    for unit in result.scalars().all():
        units[unit.code] = unit.id

    stmt = select(Supplier).where(Supplier.is_deleted == False)
    result = await session.execute(stmt)
    for sup in result.scalars().all():
        suppliers[sup.code] = sup.id

    errors: List[ValidationError] = []
    success_count = 0
    insert_count = 0
    update_count = 0
    failed_count = 0
    skip_count = 0
    row_number = 1

    for row in reader:
        row_number += 1

        try:
            # 解析資料
            code = row.get("code", "").strip()
            name = row.get("name", "").strip()
            barcode = row.get("barcode", "").strip() or None
            category_code = row.get("category_code", "").strip()
            unit_code = row.get("unit_code", "").strip()
            cost_price = row.get("cost_price", "").strip()
            selling_price = row.get("selling_price", "").strip()
            min_stock = row.get("min_stock", "").strip()
            supplier_code = row.get("supplier_code", "").strip()
            status_str = row.get("status", "ACTIVE").strip().upper()

            # 驗證必填欄位
            if not name or not category_code or not unit_code or not cost_price or not selling_price:
                if skip_errors:
                    skip_count += 1
                    continue
                errors.append(
                    ValidationError(
                        row_number=row_number, field="", error="必填欄位不完整"
                    )
                )
                failed_count += 1
                continue

            # 驗證關聯資料
            category_id = categories.get(category_code)
            unit_id = units.get(unit_code)
            supplier_id = suppliers.get(supplier_code) if supplier_code else None

            if not category_id:
                if skip_errors:
                    skip_count += 1
                    continue
                errors.append(
                    ValidationError(
                        row_number=row_number,
                        field="category_code",
                        error=f"分類代碼 '{category_code}' 不存在",
                    )
                )
                failed_count += 1
                continue

            if not unit_id:
                if skip_errors:
                    skip_count += 1
                    continue
                errors.append(
                    ValidationError(
                        row_number=row_number,
                        field="unit_code",
                        error=f"計量單位 '{unit_code}' 不存在",
                    )
                )
                failed_count += 1
                continue

            # 轉換數值
            cost_val = Decimal(cost_price)
            sell_val = Decimal(selling_price)
            stock_val = int(min_stock) if min_stock else 0

            # 檢查商品是否存在
            existing_product = None
            if code:
                stmt = select(Product).where(
                    Product.code == code, Product.is_deleted == False
                )
                result = await session.execute(stmt)
                existing_product = result.scalar_one_or_none()

            if existing_product:
                # 更新模式
                if mode == ImportMode.INSERT:
                    skip_count += 1
                    continue

                existing_product.name = name
                existing_product.barcode = barcode
                existing_product.category_id = category_id
                existing_product.unit_id = unit_id
                existing_product.cost_price = cost_val
                existing_product.selling_price = sell_val
                existing_product.min_stock = stock_val
                existing_product.supplier_id = supplier_id
                existing_product.is_active = status_str == "ACTIVE"
                existing_product.updated_by = current_user.id
                session.add(existing_product)
                update_count += 1
                success_count += 1
            else:
                # 新增模式
                if mode == ImportMode.UPDATE:
                    skip_count += 1
                    continue

                # 自動產生商品編號
                if not code and auto_generate_code:
                    # 簡單的編號產生邏輯
                    import uuid
                    code = f"PRD{uuid.uuid4().hex[:8].upper()}"

                new_product = Product(
                    code=code,
                    name=name,
                    barcode=barcode,
                    category_id=category_id,
                    unit_id=unit_id,
                    cost_price=cost_val,
                    selling_price=sell_val,
                    min_stock=stock_val,
                    supplier_id=supplier_id,
                    is_active=status_str == "ACTIVE",
                    created_by=current_user.id,
                )
                session.add(new_product)
                insert_count += 1
                success_count += 1

        except Exception as e:
            if skip_errors:
                skip_count += 1
                continue
            errors.append(
                ValidationError(
                    row_number=row_number, field="", error=str(e)
                )
            )
            failed_count += 1

    await session.commit()

    status = ImportStatus.COMPLETED if failed_count == 0 else ImportStatus.COMPLETED
    message = f"匯入完成：成功 {success_count} 筆（新增 {insert_count}，更新 {update_count}）"
    if failed_count > 0:
        message += f"，失敗 {failed_count} 筆"
    if skip_count > 0:
        message += f"，跳過 {skip_count} 筆"

    return ImportResult(
        status=status,
        total_rows=row_number - 1,
        success_count=success_count,
        insert_count=insert_count,
        update_count=update_count,
        failed_count=failed_count,
        skip_count=skip_count,
        errors=errors,
        message=message,
    )


@router.get(
    "/products/export",
    summary="匯出商品資料",
)
async def export_products(
    session: SessionDep,
    current_user: CurrentUser,
    format: ExportFormat = Query(default=ExportFormat.CSV),
    category_id: Optional[int] = Query(default=None, description="分類 ID 過濾"),
    supplier_id: Optional[int] = Query(default=None, description="供應商 ID 過濾"),
    include_inactive: bool = Query(default=False, description="是否包含停用商品"),
):
    """匯出商品資料為 CSV 格式"""
    # 建立查詢
    stmt = select(Product).where(Product.is_deleted == False)

    if not include_inactive:
        stmt = stmt.where(Product.is_active == True)

    if category_id:
        stmt = stmt.where(Product.category_id == category_id)

    if supplier_id:
        stmt = stmt.where(Product.supplier_id == supplier_id)

    stmt = stmt.order_by(Product.code)
    result = await session.execute(stmt)
    products = result.scalars().all()

    # 預先載入關聯資料
    categories = {}
    units = {}
    suppliers = {}

    stmt = select(Category)
    result = await session.execute(stmt)
    for cat in result.scalars().all():
        categories[cat.id] = cat.code

    stmt = select(Unit)
    result = await session.execute(stmt)
    for unit in result.scalars().all():
        units[unit.id] = unit.code

    stmt = select(Supplier)
    result = await session.execute(stmt)
    for sup in result.scalars().all():
        suppliers[sup.id] = sup.code

    # 產生 CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # 寫入標題列
    headers = [
        "code",
        "name",
        "barcode",
        "category_code",
        "unit_code",
        "cost_price",
        "selling_price",
        "min_stock",
        "supplier_code",
        "status",
    ]
    writer.writerow(headers)

    # 寫入資料
    for product in products:
        row = [
            product.code,
            product.name,
            product.barcode or "",
            categories.get(product.category_id, ""),
            units.get(product.unit_id, ""),
            str(product.cost_price),
            str(product.selling_price),
            str(product.min_stock),
            suppliers.get(product.supplier_id, "") if product.supplier_id else "",
            "ACTIVE" if product.is_active else "INACTIVE",
        ]
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=products_export.csv"
        },
    )
