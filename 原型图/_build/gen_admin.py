# -*- coding: utf-8 -*-
"""Web 端：管理员全套页面"""
from common import *

def build():
    # ---------- 管理员工作台 ----------
    c = stats([('286','货主数'),('74','公司数'),('512','司机数'),('368','车辆数'),
               ('1,248','订单总数'),('36','待承接'),('118','运输中'),('842','已完成'),
               ('7','异常'),('12','待审认证')])
    c += '<div style="height:16px"></div>'
    c += ('<div class="notice notice-info">' + ico('shield')
      + '<div>管理员仅有平台级只读查询 + 审核 / 禁用恢复 / 公告 / 异常处置权限，不能直接改写订单、运输任务、打卡或费用记录。</div></div><div style="height:16px"></div>')
    c += panel('审核待办', '<ul class="list-simple">'
      + '<li><span>统一认证审核 · 12 项待审核</span><span class="meta"><a href="web-21-certifications.html" style="color:var(--brand)">去审核</a></span></li>'
      + '<li><span>货主认证审核 · 4 项</span><span class="meta"><a href="web-28-shipper-certifications.html" style="color:var(--brand)">去审核</a></span></li>'
      + '<li><span>公司认证审核 · 3 项</span><span class="meta"><a href="web-29-carrier-certifications.html" style="color:var(--brand)">去审核</a></span></li>'
      + '<li><span>车辆转籍申请 · 2 项</span><span class="meta"><a href="web-27-vehicle-transfers.html" style="color:var(--brand)">去处理</a></span></li>'
      + '<li><span>平台异常 · 3 项待处理</span><span class="meta"><a href="web-26-platform-exceptions.html" style="color:var(--brand)">去处置</a></span></li></ul>')
    c += panel('平台运输动态', table(['#订单编号','货主 / 物流公司','货物','订单状态','更新时间','操作'], [
      ['ORDER-251120-0012','华远建材 / 盛达物流','热轧钢板 · 32 吨',pill('运输中'),'2026-11-21 08:32',ops('查看')],
      ['ORDER-251118-0007','华远建材 / 盛达物流','水泥 · 80 吨',pill('已承接'),'2026-11-18 15:02',ops('查看')],
      ['ORDER-251116-0011','华远建材 / —','冷轧卷板 · 18 吨',pill('取消处理中'),'2026-11-16 16:25',ops('查看')],
      ['ORDER-251115-0004','远东实业 / 通顺物流','建材辅料 · 12 吨',pill('异常处理中'),'2026-11-15 11:08',ops('查看')],
    ], paginate=False))
    save('web-20-admin-dashboard.html', web_shell('admin','web-20-admin-dashboard.html','工作台',
        '平台管理员 · 全局监控与审核', c,
        right='<span style="font-size:13px;color:var(--text-2)">平台管理员</span>'))

    # ---------- 统一认证审核 ----------
    def review_page(fname, title, sub, active, rows, detail):
        cc = page_head(title, sub)
        cc += filters([('主体类型',sel(['货主','物流公司','司机','驾驶资格','车辆证件'])),
                       ('认证状态',sel(['未提交','待审核','审核通过','审核不通过'])),
                       ('名称 / 手机号',inp('请输入')),('提交时间',inp('开始日期 ～ 结束日期'))])
        cc += panel('审核列表', table(['#主体编号','主体名称','主体类型','提交时间','认证状态','操作'], rows), tight=True)
        dd = ('<div class="notice notice-info" style="margin-bottom:16px">' + ico('shield')
          + '<div>审核通过后资料生效；驳回必须填写原因，原因作为追加记录对该主体可见。</div></div>'
          + detail
          + '<div class="field" style="margin-top:16px"><label class="field-label"><span class="req">*</span>驳回原因（驳回时必填）</label>'
          + '<textarea class="textarea" id="certReason" placeholder="请说明驳回原因与需补充的资料"></textarea>'
          + '<div class="help err" id="certReasonTip" style="display:none">驳回原因为必填项。</div></div>')
        cc += drawer('certDrawer','认证审核详情', dd,
            '<button class="btn btn-secondary" data-act="close">关闭</button>'
            '<button class="btn btn-danger" onclick="submitReject(\'certReason\',\'认证已驳回，原因已追加\')">驳回</button>'
            '<button class="btn btn-primary" onclick="submitAction(\'审核通过，认证状态更新\')">通过</button>')
        cc = cc.replace('<button class="btn btn-text" onclick="toast(\'原型演示：审核\')">审核</button>',
                        '<button class="btn btn-text" onclick="openDrawer(\'certDrawer\')">审核</button>')
        save(fname, web_shell('admin', active, title, sub, cc))

    detail_all = kv([('主体名称','远东实业有限公司'),('主体类型','货主 · 企业'),
      ('统一社会信用代码','91310117MA1K5XXXXX'),('法定代表人','吴芳'),('联系人 / 电话','吴芳 / 13700137001'),
      ('营业执照','营业执照_远东实业.pdf'),('提交时间','2026-11-22 09:12')])
    review_page('web-21-certifications.html','统一认证审核',
        '集中审核货主、物流公司、司机、驾驶资格与车辆证件 · 驳回原因必填',
        'web-21-certifications.html',
        [['ACCT-251122-0031','远东实业有限公司','货主','2026-11-22 09:12',pill('待审核'),ops('审核')],
         ['ACCT-251121-0028','通顺物流有限公司','物流公司','2026-11-21 15:40',pill('待审核'),ops('审核')],
         ['ACCT-251120-0022','刘志强','司机','2026-11-20 11:05',pill('待审核'),ops('审核')],
         ['ACCT-251119-0017','沪C·9T556','车辆证件','2026-11-19 16:28',pill('待审核'),ops('审核')],
         ['ACCT-251118-0012','陈明','驾驶资格','2026-11-18 10:30',pill('审核不通过'),ops('查看')]],
        detail_all)

    detail_shipper = kv([('主体名称','远东实业有限公司'),('认证类型','企业'),
      ('统一社会信用代码','91310117MA1K5XXXXX'),('法定代表人','吴芳'),('联系人 / 电话','吴芳 / 13700137001'),
      ('营业执照','营业执照_远东实业.pdf'),('提交时间','2026-11-22 09:12')])
    review_page('web-28-shipper-certifications.html','货主认证审核',
        '仅处理货主认证 · 个人 / 企业两类资料',
        'web-28-shipper-certifications.html',
        [['ACCT-251122-0031','远东实业有限公司','企业','2026-11-22 09:12',pill('待审核'),ops('审核')],
         ['ACCT-251120-0019','张敏','个人','2026-11-20 14:22',pill('待审核'),ops('审核')],
         ['ACCT-251117-0008','恒信物资经营部','企业','2026-11-17 09:31',pill('审核不通过'),ops('查看')]],
        detail_shipper)

    detail_carrier = kv([('企业名称','通顺物流有限公司'),('统一社会信用代码','91310120MA1K7XXXXX'),
      ('法定代表人','马骏'),('注册资本','300 万元'),('经营范围','道路普通货物运输'),
      ('营业执照','营业执照_通顺物流.pdf'),('道路运输经营许可证','道路运输经营许可证_通顺.pdf'),
      ('提交时间','2026-11-21 15:40')])
    review_page('web-29-carrier-certifications.html','公司认证审核',
        '仅处理物流公司企业认证 · 营业执照与资质资料',
        'web-29-carrier-certifications.html',
        [['ACCT-251121-0028','通顺物流有限公司','物流公司','2026-11-21 15:40',pill('待审核'),ops('审核')],
         ['ACCT-251119-0015','迅达运输服务有限公司','物流公司','2026-11-19 13:06',pill('待审核'),ops('审核')],
         ['ACCT-251115-0004','华通路运有限公司','物流公司','2026-11-15 10:44',pill('审核通过'),ops('查看')]],
        detail_carrier)

    # ---------- 平台主体查询 ----------
    c = page_head('平台主体查询','货主 / 物流公司 / 司机 / 车辆统一查询 · 只读',
        '<button class="btn btn-text" onclick="toast(\'已导出查询结果（原型演示）\')">导出</button>')
    c += '<div class="tabs tab-scope">'
    for i,(name,on) in enumerate([('货主',True),('物流公司',False),('司机',False),('车辆',False)]):
        c += f'<div class="tab{" active" if on else ""}" data-group="acct" data-name="{name}" onclick="switchTab(this,\'acct\')">{name}</div>'
    c += '</div>'
    c += '<div class="tabpane active" data-group="acct" data-name="货主">'
    c += filters([('名称',inp('请输入')),('认证状态',sel(['未提交','待审核','审核通过','审核不通过'])),
                  ('账号状态',sel(['正常使用','已禁用','已注销'])),('手机号',inp('请输入'))])
    c += table(['#主体编号','名称','认证状态','账号状态','订单数','注册时间','操作'], [
      ['ACCT-251106-0008','华远建材有限公司',pill('审核通过'),pill('正常使用'),'18','2026-11-06 10:22',ops('查看','禁用')],
      ['ACCT-251118-0024','远东实业有限公司',pill('待审核'),pill('正常使用'),'0','2026-11-18 09:12',ops('查看','禁用')],
      ['ACCT-251105-0003','宏基物资有限公司',pill('审核通过'),pill('已禁用'),'32','2026-11-05 15:40',ops('查看','恢复')],
    ])
    c += '</div>'
    for name, rows, cols in [
      ('物流公司', [
        ['ACCT-251102-0002','盛达物流有限公司',pill('审核通过'),pill('正常使用'),'14','2026-11-02 08:30'],
        ['ACCT-251121-0028','通顺物流有限公司',pill('待审核'),pill('正常使用'),'0','2026-11-21 15:40'],
      ], ['#主体编号','企业名称','认证状态','账号状态','司机数','注册时间','操作']),
      ('司机', [
        ['ACCT-251103-0012','王建国',pill('审核通过'),pill('正常使用'),'盛达物流','2026-11-03 09:20'],
        ['ACCT-251119-0033','刘志强',pill('待审核'),pill('正常使用'),'盛达物流','2026-11-19 11:05'],
        ['ACCT-251108-0018','陈明',pill('审核通过'),pill('已禁用'),'通顺物流','2026-11-08 16:12'],
      ], ['#主体编号','姓名','认证状态','账号状态','所属公司','注册时间','操作']),
      ('车辆', [
        ['VEH-251102-0004','沪A·8F231',pill('在册'),pill('可用'),'盛达物流','王建国'],
        ['VEH-251110-0017','苏E·7M220',pill('维修中'),pill('暂停使用'),'盛达物流','孙伟'],
      ], ['#车辆编号','车牌号','生命周期','可用性','所属公司','当前司机','操作']),
    ]:
        c += f'<div class="tabpane" data-group="acct" data-name="{name}">'
        c += filters([('关键词',inp('请输入名称 / 车牌')),('认证状态',sel(['未提交','待审核','审核通过','审核不通过'])),
                      ('账号状态',sel(['正常使用','已禁用','已注销']))])
        c += table(cols, [r + [ops('查看','禁用' if '已禁用' not in ''.join(r) else '恢复')] for r in rows])
        c += '</div>'
    c += modal('disableModal','禁用主体',
        '禁用后该主体账号状态变为「已禁用」，历史业务记录保留；可随时恢复。',
        '<button class="btn btn-secondary" onclick="closeModal()">取消</button>'
        '<button class="btn btn-danger" onclick="submitAction(\'账号状态已更新为已禁用\')">确认禁用</button>')
    c = c.replace('<button class="btn btn-text" onclick="toast(\'原型演示：禁用\')">禁用</button>',
                  '<button class="btn btn-text" onclick="openModal(\'disableModal\')">禁用</button>')
    save('web-22-accounts.html', web_shell('admin','web-22-accounts.html','平台主体查询',
        '管理员只读查询 · 禁用 / 恢复为独立操作', c))

    # ---------- 运输订单查询 ----------
    c = page_head('运输订单查询','平台级只读查询 · 按编号、货主、物流公司、状态、发布时间',
        '<button class="btn btn-text" onclick="toast(\'已导出查询结果（原型演示）\')">导出</button>')
    c += filters([('订单编号',inp('请输入')),('货主',inp('请输入')),('物流公司',inp('请输入')),
                  ('订单状态',sel(['待承接','已承接','运输中','已完成','取消处理中','已取消','异常处理中'])),
                  ('发布时间',inp('开始日期 ～ 结束日期'))])
    c += table(['#订单编号','货主','物流公司','货物','订单状态','发布时间','操作'], [
      ['ORDER-251120-0012','华远建材有限公司','盛达物流有限公司','热轧钢板 · 32 吨',pill('运输中'),'2026-11-20 09:12',ops('查看')],
      ['ORDER-251118-0007','华远建材有限公司','盛达物流有限公司','水泥 · 80 吨',pill('已承接'),'2026-11-18 14:30',ops('查看')],
      ['ORDER-251116-0011','华远建材有限公司','—','冷轧卷板 · 18 吨',pill('取消处理中'),'2026-11-16 16:20',ops('查看')],
      ['ORDER-251115-0004','远东实业有限公司','通顺物流有限公司','建材辅料 · 12 吨',pill('异常处理中'),'2026-11-15 11:08',ops('查看')],
      ['ORDER-251112-0019','华远建材有限公司','盛达物流有限公司','冷轧卷板 · 18 吨',pill('已完成'),'2026-11-12 08:40',ops('查看')],
    ], total='共 1,248 条')
    save('web-23-admin-orders.html', web_shell('admin','web-23-admin-orders.html','运输订单查询',
        '只读，不提供改写业务记录的操作', c))

    # ---------- 运输任务查询 ----------
    c = page_head('运输任务查询','平台级只读查询 · 含打卡、照片、费用与异常记录', '')
    c += filters([('任务编号',inp('请输入')),('物流公司',inp('请输入')),('司机',inp('请输入')),
                  ('任务状态',sel(['待司机确认','待装货','运输中','待签收','待确认完成','已完成','异常','已拒绝'])),
                  ('车辆',inp('请输入车牌'))])
    c += table(['#任务编号','物流公司 / 司机','车辆','货物','任务状态','计划送达','操作'], [
      ['TASK-251120-0003','盛达物流 / 王建国','沪A·8F231','热轧钢板 · 32 吨',pill('运输中'),'2026-11-22 18:00',ops('查看')],
      ['TASK-251118-0002','盛达物流 / 李海涛','沪B·3D772','水泥 · 80 吨',pill('待司机确认'),'2026-11-23 18:00',ops('查看')],
      ['TASK-251116-0004','盛达物流 / 孙伟','苏E·7M220','冷轧卷板 · 18 吨',pill('异常'),'2026-11-18 18:00',ops('查看')],
      ['TASK-251110-0001','通顺物流 / 赵强','沪A·5K108','镀锌板 · 9 吨',pill('已完成'),'2026-11-12 18:00',ops('查看')],
    ], total='共 986 条')
    dd = ('<div class="notice notice-info" style="margin-bottom:16px">' + ico('eye')
      + '<div>管理员只读查看，打卡照片与费用凭证可查阅但不能修改。</div></div>'
      + kv([('任务编号','TASK-251120-0003'),('任务状态',pill('运输中')),('司机 / 车辆','王建国 / 沪A·8F231'),
            ('发货地打卡','2026-11-21 07:58 · 距离快照 120 米 · 照片 3 张'),
            ('起运打卡','2026-11-21 08:32 · 装前 / 装中 / 装后'),('报销费用','EXP-251120-0007 · ¥ 860.00 · ' + pill('待审核')),
            ('异常处理记录','无')]))
    c += drawer('taskDrawer','运输任务详情', dd, '<button class="btn btn-secondary" data-act="close">关闭</button>')
    c = c.replace('<button class="btn btn-text" onclick="toast(\'原型演示：查看\')">查看</button>',
                  '<button class="btn btn-text" onclick="openDrawer(\'taskDrawer\')">查看</button>')
    save('web-24-admin-tasks.html', web_shell('admin','web-24-admin-tasks.html','运输任务查询',
        '管理员只读 · 可查阅业务证据链', c))

    # ---------- 平台公告与通知 ----------
    c = page_head('平台公告与通知','公告为独立内容，与业务事件触发的通知分开管理',
        '<button class="btn btn-primary" onclick="openDrawer(\"annDrawer\")">' + ico('plus','icon-sm') + '发布公告</button>')
    c += filters([('标题',inp('请输入标题')),('公告类型',sel(['系统维护','规则变更','功能更新','其它'])),
                  ('发布时间',inp('开始日期 ～ 结束日期'))])
    c += panel('公告列表', table(['#标题','公告类型','接收范围','发布时间','状态','操作'], [
      ['关于系统维护的通知','系统维护','全部用户','2026-11-22 09:00','已发布',ops('编辑','查看')],
      ['运输订单状态规则调整说明','规则变更','货主 / 物流公司','2026-11-18 14:20','已发布',ops('编辑','查看')],
      ['司机端打卡功能更新','功能更新','司机','2026-11-15 10:00','已发布',ops('编辑','查看')],
      ['认证资料提交要求补充','规则变更','物流公司','2026-11-10 16:30','草稿',ops('编辑','发布')],
    ]))
    ad = ('<div class="field"><label class="field-label"><span class="req">*</span>标题</label>' + inp('请输入公告标题') + '</div>'
      + '<div class="field"><label class="field-label"><span class="req">*</span>公告类型</label>'
      + sel(['系统维护','规则变更','功能更新','其它']) + '</div>'
      + '<div class="field"><label class="field-label"><span class="req">*</span>接收范围</label><div class="check-row">'
      + ''.join(f'<label><input type="checkbox" {"checked" if x=="全部用户" else ""}>{x}</label>' for x in ['全部用户','货主','物流公司','司机']) + '</div></div>'
      + '<div class="field"><label class="field-label"><span class="req">*</span>正文</label><textarea class="textarea" placeholder="请输入公告正文"></textarea></div>')
    c += drawer('annDrawer','发布平台公告', ad,
        '<button class="btn btn-secondary" data-act="close">保存草稿</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'公告已发布\')">发布</button>')
    save('web-25-announcements.html', web_shell('admin','web-25-announcements.html','平台公告与通知',
        '已发布 3 · 草稿 1', c))

    # ---------- 平台异常管理 ----------
    c = page_head('平台异常管理','投诉 / 纠纷 / 违规 / 停滞 / 费用争议 · 仅可追加异常处理记录',
        '<button class="btn btn-primary" onclick="openDrawer(\"peDrawer\")">' + ico('plus','icon-sm') + '登记异常</button>')
    c += filters([('异常类型',sel(['投诉','订单纠纷','物流公司违规','司机违规','车辆异常','任务停滞','费用争议','其它'])),
                  ('关联主体',inp('请输入')),('处理状态',sel(['待处理','处理中','已处理'])),('时间',inp('开始日期 ～ 结束日期'))])
    c += table(['#异常编号','异常类型','关联主体 / 订单','上报人','上报时间','处理状态','操作'], [
      ['PEX-251122-0003','订单纠纷','ORDER-251118-0007<br><span class="cell-sub">华远建材 / 盛达物流</span>','货主','2026-11-22 10:12','待处理',ops('处置','查看')],
      ['PEX-251121-0002','司机违规','ACCT-251108-0018 · 陈明','物流公司','2026-11-21 15:30','处理中',ops('查看')],
      ['PEX-251120-0001','任务停滞','TASK-251117-0006','系统','2026-11-20 09:08','已处理',ops('查看')],
    ])
    ped = ('<div class="notice notice-warning" style="margin-bottom:16px">' + ico('warn')
      + '<div>管理员只能追加异常处理记录，不能改写运输订单、任务、打卡或费用记录。</div></div>'
      + kv([('异常类型','订单纠纷'),('关联订单','ORDER-251118-0007'),('上报人','货主 华远建材有限公司'),
            ('上报时间','2026-11-22 10:12'),('问题描述','物流公司未按约定时间安排装货，申请平台介入')])
      + '<div class="field" style="margin-top:16px"><label class="field-label"><span class="req">*</span>处置结果</label>'
      + '<textarea class="textarea" placeholder="请填写处置结果，将追加为异常处理记录"></textarea></div>')
    c += drawer('peDrawer','平台异常处置', ped,
        '<button class="btn btn-secondary" data-act="close">关闭</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'处置记录已追加，原文保留\')">提交处置</button>')
    c = c.replace('<button class="btn btn-text" onclick="toast(\'原型演示：处置\')">处置</button>',
                  '<button class="btn btn-text" onclick="openDrawer(\'peDrawer\')">处置</button>')
    save('web-26-platform-exceptions.html', web_shell('admin','web-26-platform-exceptions.html','平台异常管理',
        '待处理 1 · 处理中 1 · 已处理 1', c))

    # ---------- 车辆转籍 ----------
    c = page_head('车辆转籍','仅当车辆无进行中任务时可转籍 · 审批后历史任务车辆数据保持有效',
        '<button class="btn btn-primary" onclick="openDrawer(\"trDrawer\")">审核转籍申请</button>')
    c += filters([('车牌号',inp('请输入')),('原所属公司',inp('请输入')),('目标公司',inp('请输入')),('状态',sel(['待审核','已通过','已驳回']))])
    c += table(['#申请编号','车牌号','原公司 → 目标公司','申请人','申请时间','进行中任务','状态','操作'], [
      ['TRF-251121-0002','沪C·9T556','通顺物流 → 盛达物流','马骏','2026-11-21 14:20','无',pill('待审核'),ops('审核')],
      ['TRF-251119-0001','沪B·3D772','盛达物流 → 通顺物流','周敏','2026-11-19 10:05','1 条（驳回）',pill('已驳回'),ops('查看')],
      ['TRF-251115-0003','沪A·5K108','恒通物流 → 盛达物流','王强','2026-11-15 16:40','无',pill('审核通过'),ops('查看')],
    ])
    trd = ('<div class="notice notice-info" style="margin-bottom:16px">' + ico('swap')
      + '<div>系统校验：该车辆当前无进行中运输任务，符合转籍条件。转籍后原任务记录的车辆信息不改写。</div></div>'
      + kv([('申请编号','TRF-251121-0002'),('车牌号','沪C·9T556'),('原所属公司','通顺物流有限公司'),
            ('目标公司','盛达物流有限公司'),('申请人','马骏'),('申请时间','2026-11-21 14:20'),
            ('进行中任务','无'),('申请原因','业务调整，车辆随车队划转')])
      + '<div class="field" style="margin-top:16px"><label class="field-label">驳回原因（驳回时必填）</label>'
      + '<textarea class="textarea" id="trReason" placeholder="请说明驳回原因"></textarea>'
      + '<div class="help err" id="trReasonTip" style="display:none">驳回原因为必填项。</div></div>')
    c += drawer('trDrawer','车辆转籍审核', trd,
        '<button class="btn btn-secondary" data-act="close">关闭</button>'
        '<button class="btn btn-danger" onclick="submitReject(\'trReason\',\'转籍申请已驳回\')">驳回</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'转籍已通过，历史记录保留\')">通过</button>')
    c = c.replace('<button class="btn btn-text" onclick="toast(\'原型演示：审核\')">审核</button>',
                  '<button class="btn btn-text" onclick="openDrawer(\'trDrawer\')">审核</button>')
    save('web-27-vehicle-transfers.html', web_shell('admin','web-27-vehicle-transfers.html','车辆转籍',
        '待审核 1 · 已通过 1 · 已驳回 1', c))
