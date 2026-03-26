"""연간·월간 계획 — 공개 조회만 (`/api/plans`). 수정은 `/admin/plans`."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.db import get_session
from jaegun.models import AnnualPlan, MonthlyPlan

router = APIRouter(prefix="/plans", tags=["plans"])


class AnnualCreate(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    title: str = Field(..., min_length=1, max_length=200)
    body: str = ""


class AnnualPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = None


class MonthlyCreate(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    title: str = Field(..., min_length=1, max_length=200)
    body: str = ""


class MonthlyPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = None


# --- 연간 (조회만) ---


@router.get("/annual", response_model=list[AnnualPlan])
def list_annual(session: Session = Depends(get_session)) -> list[AnnualPlan]:
    rows = session.exec(select(AnnualPlan).order_by(AnnualPlan.year.desc())).all()
    return list(rows)


@router.get("/annual/{year}", response_model=AnnualPlan)
def get_annual(year: int, session: Session = Depends(get_session)) -> AnnualPlan:
    row = session.get(AnnualPlan, year)
    if row is None:
        raise HTTPException(status_code=404, detail="해당 연도 연간 계획이 없습니다.")
    return row


# --- 월간 (조회만) ---


@router.get("/monthly", response_model=list[MonthlyPlan])
def list_monthly(
    *,
    session: Session = Depends(get_session),
    year: int = Query(..., ge=2000, le=2100, description="조회할 연도"),
) -> list[MonthlyPlan]:
    stmt = (
        select(MonthlyPlan)
        .where(MonthlyPlan.year == year)
        .order_by(MonthlyPlan.month.asc())
    )
    return list(session.exec(stmt).all())


@router.get("/monthly/{year}/{month}", response_model=MonthlyPlan)
def get_monthly(
    year: int,
    month: int,
    session: Session = Depends(get_session),
) -> MonthlyPlan:
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="month는 1~12입니다.")
    row = session.exec(
        select(MonthlyPlan).where(MonthlyPlan.year == year, MonthlyPlan.month == month)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="해당 월 계획이 없습니다.")
    return row
