## Problem Statement

货主、物流公司、司机、平台管理员之间目前没有一个统一的平台来承接运输业务：货主发布货源后无法让物流公司高效承接并跟踪进度；物流公司缺少管理旗下司机、车辆、派单、运输异常与司机费用报销的手段；司机缺少接收任务、关键节点打卡、签收与费用提交的执行工具；管理员缺少认证审核、违规处理与平台运营能力。四类角色的数据相互关联，但权限必须严格隔离，且已经发生的业务记录不能被事后改写。需要一个覆盖 V1 全流程的实现，让这些角色在同一套数据上协作，并保证业务历史可审计。

## Solution

按已确认的需求文档（V1.2）实现 V1 平台：Vue3+Vite Web 端承载货主、物流公司、管理员三种角色（同一入口按身份展示功能），Vue3 移动 H5 作为司机端（在微信内打开，不引入小程序工具链），FastAPI 后端 + SQLite 存储，凭证存项目本地文件目录、库内只存相对路径，所有脚本为 `.py`、不引入额外服务。术语遵循 `GLOSSARY.md`，边界遵循 `docs/adr/` 0001–0008；业务决策见需求文档第八节与 8.3 设计约定。业务历史只读、追加不可变；管理员不改写业务实体，更正以追加异常处理记录完成。

## User Stories

