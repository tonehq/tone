from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import io

from core.database.session import get_db
from core.middleware.auth import require_org_member, JWTClaims
from core.models.call_log import CallLog
from core.models.upload import Upload
from core.services.r2_storage_service import R2StorageService

router = APIRouter()


@router.get("/get_all_call_logs", response_model=List[Dict[str, Any]])
def get_all_call_logs(
    agent_id: Optional[int] = Query(None, description="Filter by agent ID"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    query = db.query(CallLog)
    if agent_id:
        query = query.filter(CallLog.agent_id == agent_id)
    call_logs = query.order_by(CallLog.id.desc()).all()
    return [
        {
            "id": cl.id,
            "uuid": str(cl.uuid),
            "agent_id": cl.agent_id,
            "provider_call_id": cl.provider_call_id,
            "transport_type": cl.transport_type,
            "from_number": cl.from_number,
            "to_number": cl.to_number,
            "status": cl.status,
            "started_at": cl.started_at,
            "ended_at": cl.ended_at,
            "duration_seconds": cl.duration_seconds,
            "upload_id": cl.upload_id,
            "transcript": cl.transcript,
        }
        for cl in call_logs
    ]


@router.get("/get_call_log_audio_url")
def get_call_log_audio_url(
    call_log_id: int = Query(..., description="The call log ID"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Return a presigned URL to play the call recording."""
    call_log = db.query(CallLog).filter(CallLog.id == call_log_id).first()
    if not call_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call log not found")
    if not call_log.upload_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recording for this call")

    upload = db.query(Upload).filter(Upload.id == call_log.upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload record not found")

    r2 = R2StorageService()
    url = r2.generate_presigned_url(upload.r2_object_key)
    return {"url": url, "file_name": upload.file_name, "content_type": upload.content_type}


@router.get("/download_call_log_audio")
def download_call_log_audio(
    call_log_id: int = Query(..., description="The call log ID"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Download the call recording as a file."""
    call_log = db.query(CallLog).filter(CallLog.id == call_log_id).first()
    if not call_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call log not found")
    if not call_log.upload_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recording for this call")

    upload = db.query(Upload).filter(Upload.id == call_log.upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload record not found")

    r2 = R2StorageService()
    audio_bytes = r2.download_file(upload.r2_object_key)

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type=upload.content_type or "audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{upload.file_name}"'},
    )
