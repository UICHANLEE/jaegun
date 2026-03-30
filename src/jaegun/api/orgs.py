"""공동체(총회·노회·교회) 등록·멤버·삭제 신청."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.auth_jwt import get_current_user, user_by_phone
from jaegun.db import get_session
from jaegun.models import Organization, OrgDeletionRequest, OrgMembership, User

router = APIRouter(prefix="/orgs", tags=["organizations"])

ORG_KINDS = frozenset({"general_assembly", "presbytery", "church"})


def _get_active_org(session: Session, org_id: UUID) -> Organization | None:
    o = session.get(Organization, org_id)
    if o is None or o.status != "active":
        return None
    return o


def _require_org_admin(session: Session, user_id: UUID, org_id: UUID) -> Organization:
    org = _get_active_org(session, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="공동체를 찾을 수 없습니다.")
    m = session.exec(
        select(OrgMembership).where(
            OrgMembership.organization_id == org_id,
            OrgMembership.user_id == user_id,
            OrgMembership.is_org_admin == True,  # noqa: E712
        )
    ).first()
    if m is None:
        raise HTTPException(status_code=403, detail="공동체 관리자만 할 수 있습니다.")
    return org


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    kind: str = Field(..., min_length=1, max_length=30)
    parent_id: UUID | None = None


class OrganizationOut(BaseModel):
    id: UUID
    name: str
    kind: str
    parent_id: UUID | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberCreate(BaseModel):
    phone: str | None = Field(default=None, max_length=20)
    user_id: UUID | None = None
    role_key: str = Field(default="member", max_length=40)
    role_label: str = Field(default="", max_length=100)
    is_org_admin: bool = False


class MemberOut(BaseModel):
    user_id: UUID
    display_name: str
    phone: str | None
    role_key: str
    role_label: str
    is_org_admin: bool


class DeletionRequestBody(BaseModel):
    reason: str = Field(default="", max_length=2000)


@router.get("", response_model=list[OrganizationOut])
def list_organizations(
    session: Session = Depends(get_session),
    kind: str | None = Query(None, description="general_assembly | presbytery | church"),
) -> list[Organization]:
    stmt = select(Organization).where(Organization.status == "active")
    if kind:
        stmt = stmt.where(Organization.kind == kind)
    stmt = stmt.order_by(Organization.kind.asc(), Organization.name.asc())
    return list(session.exec(stmt).all())


@router.post("", response_model=OrganizationOut, status_code=201)
def create_organization(
    body: OrganizationCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Organization:
    if body.kind not in ORG_KINDS:
        raise HTTPException(
            status_code=422,
            detail=f"kind는 {', '.join(sorted(ORG_KINDS))} 중 하나여야 합니다.",
        )
    parent: Organization | None = None
    if body.parent_id is not None:
        parent = _get_active_org(session, body.parent_id)
        if parent is None:
            raise HTTPException(status_code=404, detail="상위 공동체를 찾을 수 없습니다.")
    row = Organization(
        name=body.name.strip(),
        kind=body.kind,
        parent_id=body.parent_id,
        created_by_user_id=user.id,
        status="active",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    session.add(
        OrgMembership(
            user_id=user.id,
            organization_id=row.id,
            role_key="chair",
            role_label="등록자(관리자)",
            is_org_admin=True,
        )
    )
    session.commit()
    session.refresh(row)
    return row


@router.get("/{org_id}", response_model=OrganizationOut)
def get_organization(org_id: UUID, session: Session = Depends(get_session)) -> Organization:
    org = _get_active_org(session, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="공동체를 찾을 수 없습니다.")
    return org


@router.get("/{org_id}/members", response_model=list[MemberOut])
def list_members(org_id: UUID, session: Session = Depends(get_session)) -> list[MemberOut]:
    if _get_active_org(session, org_id) is None:
        raise HTTPException(status_code=404, detail="공동체를 찾을 수 없습니다.")
    rows = session.exec(
        select(OrgMembership).where(OrgMembership.organization_id == org_id)
    ).all()
    out: list[MemberOut] = []
    for m in rows:
        u = session.get(User, m.user_id)
        if u is None:
            continue
        out.append(
            MemberOut(
                user_id=u.id,
                display_name=u.display_name,
                phone=u.phone,
                role_key=m.role_key,
                role_label=m.role_label or "",
                is_org_admin=m.is_org_admin,
            )
        )
    out.sort(key=lambda x: (not x.is_org_admin, x.role_key, x.display_name))
    return out


@router.post("/{org_id}/members", response_model=MemberOut, status_code=201)
def add_member(
    org_id: UUID,
    body: MemberCreate,
    session: Session = Depends(get_session),
    admin_user: User = Depends(get_current_user),
) -> MemberOut:
    _require_org_admin(session, admin_user.id, org_id)
    target: User | None = None
    if body.user_id is not None:
        target = session.get(User, body.user_id)
    elif body.phone:
        target = user_by_phone(session, body.phone)
    else:
        raise HTTPException(status_code=422, detail="user_id 또는 phone이 필요합니다.")
    if target is None:
        raise HTTPException(status_code=404, detail="해당 회원을 찾을 수 없습니다.")
    dup = session.exec(
        select(OrgMembership).where(
            OrgMembership.organization_id == org_id,
            OrgMembership.user_id == target.id,
        )
    ).first()
    if dup:
        raise HTTPException(status_code=409, detail="이미 이 공동체에 등록된 회원입니다.")
    m = OrgMembership(
        user_id=target.id,
        organization_id=org_id,
        role_key=(body.role_key or "member").strip() or "member",
        role_label=(body.role_label or "").strip(),
        is_org_admin=body.is_org_admin,
    )
    session.add(m)
    session.commit()
    return MemberOut(
        user_id=target.id,
        display_name=target.display_name,
        phone=target.phone,
        role_key=m.role_key,
        role_label=m.role_label,
        is_org_admin=m.is_org_admin,
    )


class MemberPatch(BaseModel):
    role_key: str | None = Field(default=None, max_length=40)
    role_label: str | None = Field(default=None, max_length=100)
    is_org_admin: bool | None = None


@router.patch("/{org_id}/members/{user_id}", response_model=MemberOut)
def patch_member(
    org_id: UUID,
    user_id: UUID,
    body: MemberPatch,
    session: Session = Depends(get_session),
    admin_user: User = Depends(get_current_user),
) -> MemberOut:
    _require_org_admin(session, admin_user.id, org_id)
    m = session.exec(
        select(OrgMembership).where(
            OrgMembership.organization_id == org_id,
            OrgMembership.user_id == user_id,
        )
    ).first()
    if m is None:
        raise HTTPException(status_code=404, detail="멤버십을 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(m, k, v)
    session.add(m)
    session.commit()
    session.refresh(m)
    u = session.get(User, user_id)
    assert u is not None
    return MemberOut(
        user_id=u.id,
        display_name=u.display_name,
        phone=u.phone,
        role_key=m.role_key,
        role_label=m.role_label or "",
        is_org_admin=m.is_org_admin,
    )


@router.delete("/{org_id}/members/{user_id}", status_code=204)
def remove_member(
    org_id: UUID,
    user_id: UUID,
    session: Session = Depends(get_session),
    admin_user: User = Depends(get_current_user),
) -> None:
    _require_org_admin(session, admin_user.id, org_id)
    m = session.exec(
        select(OrgMembership).where(
            OrgMembership.organization_id == org_id,
            OrgMembership.user_id == user_id,
        )
    ).first()
    if m is None:
        raise HTTPException(status_code=404, detail="멤버십을 찾을 수 없습니다.")
    session.delete(m)
    session.commit()


@router.post("/{org_id}/deletion-request", status_code=201)
def request_org_deletion(
    org_id: UUID,
    body: DeletionRequestBody,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    _require_org_admin(session, user.id, org_id)
    pending = session.exec(
        select(OrgDeletionRequest).where(
            OrgDeletionRequest.organization_id == org_id,
            OrgDeletionRequest.status == "pending",
        )
    ).first()
    if pending:
        raise HTTPException(status_code=409, detail="이미 삭제 신청이 접수되어 있습니다.")
    row = OrgDeletionRequest(
        organization_id=org_id,
        requested_by_user_id=user.id,
        reason=(body.reason or "").strip(),
        status="pending",
    )
    session.add(row)
    session.commit()
    return {"detail": "전체 관리자 승인 후 삭제됩니다."}