1. As a 货主, I want to register with my phone, so that I can access the shipper workspace.
2. As a 货主, I want to choose 个人 or 企业 authentication and submit the required identity or enterprise documents, so that my identity can be reviewed.
3. As a 货主, I want to see my current 认证状态 (未提交 / 待审核 / 审核通过 / 审核不通过), so that I know where my review stands.
4. As a 货主 whose authentication was rejected, I want to see the rejection reason and resubmit, so that I can regain the ability to publish.
5. As a 货主 whose 认证状态 is not 审核通过, I want publishing to be blocked with a clear reason, so that I do not waste effort.
6. As a 货主, I want my 账号状态 to be separate from my 认证状态, so that a review stage is never mistaken for account availability.
7. As a 物流公司, I want to register and submit 企业基本信息、营业执照、负责人、联系人及资质资料, so that my enterprise can be reviewed.
8. As a 物流公司, I want to see my 认证状态 and rejection reason, so that I can resubmit when rejected.
9. As a 物流公司 whose authentication is not approved or whose account is disabled, I want 承接 and 派单 to be blocked, so that compliance is preserved.
10. As a 物流公司, I want to create driver accounts with a phone number and a temporary password, so that drivers can join my company.
11. As a 司机, I want to log in on mobile H5 with my phone and temporary password, so that I can access my assigned tasks.
12. As a 司机 on first login, I want to be forced to change my password and complete identity and driving-license details, so that 身份绑定 is complete and my company ownership is confirmed.
13. As a 司机, I want to be blocked when my account is disabled, my 雇佣关系 is 离职, or my company is disabled, so that I cannot perform transport business improperly.
14. As a 司机, I want to be unable to self-register or take public 货源, so that the承运 boundary is unambiguous.
15. As an 管理员, I want to log in with platform-issued credentials, so that I can operate the platform.
16. As any user, I want to log out securely, so that my session no longer grants access.
17. As an 管理员, I want to disable or restore a 货主 / 物流公司 / 司机 account, so that violations are handled without erasing history.
18. As an 管理员, I want to mark an account 已注销 while keeping its records, so that data retention holds.
19. As a 物流公司, I want to set a driver's 接单可用性 to 暂停接单, so that no new tasks are assigned while existing tasks continue.
20. As a 物流公司, I want to record a driver's 雇佣关系 (在职 / 离职) independently of account status, so that the four state dimensions stay orthogonal.
21. As a 物流公司, I want to record a vehicle's 可用性 and 生命周期 as two independent dimensions, so that 维修 / 停用 / 占用 do not conflict.
22. As a 货主, I want a homepage showing my warehouse count, total orders, and counts for 待承接 / 已承接 / 运输中 / 已完成 / 已取消, so that I can see my business at a glance.
23. As a 货主, I want recent orders, recent transport activity and system notices on my homepage, so that I know what needs attention.
24. As a 货主, I want quick links from the homepage into warehouse and order management, so that I can work efficiently.
25. As a 货主, I want to list all my warehouses with name, location, contact, phone, type and status, so that I can manage them.
26. As a 货主, I want to search warehouses by name, so that I can find one quickly.
27. As a 货主, I want to create a warehouse with name, contact, phone, province/city/district, detailed address, type and remarks, so that I can use it as a shipping location.
28. As a 货主, I want to modify my warehouse master data, so that contact details stay current.
29. As a 货主, I want to 停用 a warehouse so it is no longer offered as the default shipping warehouse for new orders, so that stale locations are not reused.
30. As a 货主, I want historical orders to keep their original shipping information after a warehouse is 停用 or deleted, so that history is not rewritten.
31. As a 货主, I want to publish a 运输订单 with cargo name, type, quantity, weight, volume, packaging, photos and remarks, so that carriers can evaluate it.
32. As a 货主, I want special cargo types to require the platform's transport requirements and qualification information, so that compliance is enforced.
33. As a 货主, I want to provide shipping information by selecting an existing warehouse or a temporary address, so that I have flexibility.
34. As a 货主, I want the shipping details frozen as a 发货快照 on the order, so that later warehouse changes do not affect history.
35. As a 货主, I want the receiving details frozen as a 收货快照 on the order, so that the destination is unambiguous.
36. As a 货主, I want to specify transport requirements (vehicle type/length/load, cold chain, rain protection, enclosed body, special loading, other services), so that only capable carriers accept.
37. As a 货主, I want to give a 运费报价 with a fixed, negotiable or other quote method and an "accept bargaining" display flag, so that the quote is visible to the carrier.
38. As a 货主, I want to confirm all order details before publishing, so that mistakes are reduced.
39. As a 货主, I want to filter my orders by order number, status, publish time, shipping place, receiving place and cargo name, so that I can find any order.
40. As a 货主, I want to view full order details (basic info, cargo, shipping, receiving, requirements, quote), so that I know what was agreed.
41. As a 货主, I want to see the accepting 物流公司, current 运输任务, driver and vehicle, so that I know who is executing.
42. As a 货主, I want to see transport status and process records, so that I can follow progress.
43. As a 货主, I want to see shipping and receiving 打卡 records and photos, so that key nodes are verifiable.
44. As a 货主, I want to see the transport completion time, so that I know when delivery happened.
45. As a 货主, I want a read-only 运输进度 that is a projection of 运输订单状态 driven by 运输任务状态, so that scheduling nodes are not confused with order stages.
46. As a 货主, I want to view but never modify driver-submitted transport records, so that evidence remains intact.
47. As a 货主, I want to directly cancel an order that has not been accepted, so that I can withdraw it immediately.
48. As a 货主, I want to request cancellation (reason required) for an accepted or dispatched-but-not-started order, so that the carrier can confirm.
49. As a 货主, I want my cancellation request to put the order into 取消处理中, so that the state is visible.
50. As a 货主, I want the order to become 已取消 when the carrier agrees, so that the outcome is recorded.
51. As a 货主, I want to see the reason and have the order restored to its pre-request state when the carrier rejects my cancellation, so that I understand the decision.
52. As a 货主, I want no cancellation entry once transport has started, with the request routed to 异常处理中 instead, so that in-transit orders are not casually voided.
53. As a 货主, I want completed orders to be non-cancellable, so that history is stable.
54. As a 货主, I want 取消处理中 and 异常处理中 to be mutually exclusive, so that the order has one unambiguous state.
55. As a 货主, I want business notifications for publish success, acceptance, driver accepted, arrival at shipper, transport started, arrival at receiver, completion and exceptions, so that I stay informed.
56. As a 货主, I want an inbox of sent notifications without read receipts, so that the V1 scope is respected.
57. As a 货主, I want to see only my own warehouses and orders, so that permission isolation holds.
58. As a 货主, I want the 运费报价 visible to me but not to the driver, so that the two fund flows stay separate.
59. As a 物流公司, I want a homepage with company info, pending reviews, today's accepted orders, pending dispatch, pending driver confirmation, in-transit, completed, exception, pending expense review, driver count and vehicle count, so that I can run operations.
60. As a 物流公司, I want an order pool listing order number, cargo name/type/weight/volume, shipping and receiving places, expected load/delivery times, vehicle requirements, quote and publish time, so that I can scan opportunities.
61. As a 物流公司, I want to filter the order pool by shipping place, receiving place, cargo type, vehicle type, weight, publish time and freight range, so that I find matching orders.
62. As a 物流公司, I want full 货源 details including cargo, locations, contacts, requirements, photos, quote and remarks, so that I can decide.
63. As a 物流公司, I want to confirm my capability, vehicles, available drivers, timing and acceptance of the quote before accepting, so that I do not overcommit.
64. As a 物流公司, I want a successful acceptance to remove the order from the public pool and assign it to my company, so that ownership is exclusive.
65. As a 物流公司, I want first-come-first-served acceptance with no competing bids, so that the V1 decision is respected.
66. As a 物流公司, I want the same order to be unacceptable by a second company, so that uniqueness holds.
67. As a 物流公司, I want accepted orders to appear in my order management ready for dispatch, so that I can proceed.
68. As a 物流公司, I want to filter my orders by number, status, shipper, shipping place, receiving place and acceptance time, so that I can manage them.
69. As a 物流公司, I want to view full order information and progress, so that I can serve my customers.
70. As a 物流公司, I want a driver list with name, phone, certification status, driving qualification, current status, current vehicle, current task and historical task count, so that I can manage my workforce.
71. As a 物流公司, I want to add a driver with basic, identity and qualification data, so that the driver belongs to my company.
72. As a 物流公司, I want to modify a driver's basic data and trigger re-verification for important identity changes, so that records stay accurate and compliant.
73. As a 物流公司, I want to read and set a driver's 接单可用性, 雇佣关系 and 账号状态 as separate fields, so that states stay independent.
74. As a 物流公司, I want a driver with 暂停接单 to receive no new tasks while existing tasks keep running, so that in-flight work is not disrupted.
75. As a 物流公司, I want a departing driver's in-progress tasks transferred through 运输异常 with the original participation and handover time preserved, so that work continues.
76. As a 物流公司, I want a departing driver's account marked 已禁用 with a departure date after handover, so that historical tasks and expenses remain attributed to the original driver.
77. As a 物流公司, I want a vehicle list with plate, type, length, max load, actual owner, current driver, status and document status, so that I can manage my fleet.
78. As a 物流公司, I want to register both company-owned and driver-owned vehicles, so that both ownership cases are covered.
79. As a 物流公司, I want to assign a company vehicle to a driver, and have driver-owned vehicles linked to their driver by default, so that all vehicles are under company management.
80. As a 物流公司, I want a vehicle that is 维修中 or 已停用 to be ineligible for new tasks, so that unsafe vehicles are not dispatched.
81. As a 物流公司, I want vehicle replacement to go through 运输异常 with before/after records and reasons preserved, so that打卡 and photos are never overwritten.
82. As a 物流公司, I want a driver to be unable to change vehicles on their own, so that control stays with the company.
83. As an 管理员, I want vehicle 转籍 executed only when the vehicle has no in-progress task, so that history is not broken.
84. As a 物流公司, I want to create a dispatch with order, driver, vehicle, planned load/delivery times and notes, so that a 运输任务 is started.
85. As a 物流公司, I want dispatch rules enforced (driver and vehicle belong to me, both available, driver qualified, vehicle meets requirements, no time conflict), so that invalid assignments are prevented.
86. As a 物流公司, I want a time conflict defined as overlapping planned load-to-delivery intervals on the same driver or vehicle among active tasks, so that the rule is deterministic.
87. As a 物流公司, I want the driver notified and able to accept or reject (with reason), so that assignment is confirmed.
88. As a 物流公司, I want to re-dispatch before transport starts while recording original/new driver, original/new vehicle, reason and time, so that changes are auditable.
89. As a 物流公司, I want changes after transport starts to go through 运输异常 rather than overwriting records, so that evidence is preserved.
90. As a 物流公司, I want to see all in-progress tasks and their progress nodes, so that I can monitor execution.
91. As a 物流公司, I want to view driver photos and 打卡 records, so that I can verify key nodes.
92. As a 物流公司, I want to manually follow up tasks whose progress has stalled, so that delays are handled.
93. As a 物流公司, I want to submit and view 运输异常 (vehicle failure, accident, cargo damage/loss, shipper delay, receiver refusal, lateness, route problems, location anomaly, other), so that problems are recorded.
94. As a 物流公司, I want to "contact" the driver, shipper or receiver by revealing stored phone numbers for offline calls, so that V1 needs no IM.
95. As a 物流公司, I want outcomes 继续运输 / 调整送达时间 / 更换车辆 / 更换司机 / 重新安排运输 to return the order to 运输中 (or 已承接 if not started), so that order and task states stay consistent.
96. As a 物流公司, I want 终止运输 to be the only in-transit outcome that sets the order to 已取消 with a written reason, so that cancellation is controlled.
97. As a 物流公司, I want every exception outcome appended with actor role and result, so that the record is immutable and auditable.
98. As a 物流公司, I want an expense list filterable by driver, task, expense type, submission time and review status, so that I can process claims.
99. As a 物流公司, I want expense details with type, amount, time, description, vouchers and linked task, so that I can judge each claim.
100. As a 物流公司, I want to approve or reject a claim, with a mandatory reason on rejection, so that decisions are explained.
101. As a 物流公司, I want 审核状态 and 支付状态 as two independent fields, so that approval does not imply payment.
102. As a 物流公司, I want to mark a single claim 已支付 after offline payment with operator and time recorded, so that the two-stage flow is captured without online payment.
103. As a 物流公司, I want a rejected claim resubmitted by the driver to become a new claim linked to the original rejection, so that history is preserved.
104. As a 物流公司, I want claims processed one at a time rather than in batches, so that V1 scope is respected.
105. As a 物流公司, I want notifications for acceptance, driver accepted/rejected, arrival at shipper/receiver, transport start, expense submission and exception submission, so that I stay informed.
106. As a 物流公司, I want to see only orders I accepted and drivers/vehicles I own, so that permission isolation holds.
107. As a 司机, I want a homepage with today's tasks, pending confirmation, pending loading, in transit, pending sign-off, pending expense submission, recent records and company notices, so that I can plan my day.
108. As a 司机, I want to see full details of tasks assigned to me (number, cargo, locations, contacts, phones, planned times, vehicle, requirements, company notes), so that I can execute.
109. As a 司机, I want to accept a task and move it to my pending list, so that the company knows I am ready.
110. As a 司机, I want to reject a task with a reason, so that the company can reassign.
111. As a 司机, I want to check in at the shipping place with location, time,现场照片 and remarks, so that arrival is evidenced.
112. As a 司机, I want a location anomaly warning when I am outside the configured radius, and the ability to submit an exception note, so that genuine deviations are handled.
113. As a 司机, I want to upload before/during/after loading photos and confirm loading complete, so that the loading process is recorded.
114. As a 司机, I want to submit loading exceptions (quantity mismatch, damage, description mismatch, cannot load, overload, other), so that problems surface early.
115. As a 司机, I want to start transport only after check-in, loading and vehicle/cargo confirmation, so that the sequence is enforced.
116. As a 司机, I want to see receiving place, contacts, requirements and ETA during transit, so that I can deliver.
117. As a 司机, I want to submit in-transit exceptions (failure, accident, road closure, congestion, cargo issue, expected delay) with photos, so that the company can respond.
118. As a 司机, I want to be unable to change vehicles myself and have any change routed through the company exception flow, so that control is preserved.
119. As a 司机, I want to check in at the receiving place with location, time and photos, with an anomaly warning when outside range, so that arrival is evidenced.
120. As a 司机, I want to upload before/during/after unloading photos and submit unloading exceptions (damage, quantity mismatch, refusal), so that delivery is recorded.
121. As a 司机, I want to submit sign-off details (receiving condition, time, receiver, sign-off photo, voucher, remarks), so that completion can be confirmed.
122. As a 司机, I want my submitted sign-off voucher to drive the task and then the 运输订单 to 已完成 after company confirmation, with the shipper only reading, so that completion is carrier-confirmed.
123. As a 司机, I want to submit one expense at a time (fuel, toll, parking, repair, other) with multiple vouchers linked to a task, so that reimbursement is granular.
124. As a 司机, I want to see review status and rejection reasons, and resubmit eligible expenses, so that I can correct claims.
125. As a 司机, I want my transport history (completed, in progress, rejected, cancelled, exception) with details, check-ins, photos and expenses, so that I can audit my work.
126. As a 司机, I want my expense records (pending, approved, rejected, pending payment, paid), so that I can track reimbursement.
127. As an 管理员, I want a homepage with platform-wide counts of shippers, companies, drivers, vehicles, total/pending/in-transit/completed/exception orders and pending certifications, so that I can monitor the platform.
128. As an 管理员, I want to list all shippers with their basic and certification data, so that I can supervise them.
129. As an 管理员, I want to approve or reject shipper certifications with a mandatory rejection reason, so that the review is explicit.
130. As an 管理员, I want to disable or restore shippers, so that violations are handled without data loss.
131. As an 管理员, I want to see a shipper's orders and warehouses, so that I can investigate issues.
132. As an 管理员, I want to list all logistics companies with basic data and business licences, so that I can supervise them.
133. As an 管理员, I want to approve or reject enterprise certifications, so that only qualified companies operate.
134. As an 管理员, I want to disable or restore logistics companies, so that violations are handled.
135. As an 管理员, I want to see a company's drivers, vehicles, orders and transport records, so that I can audit it.
136. As an 管理员, I want to list all drivers with their company, certification, qualification, account status, history and expenses, so that I can supervise them.
137. As an 管理员, I want to restrict or disable non-compliant drivers, so that platform rules are enforced.
138. As an 管理员, I want to list all vehicles with plate, type, owner, company, current driver, status and documents, so that I can supervise them.
139. As an 管理员, I want to handle non-compliant or abnormal vehicles, so that risks are contained.
140. As an 管理员, I want to list all orders and query by number, shipper, company, status and publish time, so that I can support the platform.
141. As an 管理员, I want to view all transport tasks with company, driver, vehicle, shipping/receiving info, status, check-ins, photos, expenses and exception records, so that I can investigate.
142. As an 管理员, I want unified certification review for shippers, companies, drivers, driving qualifications and vehicle documents, with mandatory rejection reasons, so that review work is centralised.
143. As an 管理员, I want to handle platform exceptions (complaints, order disputes, company/driver violations, vehicle anomalies, stalled tasks, expense disputes) by appending 异常处理记录, so that resolution is traceable.
144. As an 管理员, I want to approve vehicle 转籍 only when there is no in-progress task, so that historical task vehicle data stays valid.
145. As an 管理员, I want to publish platform announcements and notices, so that users are informed of maintenance and rule changes.
146. As an 管理员, I want to be unable to directly rewrite orders, tasks, check-ins or expenses, with my writes limited to review, disable/restore, exception handling and notices, so that business evidence is protected.
147. As a user, I want notifications automatically triggered by business state changes and delivered to the correct recipient set, so that communication is timely.
148. As an 管理员, I want announcements to be independent content rather than business events, so that the two notification kinds are not confused.
149. As a user, I want order, task, dispatch, vehicle-change, check-in, photo, expense, review and exception histories to be read-only and append-only, so that history is immutable.
150. As a user, I want corrections recorded as new dated records with reasons while originals remain, so that the audit trail survives.
151. As a user, I want permission isolation so that a shipper sees only their own data, a company only its accepted orders and own drivers/vehicles, and a driver only assigned tasks and related expenses, so that data cannot leak across roles.
152. As an 管理员, I want platform-wide read access without business-record write access, so that oversight does not compromise evidence.
153. As a user, I want logout to invalidate the session token immediately, so that the old login state cannot be reused.
154. As a user, I want order/task/expense numbers generated as type prefix plus date plus a daily non-reused sequence, so that identifiers are readable and unique.
155. As a user, I want vouchers stored as local files with only relative paths in the database, so that no external object storage is needed.
156. As a user, I want all monetary amounts stored as integer cents in CNY with conversion to yuan/Decimal only at the API boundary, and all times as ISO 8601 local datetimes, so that values are exact and consistent (SQLite stores DECIMAL as REAL, causing rounding errors).
157. As a user, I want no physical deletes anywhere, with lifecycle expressed by 停用 / 离职 / 已禁用 / 已注销 states, so that references never dangle.
158. As a user, I want the Web clients and the driver H5 to share one backend API, so that business rules are defined once.
159. As a user, I want consistent pagination and filtering across all list endpoints, so that interfaces behave predictably.
160. As a user, I want unauthorised or invalid requests to return clear errors without exposing other parties' data, so that isolation is enforced at the boundary.

