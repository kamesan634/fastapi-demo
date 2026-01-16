"""
共用 Schema 模型

定義通用的請求和回應模型。

模型：
- PaginatedResponse: 分頁回應
- MessageResponse: 訊息回應
"""

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# 泛型類型變數
T = TypeVar("T")


class MessageResponse(BaseModel):
    """
    訊息回應模型

    用於回傳簡單的成功/失敗訊息。

    屬性：
    - message: 回應訊息
    - success: 是否成功
    """

    message: str = Field(description="回應訊息")
    success: bool = Field(default=True, description="是否成功")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分頁回應模型

    用於回傳分頁資料。

    屬性：
    - items: 資料列表
    - total: 總筆數
    - page: 當前頁碼
    - page_size: 每頁筆數
    - pages: 總頁數
    """

    items: List[T] = Field(description="資料列表")
    total: int = Field(description="總筆數")
    page: int = Field(description="當前頁碼")
    page_size: int = Field(description="每頁筆數")
    pages: int = Field(description="總頁數")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """建立分頁回應"""
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )


class QueryParams(BaseModel):
    """
    查詢參數基礎模型

    屬性：
    - page: 頁碼（從 1 開始）
    - page_size: 每頁筆數
    - search: 搜尋關鍵字
    - sort_by: 排序欄位
    - sort_order: 排序方向（asc/desc）
    """

    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    search: Optional[str] = Field(default=None, description="搜尋關鍵字")
    sort_by: Optional[str] = Field(default=None, description="排序欄位")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="排序方向")

    @property
    def offset(self) -> int:
        """計算偏移量"""
        return (self.page - 1) * self.page_size


class IDResponse(BaseModel):
    """
    ID 回應模型

    用於回傳新建資料的 ID。

    屬性：
    - id: 資料 ID
    """

    id: int = Field(description="資料 ID")
