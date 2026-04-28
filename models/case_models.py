# -*- coding: utf-8 -*-
"""
案件相关 Pydantic 模型
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CasePersonResponse(BaseModel):
    id_card_number: str
    person_name: Optional[str] = None
    person_source: str = "unknown"
    role_in_case: Optional[str] = None


class CaseResponse(BaseModel):
    id: int
    case_number: str
    case_name: Optional[str] = None
    case_type: Optional[str] = None
    incident_time: Optional[str] = None
    incident_location: Optional[str] = None
    description: Optional[str] = None
    import_log_id: Optional[int] = None
    created_at: Optional[str] = None


class CaseDetailResponse(CaseResponse):
    persons: List[CasePersonResponse] = []