## Implementation Decisions

- Backend modules: identity and account management; shipper business (warehouses, order publishing, order queries, cancellation); carrier business (order pool, acceptance, driver management, vehicle management, dispatch, transport progress, exception handling, expense review and payment marking); driver business (task execution, check-ins, loading/unloading, sign-off, expense submission, personal records); administrator operations (review, disable/restore, platform exceptions, notices, vehicle 转籍); notification generation; local file storage; append-only history.
- Frontend modules: a Vue3 Web app with role-aware routing and views for three web roles; a Vue3 mobile H5 app for the driver. Both call the same FastAPI HTTP API; no separate business logic in either client.
- Account model: one `Account` table with a role discriminator plus one profile table per role. companys create driver accounts; first login forces password change and identity/qualification completion as 身份绑定. Login sessions are opaque tokens persisted in SQLite; disable or logout deletes the token. Password hashes use a standard-library KDF; no SMS verification.
- State dimensions: `账号状态` is the sole authority for business blocking with values {正常使用, 已禁用, 已注销}; `认证状态` has {未提交, 待审核, 审核通过, 审核不通过}; driver `接单可用性` {可派单, 任务占用中, 暂停接单} and `雇佣关系` {在职, 离职} are separate; vehicle `可用性` {可用, 占用中, 暂停使用} and `生命周期` {在册, 维修中, 已停用} are separate. These are never collapsed into one field.
- 运输订单状态: {待承接, 已承接, 运输中, 已完成, 取消处理中, 已取消, 异常处理中}. 运输任务状态: {待司机确认, 待装货, 运输中, 待签收, 待确认完成, 已完成, 异常, 已拒绝}. The two machines are independent; shipper progress is a read-only projection of order state driven by task state. `取消处理中` and `异常处理中` are mutually exclusive.
- Cancellation: accepted-but-not-started orders go 取消处理中 on shipper request; carrier approval yields 已取消, rejection restores the prior order state with a written reason; no automatic timeout. Started orders route to 异常处理中; only 终止运输 yields 已取消 with a reason.
- Exception mapping: 继续运输 / 调整送达时间 / 更换车辆 / 更换司机 / 重新安排运输 return the order to 运输中 (or 已承接 if not started); 终止运输 sets 已取消. All exception outcomes are appended with actor role and result; no overwrites.
- Driver rejection sets the task to terminal 已拒绝 with a reason and returns the order to 待派单; dispatch history is preserved.
- Dispatch validation: driver and vehicle must belong to the company, be available, driver qualified, vehicle meeting order requirements, and neither may have a time conflict defined by overlapping [planned load, planned delivery] intervals on active tasks.
- Check-in proximity: distance computed with Haversine on stored latitude/longitude against the frozen snapshot, default radius 1 km and configurable; out-of-range produces a warning plus a required exception note, never an automatic rejection. No continuous GPS trace.
- History model: business history records are append-only and versioned — corrections insert a new record carrying `replaced_by` and a reason; originals are never UPDATEd or DELETEd. Master data (warehouse details, driver basic details) remains editable. Administrators cannot write order, task, check-in or expense records.
- Data model: Account and role profiles; 仓库; 运输订单 with embedded 发货快照 and 收货快照; 运输任务; 派单记录; 打卡记录; 现场照片/凭证 with relative file paths; 报销费用 with independent 审核状态 and 支付状态; 异常处理记录 with actor role; 通知 records; 认证记录 with rejection reason.
- API contract: REST over JSON with an opaque session token in a cookie or header; list endpoints share pagination and filter conventions; errors are structured and never leak other roles' data; completion and payment actions record operator and time.
- Identifiers follow `prefix-YYMMDD-0001` per entity type (order / task / expense / dispatch), generated server-side with a per-day non-reused sequence.
- Money is stored as integer cents in CNY, converted to/from yuan `Decimal` or string only at the API/Pydantic boundary; SQLite maps `DECIMAL` to NUMERIC affinity (stored as REAL), so floating-point amounts are avoided. All time fields are ISO 8601 local datetimes; no timezone library.
- File vouchers are written to a dedicated local directory inside the project; the database stores only relative paths. Notifications are inbox records marked as sent; no read state, email, SMS or push.
- Payment: 已支付 is set by the carrier after offline settlement on a single claim, recording operator and time; no payment gateway and no batch processing.
- Out-of-scope decisions are recorded in `docs/adr/`; terminology in `GLOSSARY.md`.

