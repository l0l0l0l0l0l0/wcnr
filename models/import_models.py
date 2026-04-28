# -*- coding: utf-8 -*-
"""
数据导入相关 Pydantic 模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ImportConfirmRequest(BaseModel):
    import_log_id: int
    skip_invalid: bool = True
    skip_duplicate: bool = False


class PromoteRequest(BaseModel):
    id_card_numbers: List[str] = Field(..., min_length=1)
    control_category: str = "重点管控"


class UploadPreviewResponse(BaseModel):
    import_log_id: int
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    preview: List[dict]
    validation_errors: List[dict]


class ImportLogResponse(BaseModel):
    id: int
    source_system: str
    file_name: str
    record_count: int
    success_count: int
    fail_count: int
    duplicate_count: int
    status: str
    error_message: Optional[str] = None
    operator_name: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
