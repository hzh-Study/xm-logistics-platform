"""报销费用路由：司机提交与自查，公司筛选、查看凭证与审核支付。"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import ActiveCarrierDep, BoundDriverDep, CsrfDep, DbConnection
from app.exceptions import (
    ExpenseNotFoundError,
    ExpenseRuleError,
    TaskNotFoundError,
    TaskStateError,
)
from app.schemas.expense import ExpenseIn, ExpenseOut, ExpenseReviewIn
from app.services import expense as expense_service

driver_router = APIRouter(prefix="/api/driver", tags=["expense-driver"])
carrier_router = APIRouter(prefix="/api/carrier", tags=["expense-carrier"])


@driver_router.post(
    "/tasks/{task_id}/expenses",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_expense(
    task_id: int,
    payload: ExpenseIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> ExpenseOut:
    """司机按已完成运输任务提交单笔报销费用及多张凭证。"""
    try:
        return expense_service.submit_expense(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@driver_router.get("/expenses", response_model=list[ExpenseOut])
def list_my_expenses(user: BoundDriverDep, conn: DbConnection) -> list[ExpenseOut]:
    """司机查看自己提交的全部报销费用。"""
    return expense_service.list_driver_expenses(conn, user.id)


@carrier_router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(
    user: ActiveCarrierDep,
    conn: DbConnection,
    driver_account_id: int | None = Query(default=None),
    task_id: int | None = Query(default=None),
    expense_type: Literal["油费", "过路费", "停车费", "维修费", "其他"] | None = Query(default=None),
    submitted_from: str | None = Query(default=None),
    submitted_to: str | None = Query(default=None),
    review_status: Literal["待审核", "审核通过", "审核驳回"] | None = Query(default=None),
    payment_status: Literal["待支付", "已支付"] | None = Query(default=None),
) -> list[ExpenseOut]:
    """物流公司按司机 / 任务 / 类型 / 提交时间 / 审核状态筛选费用。"""
    return expense_service.list_carrier_expenses(
        conn,
        user.id,
        driver_account_id=driver_account_id,
        task_id=task_id,
        expense_type=expense_type,
        submitted_from=submitted_from,
        submitted_to=submitted_to,
        review_status=review_status,
        payment_status=payment_status,
    )


@carrier_router.get("/expenses/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, user: ActiveCarrierDep, conn: DbConnection) -> ExpenseOut:
    """物流公司查看本公司一笔报销费用的明细与凭证。"""
    try:
        return expense_service.get_carrier_expense(conn, user.id, expense_id)
    except ExpenseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报销费用不存在")


@carrier_router.post("/expenses/{expense_id}/review", response_model=ExpenseOut)
def review_expense(
    expense_id: int,
    payload: ExpenseReviewIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> ExpenseOut:
    """物流公司审核单笔费用：通过或驳回（原因必填）。"""
    try:
        return expense_service.review_expense(conn, user.id, expense_id, payload)
    except ExpenseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报销费用不存在")
    except ExpenseRuleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)


@carrier_router.post("/expenses/{expense_id}/mark-paid", response_model=ExpenseOut)
def mark_paid(
    expense_id: int, user: ActiveCarrierDep, conn: DbConnection, _csrf: CsrfDep
) -> ExpenseOut:
    """线下付款后物流公司标记单笔费用已支付。"""
    try:
        return expense_service.mark_paid(conn, user.id, expense_id)
    except ExpenseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报销费用不存在")
    except ExpenseRuleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)


@driver_router.post(
    "/expenses/{expense_id}/resubmit",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
)
def resubmit_expense(
    expense_id: int,
    payload: ExpenseIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> ExpenseOut:
    """司机驳回重提：新笔关联原笔，原笔保留为历史。"""
    try:
        return expense_service.resubmit_expense(conn, user.id, expense_id, payload)
    except (ExpenseNotFoundError, TaskNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报销费用不存在")
    except (ExpenseRuleError, TaskStateError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