## Testing Decisions

- A good test asserts only externally observable behavior: HTTP status, response payload, and business state observable through subsequent API reads by the relevant role. Tests never assert on internal functions, private helpers, or database schema details. Append-only history is verified by reading records back through the API after a correction and confirming the original still exists with its reason, not by inspecting tables.
- The only seam is the FastAPI HTTP API, exercised as a black box. Each test runs against a throwaway SQLite database and an isolated local file directory injected into the app, drives real login/session flows for all four roles (including the driver H5, which uses the same API), and tears both down afterwards. Both web roles and the driver are covered through this one seam; no separate frontend or domain-unit seams are introduced.
- Modules covered through the seam: authentication and session invalidation; certification review and rejection reasons; warehouse CRUD and snapshot immutability; order publishing, filtering and detail reads; acceptance exclusivity; dispatch validation and time conflicts; driver accept/reject and re-dispatch; check-in proximity warnings; loading/unloading and sign-off; task-driven order completion; cancellation branches; exception outcomes and order-state mapping; expense review/payment two-stage flow and resubmission; notification delivery by recipient; permission isolation; append-only history; identifier generation.
- Prior art: none — the repository is greenfield with no code or existing tests. The single HTTP API seam was proposed and confirmed with the user before writing this spec; it is the highest possible seam because both web clients and the driver H5 share the same backend.

