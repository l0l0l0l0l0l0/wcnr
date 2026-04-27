# -*- coding: utf-8 -*-
"""
通用 Pydantic 响应模型
"""

from pydantic import BaseModel
from typing import TypeVar, Generic, Optional, List

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None


class PaginatedData(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int
