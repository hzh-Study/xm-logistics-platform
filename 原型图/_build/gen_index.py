# -*- coding: utf-8 -*-
"""原型索引页：按角色分组，iframe 预览全部页面"""
from common import *

GROUPS = [
 ('Web · 登录', [
   ('web-01-login.html','登录（含注册展开）','Web / 账号登录'),
 ]),
 ('Web · 货主', [
   ('web-02-shipper-dashboard.html','货主工作台','统计 / 待办 / 订单 / 通知'),
   ('web-03-shipper-certification.html','货主认证','认证状态 / 资料 / 审核记录'),
   ('web-04-shipper-warehouses.html','仓库管理','筛选 / 列表 / 状态'),
   ('web-05-shipper-order-new.html','发布运输订单','分区表单 / 快照 / 报价 / 确认'),
   ('web-06-shipper-orders.html','我的订单','筛选 / 全状态标签 / 分页'),
   ('web-07-order-progress.html','订单进度','横向步骤条 / 时间线 / 打卡照片'),
   ('web-08-order-cancel.html','订单取消','原因必填 / 二次确认'),
 ]),
 ('Web · 物流公司', [
   ('web-09-carrier-dashboard.html','物流公司工作台','统计 / 待办 / 运输动态'),
   ('web-10-carrier-certification.html','企业认证','企业资质 / 审核记录'),
   ('web-11-order-pool.html','订单池（货源）','筛选 / 货源列表 / 承接抽屉'),
   ('web-12-dispatch.html','派单管理','待派单 / 派单抽屉 / 校验'),
   ('web-13-exceptions.html','运输异常','异常列表 / 处置抽屉'),
   ('web-14-cancel-applications.html','取消申请处理','审核 / 驳回必填'),
   ('web-15-drivers.html','司机管理','四维状态 / 新增司机抽屉'),
   ('web-16-vehicles.html','车辆管理','可用性 + 生命周期双维度'),
   ('web-17-expenses.html','费用审核','审核 / 驳回必填 / 标记已支付'),
   ('web-18-task-progress.html','任务进度','节点时间线 / 关联费用'),
 ]),
 ('Web · 管理员', [
   ('web-20-admin-dashboard.html','管理员工作台','平台统计 / 审核待办'),
   ('web-21-certifications.html','统一认证审核','多主体审核 / 驳回必填'),
   ('web-22-accounts.html','平台主体查询','Tab / 只读查询 / 禁用恢复'),
   ('web-23-admin-orders.html','运输订单查询','平台级只读查询'),
   ('web-24-admin-tasks.html','运输任务查询','任务详情抽屉 / 证据链'),
   ('web-25-announcements.html','平台公告与通知','公告列表 / 发布抽屉'),
   ('web-26-platform-exceptions.html','平台异常管理','追加式异常处理记录'),
   ('web-27-vehicle-transfers.html','车辆转籍','无在途任务校验 / 审核'),
   ('web-28-shipper-certifications.html','货主认证审核','个人 / 企业资料'),
   ('web-29-carrier-certifications.html','公司认证审核','营业执照 / 资质'),
 ]),
 ('司机 H5', [
   ('h5-01-login.html','H5 登录','临时密码登录'),
   ('h5-02-onboarding.html','H5 身份绑定','三步流程 / 步骤指示'),
   ('h5-03-blocked.html','H5 账号阻断','只读 / 无可执行操作'),
   ('h5-04-home.html','H5 工作台','统计 / 最近任务 / 通知'),
   ('h5-05-tasks.html','H5 任务列表','卡片列表 / 接单 / 拒绝必填'),
   ('h5-06-departure.html','H5 起运装货打卡','定位占位 / 位置异常警告 / 三阶段照片'),
   ('h5-07-signoff.html','H5 签收','收货信息 / 凭证 / 确认'),
   ('h5-08-exception.html','H5 异常处理','类型单选 / 照片 / 追加记录'),
   ('h5-09-expense.html','H5 费用提交','单次一笔 / 凭证 / 关联任务'),
   ('h5-10-expense-records.html','H5 费用记录','审核 / 支付状态 / 重新提交'),
 ]),
]

def build():
    first = GROUPS[0][1][0][0]
    c = head('物流运输管理平台 · 原型图索引')
    c += '<div class="hub"><aside class="hub-side">'
    c += ('<div class="hub-head"><h1>物流运输管理平台 · 原型图</h1>'
      '<p>UI 原型 v1 · 覆盖 Web 三角色与司机 H5<br>基于 docs/ui-design-brief.md 生成</p></div>')
    for gname, items in GROUPS:
        c += f'<div class="hub-group-title">{gname}</div>'
        for i,(fname,title,sub) in enumerate(items, 1):
            c += (f'<div class="hub-link{" active" if fname==first else ""}" data-preview="{fname}" '
                  f'data-title="{title}" data-sub="{sub}" role="button" tabindex="0">'
                  f'<span class="idx">{i:02d}</span><span>{title}</span></div>')
    c += '</aside><main class="hub-main">'
    c += (f'<div class="hub-bar"><div><span class="title" id="hubTitle">{GROUPS[0][1][0][1]}</span>'
          f'<span class="sub" id="hubSub">{GROUPS[0][1][0][2]}</span></div>'
          f'<a class="btn btn-secondary btn-sm" id="openNew" href="{first}" target="_blank">在新窗口打开</a></div>')
    c += f'<iframe class="hub-frame" id="previewFrame" src="{first}" title="原型预览"></iframe>'
    c += '</main></div>'
    c += foot()
    save('index.html', c)
