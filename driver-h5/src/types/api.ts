/** 后端统一错误信封。 */
export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
    details: unknown
  }
}
