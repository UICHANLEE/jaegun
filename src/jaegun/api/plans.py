"""연간·월간 계획 CRUD."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.db import get_session
from jaegun.models import AnnualPlan, MonthlyPlan
from jaegun.security import require_admin

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


# --- 연간 ---


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


@router.post(
    "/annual",
    response_model=AnnualPlan,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_annual(body: AnnualCreate, session: Session = Depends(get_session)) -> AnnualPlan:
    if session.get(AnnualPlan, body.year) is not None:
        raise HTTPException(status_code=409, detail="이미 해당 연도 연간 계획이 있습니다.")
    row = AnnualPlan(year=body.year, title=body.title, body=body.body)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch(
    "/annual/{year}",
    response_model=AnnualPlan,
    dependencies=[Depends(require_admin)],
)
def patch_annual(
    year: int,
    body: AnnualPatch,
    session: Session = Depends(get_session),
) -> AnnualPlan:
    row = session.get(AnnualPlan, year)
    if row is None:
        raise HTTPException(status_code=404, detail="해당 연도 연간 계획이 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if not data:
        return row
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/annual/{year}", status_code=204, dependencies=[Depends(require_admin)])
def delete_annual(year: int, session: Session = Depends(get_session)) -> None:
    row = session.get(AnnualPlan, year)
    if row is None:
        raise HTTPException(status_code=404, detail="해당 연도 연간 계획이 없습니다.")
    session.delete(row)
    session.commit()


# --- 월간 ---


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


@router.post(
    "/monthly",
    response_model=MonthlyPlan,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_monthly(body: MonthlyCreate, session: Session = Depends(get_session)) -> MonthlyPlan:
    exists = session.exec(
        select(MonthlyPlan).where(
            MonthlyPlan.year == body.year,
            MonthlyPlan.month == body.month,
        )
    ).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="이미 해당 연·월 계획이 있습니다.")
    row = MonthlyPlan(
        year=body.year,
        month=body.month,
        title=body.title,
        body=body.body,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch(
    "/monthly/{year}/{month}",
    response_model=MonthlyPlan,
    dependencies=[Depends(require_admin)],
)
def patch_monthly(
    year: int,
    month: int,
    body: MonthlyPatch,
    session: Session = Depends(get_session),
) -> MonthlyPlan:
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="month는 1~12입니다.")
    row = session.exec(
        select(MonthlyPlan).where(MonthlyPlan.year == year, MonthlyPlan.month == month)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="해당 월 계획이 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if not data:
        return row
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete(
    "/monthly/{year}/{month}",
    status_code=204,
    dependencies=[Depends(require_admin)],
)
def delete_monthly(
    year: int,
    month: int,
    session: Session = Depends(get_session),
) -> None:
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="month는 1~12입니다.")
    row = session.exec(
        select(MonthlyPlan).where(MonthlyPlan.year == year, MonthlyPlan.month == month)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="해당 월 계획이 없습니다.")
    session.delete(row)
    session.commit()