## Out of Scope

- 多家物流公司报价竞价；货主与物流公司之间的运费结算、对账、在线支付。
- 物流公司内部调度员 / 财务等员工子角色；平台内即时通讯（IM）。
- 多个发货地或多个收货地；司机实时 GPS 轨迹与地图查看。
- 费用报销的硬性金额上限；货主对运输完成的二次确认。
- 原生微信小程序 / uni-app 工具链；短信验证码；JWT；Redis / MySQL / PostgreSQL / Docker 等额外服务；邮件 / 短信 / 推送通知；在线支付网关；批量支付；超时自动取消；议价流程。
- 前端浏览器级 E2E 测试 seam 与领域纯函数单元测试 seam（本次只保留单一 HTTP API seam）。
- V1 之外的任何需求（见需求文档 8.1 V1 范围外统一登记）。

## Further Notes

- Source of truth: `writing-block.md` (V1.2), `GLOSSARY.md`, and `docs/adr/0001`–`0008`. All vocabulary in this spec follows the glossary (运输订单 / 货源 / 运输任务 / 发货快照 / 收货快照 / 运费报价 / 报销费用 / 打卡 / 异常处理记录).
- The 12 business decisions were confirmed on 2026-11-15; the design clarifications in sections 8.2/8.3 were confirmed on 2026-11-22 and back-filled into the requirement doc.
- The issue tracker is GitHub `hzh-Study/xm-logistics-platform` via `gh`.
- Published as issue #1 in `hzh-Study/xm-logistics-platform` with the `ready-for-agent` label.
