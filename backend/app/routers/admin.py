"""管理员路由：物流公司列表、认证审核与账号状态处置。"""

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException

from app.dependencies import AdminDep, CsrfDep, DbConnection
from app.exceptions import CarrierNotFoundError
from app.schemas.carrier import (
    AccountStatusIn,
    CarrierSummaryOut,
    CertificationRecordOut,
    ReviewIn,
)
from app.services import admin as admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/carriers", response_model=list[CarrierSummaryOut])
def list_carriers(
    conn: DbConnection,
    _admin: AdminDep,
    auth_status: str | None = None,
) -> list[CarrierSummaryOut]:
    """列出物流公司及其认证与账号状态。"""
    return admin_service.list_carriers(conn, auth_status)


@router.get(
    "/carriers/{account_id}/certifications",
    response_model=list[CertificationRecordOut],
)
def carrier_certifications(
    account_id: int, conn: DbConnection, _admin: AdminDep
) -> list[CertificationRecordOut]:
    """读取物流公司的全部认证记录（只读历史）。"""
    try:
        return admin_service.carrier_certifications(conn, account_id)
    except CarrierNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="物流公司不存在")


@router.post("/carriers/{account_id}/status", response_model=CarrierSummaryOut)
def set_account_status(
    account_id: int,
    payload: AccountStatusIn,
    conn: DbConnection,
    _admin: AdminDep,
    _csrf: CsrfDep,
) -> CarrierSummaryOut:
    """禁用或恢复物流公司账号，不改写认证与业务历史。"""
    try:
        return admin_service.set_account_status(
            conn, account_id, payload.account_status
        )
    except CarrierNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="物流公司不存在")


@router.post(
    "/carriers/{account_id}/certification/review",
    response_model=CertificationRecordOut,
)
def review_certification(
    account_id: int,
    payload: ReviewIn,
    conn: DbConnection,
    _admin: AdminDep,
    _csrf: CsrfDep,
) -> CertificationRecordOut:
    """审核物流公司认证；驳回原因由入参模型强制必填。"""
    try:
        return admin_service.review_certification(conn, account_id, payload)
    except CarrierNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="物流公司不存在")
