# -*- coding: utf-8 -*-
"""
用户相关 Pydantic 模型
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    real_name: Optional[str] = None
    role: str = Field(default="operator", pattern="^(admin|operator)$")
    police_station: Optional[str] = None


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(admin|operator)$")
    police_station: Optional[str] = None
    is_active: Optional[int] = Field(default=None, ge=0, le=1)


class UserSelfUpdate(BaseModel):
    real_name: Optional[str] = None
    old_password: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    real_name: Optional[str] = None
    role: str
    police_station: Optional[str] = None
    is_active: int
    created_at: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
