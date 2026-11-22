import { request } from '@/api/request'
import type { Expense, ExpenseType } from '@/types/expense'

/** 司机提交单笔报销费用的入参。 */
export interface ExpensePayload {
  expense_type: ExpenseType
  amount_yuan: string
  incurred_at: string
  description: string
  vouchers: string[]
}

/** 司机按已完成运输任务提交单笔报销费用。 */
export function submitExpense(taskId: number, payload: ExpensePayload): Promise<Expense> {
  return request.post<Expense>(`/api/driver/tasks/${taskId}/expenses`, payload)
}

/** 驳回后重新提交，新笔关联原笔且原笔保留为历史。 */
export function resubmitExpense(expenseId: number, payload: ExpensePayload): Promise<Expense> {
  return request.post<Expense>(`/api/driver/expenses/${expenseId}/resubmit`, payload)
}

/** 司机查看自己提交的全部报销费用。 */
export function listMyExpenses(): Promise<Expense[]> {
  return request.get<Expense[]>('/api/driver/expenses')
}
