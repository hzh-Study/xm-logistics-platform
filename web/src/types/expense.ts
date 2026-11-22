/** 报销费用类型。 */
export type ExpenseType = '油费' | '过路费' | '停车费' | '维修费' | '其他'

/** 报销费用审核状态。 */
export type ExpenseReviewStatus = '待审核' | '审核通过' | '审核驳回'

/** 报销费用支付状态，与审核状态独立。 */
export type ExpensePaymentStatus = '待支付' | '已支付'

/** 一笔报销费用：公司可查看凭证、审核并在收款后标记已支付。 */
export interface Expense {
  id: number
  expense_no: string
  task_id: number
  task_no: string
  order_id: number
  driver_account_id: number
  driver_name: string
  carrier_account_id: number
  expense_type: ExpenseType
  amount_yuan: string
  incurred_at: string
  description: string
  vouchers: string[]
  review_status: ExpenseReviewStatus
  review_reason: string
  payment_status: ExpensePaymentStatus
  reviewed_at: string | null
  reviewed_by_account_id: number | null
  paid_at: string | null
  paid_by_account_id: number | null
  replaced_by: number | null
  superseded_by: number | null
  created_at: string
}
