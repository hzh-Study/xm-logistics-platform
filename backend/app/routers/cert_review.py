"""管理员认证审核路由。"""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import AdminDep, CsrfDep, DbConnection
from app.exceptions import CertificationNotFoundError, CertificationStateError
from app.schemas.shipper import AdminCertOut, ReviewIn
from app.services import shipper as shipper_service

router = APIRouter(prefix="/api/admin", tags=["admin-cert-review"])


@router.get("/shipper-certifications", response_model=list[AdminCertOut])
def list_shipper_certifications(
    _admin: AdminDep,
    conn: DbConnection,
) -> list[AdminCertOut]:
    """管理员列出全部货主认证记录。"""
    return shipper_service.list_admin_certifications(conn)


@router.post(
    "/shipper-certifications/{certification_id}/review",
    response_model=AdminCertOut,
)
def review_certification(
    certification_id: int,
    payload: ReviewIn,
    admin: AdminDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> AdminCertOut:
    """管理员审核通过或驳回货主认证。"""
    try:
        return shipper_service.review_certification(
            conn,
            certification_id,
            payload.decision,
            payload.rejection_reason or "",
            admin.id,
        )
    except CertificationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="认证记录不存在")
    except CertificationStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
