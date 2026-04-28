# -*- coding: utf-8 -*-
"""
人口系统相关 Pydantic 模型
"""

from pydantic import BaseModel
from typing import Optional


class PopulationResponse(BaseModel):
    id: int
    id_card_number: str
    name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    import_log_id: Optional[int] = None
    promoted: int = 0
    promoted_at: Optional[str] = None
    created_at: Optional[str] = None
