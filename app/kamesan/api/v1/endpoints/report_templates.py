"""
報表範本 API 端點

提供報表範本的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import func, or_, select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.report_template import ReportTemplate, ReportType
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.report_template import (
    ReportTemplateCreate,
    ReportTemplateResponse,
    ReportTemplateSummary,
    ReportTemplateUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[ReportTemplateSummary],
    summary="取得報表範本列表",
)
async def get_report_templates(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    report_type: Optional[ReportType] = Query(default=None, description="報表類型"),
    is_active: Optional[bool] = Query(default=True, description="是否啟用"),
    search: Optional[str] = Query(default=None, description="搜尋（代碼、名稱）"),
):
    """
    取得報表範本列表

    使用者可以看到：
    1. 系統內建範本
    2. 公開範本
    3. 自己建立的範本
    """
    statement = select(ReportTemplate).where(
        ReportTemplate.is_deleted == False,
        or_(
            ReportTemplate.is_system == True,
            ReportTemplate.is_public == True,
            ReportTemplate.owner_id == current_user.id,
        ),
    )

    # 篩選條件
    if report_type:
        statement = statement.where(ReportTemplate.report_type == report_type)
    if is_active is not None:
        statement = statement.where(ReportTemplate.is_active == is_active)
    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            or_(
                ReportTemplate.code.ilike(search_pattern),
                ReportTemplate.name.ilike(search_pattern),
            )
        )

    # 計算總數
    count_statement = select(func.count()).select_from(statement.subquery())
    count_result = await session.execute(count_statement)
    total = count_result.scalar() or 0

    # 分頁和排序
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(
        ReportTemplate.is_system.desc(),  # 系統範本優先
        ReportTemplate.name,
    )

    result = await session.execute(statement)
    templates = result.scalars().all()

    return PaginatedResponse.create(
        items=templates, total=total, page=page, page_size=page_size
    )


@router.post(
    "",
    response_model=ReportTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立報表範本",
)
async def create_report_template(
    template_data: ReportTemplateCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    建立自訂報表範本
    """
    # 檢查代碼是否已存在
    statement = select(ReportTemplate).where(
        ReportTemplate.code == template_data.code,
        ReportTemplate.is_deleted == False,
    )
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="報表代碼已存在")

    # 轉換設定為 dict
    fields_config = None
    if template_data.fields_config:
        fields_config = [f.model_dump() for f in template_data.fields_config]

    filters_config = None
    if template_data.filters_config:
        filters_config = [f.model_dump() for f in template_data.filters_config]

    sort_config = None
    if template_data.sort_config:
        sort_config = [s.model_dump() for s in template_data.sort_config]

    template = ReportTemplate(
        code=template_data.code,
        name=template_data.name,
        description=template_data.description,
        report_type=template_data.report_type,
        fields_config=fields_config,
        filters_config=filters_config,
        sort_config=sort_config,
        format_config=template_data.format_config,
        is_public=template_data.is_public,
        is_active=template_data.is_active,
        owner_id=current_user.id,
        is_system=False,  # 使用者建立的都不是系統範本
        created_by=current_user.id,
    )

    session.add(template)
    await session.commit()
    await session.refresh(template)

    return template


@router.get(
    "/types",
    response_model=list[dict],
    summary="取得報表類型清單",
)
async def get_report_types(
    current_user: CurrentUser,
):
    """
    取得所有可用的報表類型
    """
    types = [
        {"code": t.value, "name": t.name}
        for t in ReportType
    ]
    return types


@router.get(
    "/{template_id}",
    response_model=ReportTemplateResponse,
    summary="取得單一報表範本",
)
async def get_report_template(
    template_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    依 ID 取得報表範本詳情
    """
    template = await session.get(ReportTemplate, template_id)
    if not template or template.is_deleted:
        raise HTTPException(status_code=404, detail="報表範本不存在")

    # 檢查權限
    if not (
        template.is_system
        or template.is_public
        or template.owner_id == current_user.id
        or current_user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="無權限存取此範本")

    return template


@router.put(
    "/{template_id}",
    response_model=ReportTemplateResponse,
    summary="更新報表範本",
)
async def update_report_template(
    template_id: int,
    template_data: ReportTemplateUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    更新報表範本

    只有範本擁有者或管理員可以更新。
    系統內建範本不可修改。
    """
    template = await session.get(ReportTemplate, template_id)
    if not template or template.is_deleted:
        raise HTTPException(status_code=404, detail="報表範本不存在")

    # 檢查權限
    if template.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="無權限修改此範本")

    if template.is_system:
        raise HTTPException(status_code=400, detail="系統內建範本不可修改")

    # 更新欄位
    update_data = template_data.model_dump(exclude_unset=True)

    # 轉換設定為 dict
    if "fields_config" in update_data and update_data["fields_config"]:
        update_data["fields_config"] = [
            f.model_dump() if hasattr(f, "model_dump") else f
            for f in update_data["fields_config"]
        ]

    if "filters_config" in update_data and update_data["filters_config"]:
        update_data["filters_config"] = [
            f.model_dump() if hasattr(f, "model_dump") else f
            for f in update_data["filters_config"]
        ]

    if "sort_config" in update_data and update_data["sort_config"]:
        update_data["sort_config"] = [
            s.model_dump() if hasattr(s, "model_dump") else s
            for s in update_data["sort_config"]
        ]

    for field, value in update_data.items():
        setattr(template, field, value)

    template.updated_by = current_user.id

    session.add(template)
    await session.commit()
    await session.refresh(template)

    return template


@router.delete(
    "/{template_id}",
    response_model=ReportTemplateResponse,
    summary="刪除報表範本",
)
async def delete_report_template(
    template_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    刪除報表範本（軟刪除）

    只有範本擁有者或管理員可以刪除。
    系統內建範本不可刪除。
    """
    template = await session.get(ReportTemplate, template_id)
    if not template or template.is_deleted:
        raise HTTPException(status_code=404, detail="報表範本不存在")

    # 檢查權限
    if template.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="無權限刪除此範本")

    if template.is_system:
        raise HTTPException(status_code=400, detail="系統內建範本不可刪除")

    # 軟刪除
    template.soft_delete()
    template.updated_by = current_user.id

    session.add(template)
    await session.commit()
    await session.refresh(template)

    return template


@router.post(
    "/{template_id}/copy",
    response_model=ReportTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="複製報表範本",
)
async def copy_report_template(
    template_id: int,
    new_code: str = Query(description="新範本代碼"),
    new_name: str = Query(description="新範本名稱"),
    session: SessionDep = None,
    current_user: CurrentUser = None,
):
    """
    複製報表範本

    可以複製系統範本或其他範本作為自己的自訂範本。
    """
    # 取得原始範本
    original = await session.get(ReportTemplate, template_id)
    if not original or original.is_deleted:
        raise HTTPException(status_code=404, detail="報表範本不存在")

    # 檢查新代碼是否已存在
    statement = select(ReportTemplate).where(
        ReportTemplate.code == new_code,
        ReportTemplate.is_deleted == False,
    )
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="報表代碼已存在")

    # 建立複製
    new_template = ReportTemplate(
        code=new_code,
        name=new_name,
        description=original.description,
        report_type=original.report_type,
        fields_config=original.fields_config,
        filters_config=original.filters_config,
        sort_config=original.sort_config,
        format_config=original.format_config,
        is_public=False,
        is_active=True,
        owner_id=current_user.id,
        is_system=False,
        created_by=current_user.id,
    )

    session.add(new_template)
    await session.commit()
    await session.refresh(new_template)

    return new_template
