# 统一 Account + 角色 profile，登录态用 DB-backed session token

四类用户共用一张 Account 表（role 区分）加各角色 profile 表；登录态是存进 SQLite 的 opaque session token，禁用或退出时删除记录即失效。选它而不是 JWT，是因为「禁用 / 退出必须立即生效」且不能引入 Redis 等外部服务；统一账号，是因为登录、状态与退出逻辑对四类用户完全一致。
