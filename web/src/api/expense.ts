import { request } from '@/api/request'
import type {
  Expense,
  ExpensePaymentStatus,
  ExpenseReviewStatus,
  ExpenseType,
} from '@/types/expense'

/** 物流公司筛选报销费用的条件。 */
export interface ExpenseFilters {
  driver_account_id?: number
  task_id?: number
  expense_type?: ExpenseType
  submitted_from?: string
  submitted_to?: string
  review_status?: ExpenseReviewStatus
  payment_status?: ExpensePaymentStatus
}

/** 按司机 / 任务 / 类型 / 提交时间 / 审核状态筛选本公司费用。 */
export function listExpenses(filters: ExpenseFilters = {}): Promise<Expense[]> {
  const query = new URLSearchParams()
  if (filters.driver_account_id !== undefined) {
    query.set('driver_account_id', String(filters.driver_account_id))
  }
  if (filters.task_id !== undefined) query.set('task_id', String(filters.task_id))
  if (filters.expense_type) query.set('expense_type', filters.expense_type)
  if (filters.submitted_from) query.set('submitted_from', filters.submitted_from)
  if (filters.submitted_to) query.set('submitted_to', filters.submitted_to)
  if (filters.review_status) query.set('review_status', filters.review_status)
  if (filters.payment_status) query.set('payment_status', filters.payment_status)
  const suffix = query.toString()
  return request.get<Expense[]>(`/api/carrier/expenses${suffix ? `?${suffix}` : ''}`)
}

/** 读取单笔报销费用的明细与凭证。 */
export function getExpense(expenseId: number): Promise<Expense> {
  return request.get<Expense>(`/api/carrier/expenses/${expenseId}`)
}

/** 物流公司审核单笔费用，驳回原因必填。 */
export function reviewExpense(
  expenseId: number,
  decision: ExpenseReviewStatus,
  reason: string,
): Promise<Expense> {
  return request.post<Expense>(`/api/carrier/expenses/${expenseId}/review`, { decision, reason })
}

/** 线下付款后标记单笔费用已支付。 */
export function markExpensePaid(expenseId: number): Promise<Expense> {
  return request.post<Expense>(`/api/carrier/expenses/${expenseId}/mark-paid`, {})
}
