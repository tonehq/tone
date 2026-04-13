from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.call_log_service import CallLogService
from core.utils.storage import generate_presigned_url, get_r2_object

router = APIRouter()


@router.get("/filter-values")
def get_filter_values(
    column_name: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return CallLogService(db).get_filter_values(column_name=column_name)


@router.post("/list")
def get_call_logs(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return CallLogService(db).get_call_logs(
        page_no=data.get("page_no", 1),
        page_size=data.get("page_size", 10),
        start_date_time=data.get("start_date_time"),
        end_date_time=data.get("end_date_time"),
        filters=data.get("filters"),
        sort_by=data.get("sort_by"),
        sort_order=data.get("sort_order", "desc"),
    )


@router.get("/{call_id}")
def get_call_log_by_id(
    call_id: int,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    result = CallLogService(db).get_call_log_by_id(call_log_id=call_id)
    if not result:
        raise HTTPException(status_code=404, detail="Call log not found")
    return result


@router.get("/{call_id}/audio-url")
def get_audio_url(
    call_id: int,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    result = CallLogService(db).get_call_log_by_id(call_log_id=call_id)
    if not result:
        raise HTTPException(status_code=404, detail="Call log not found")

    audio_path = result.get("audio_file_path")
    if not audio_path:
        raise HTTPException(status_code=404, detail="No audio recording for this call")

    url = generate_presigned_url(audio_path)
    return {"url": url}


@router.get("/{call_id}/audio")
def download_audio(
    call_id: int,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
    range: Optional[str] = Header(None),
):
    """Stream the audio file from R2 for playback or download.

    Supports HTTP Range requests so browsers can seek within the audio.
    """
    result = CallLogService(db).get_call_log_by_id(call_log_id=call_id)
    if not result:
        raise HTTPException(status_code=404, detail="Call log not found")

    audio_path = result.get("audio_file_path")
    if not audio_path:
        raise HTTPException(status_code=404, detail="No audio recording for this call")

    try:
        r2_response = get_r2_object(audio_path, range_header=range)
    except Exception:
        raise HTTPException(status_code=404, detail="Audio file not found in storage")

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(r2_response["ContentLength"]),
    }
    if "ContentRange" in r2_response:
        headers["Content-Range"] = r2_response["ContentRange"]

    status_code = r2_response["StatusCode"]

    return StreamingResponse(
        r2_response["Body"].iter_chunks(chunk_size=1024 * 64),
        status_code=status_code,
        media_type=r2_response["ContentType"],
        headers=headers,
    )
