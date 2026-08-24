from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from core.api.v1.channels import list_phone_numbers_for_channel
from core.database.session import get_db
from core.middleware.auth import (JWTClaims, require_admin_or_owner,
                                  require_org_member)
from core.services.sip.registry import supported_carriers
from core.services.sip.trunk_service import SipTrunkService
from core.utils.auth_helpers import require_org_id

router = APIRouter()


def _svc(claims: JWTClaims, db: Session) -> SipTrunkService:
    return SipTrunkService(db, org_id=require_org_id(claims.org_id), user_id=claims.user_id)


@router.get("/carriers")
def list_carriers(claims: JWTClaims = Depends(require_org_member)) -> List[str]:
    return supported_carriers()


@router.post("/list")
def list_sip_trunks(
    body: Dict[str, Any] = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).list_trunks()


@router.get("/get")
def get_sip_trunk(
    trunk_id: str = Query(...),
    include_auth: bool = Query(False),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).get_trunk(trunk_id, include_auth=include_auth)


@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_sip_trunk(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).create_trunk(data)


@router.put("/update")
def update_sip_trunk(
    trunk_id: str = Query(...),
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).update_trunk(trunk_id, data)


@router.delete("/delete")
def delete_sip_trunk(
    trunk_id: str = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).delete_trunk(trunk_id)


@router.post("/provision")
def provision_sip_trunk(
    trunk_id: str = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).provision_trunk(trunk_id)


@router.get("/phone_numbers")
def list_trunk_phone_numbers(
    trunk_id: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = require_org_id(claims.org_id)
    trunk = _svc(claims, db).get_trunk_record(trunk_id)
    return list_phone_numbers_for_channel(db, org_id, str(trunk.channel_id))


@router.get("/carrier_phone_numbers")
def list_carrier_phone_numbers(
    trunk_id: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).list_carrier_numbers(trunk_id)


@router.post("/attach_number")
def attach_number(
    trunk_id: str = Query(...),
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).attach_number(
        trunk_id, data.get("number") or "", label=data.get("label")
    )


@router.delete("/detach_number")
def detach_number(
    trunk_id: str = Query(...),
    number: str = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).detach_number(trunk_id, number)
