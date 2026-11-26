# 连接、事务与并发

适用范围：拿连接、开事务、设 pragma、备份。目标：无半成品写入、无锁冲突。

## 规则

- MUST 每请求一个连接，MUST NOT 跨请求共享；连接工厂须设 `check_same_thread=False` 以允许同一请求内跨线程。理由：sqlite3 默认跨线程拒绝，而 FastAPI 同步依赖的 yield/close 必跨线程；跨请求共享仍会触发线程错误。
- MUST 用 Python 3.12 的 `autocommit=False`（官方推荐），事务显式管理，MUST NOT 依赖隐式 DML 事务。理由：隐式事务行为易变且反直觉。
- MUST 多语句写以 `BEGIN IMMEDIATE` 开始，成功 commit、异常 rollback。理由：IMMEDIATE 先拿写锁避免升级锁失败导致的 `SQLITE_BUSY`。
- MUST 每个新连接设 `foreign_keys=ON`、`busy_timeout=5000`、`synchronous=FULL`；`foreign_keys` 必须在事务前设（事务内设置无效）。理由：默认关 FK、无等待、掉电丢数据都不安全。
- MUST 初始化时一次性设 `journal_mode=WAL`（持久化设置）。理由：读写互不阻塞；`-wal` / `-shm` 文件须与库一同保留。
- MUST 完整性检查用 `PRAGMA foreign_key_check`（`integrity_check` 不查 FK）。理由：真正发现外键违规。
- MUST 在线备份用 `Connection.backup()`，MUST NOT 直接 `cp` 活跃库文件。理由：保证一致性快照。

## Checklist

- [ ] 每请求连接，不跨请求共享；连接已设 `check_same_thread=False`
- [ ] `autocommit=False`，`BEGIN IMMEDIATE`，commit / rollback
- [ ] 连接级 `foreign_keys=ON` / `busy_timeout=5000` / `synchronous=FULL`
- [ ] 初始化 WAL，FK 检查用 `foreign_key_check`，备份用 `backup()`
