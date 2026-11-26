# -*- coding: utf-8 -*-
"""Web 端：物流公司全套页面"""
from common import *

def build():
    # ---------- 物流公司工作台 ----------
    c = stats([('1','待审核企业'),('6','今日承接'),('3','待派单'),('2','待司机确认'),
               ('5','运输中'),('12','已完成'),('1','异常'),('2','待审费用'),
               ('14','司机数'),('9','车辆数')])
    c += '<div style="height:16px"></div>'
    c += ('<div class="notice notice-info">' + ico('shield') + '<div>企业认证：' + pill('审核通过')
          + ' · 账号状态：' + pill('正常使用') + '。承接与派单功能可用。</div></div><div style="height:16px"></div>')
    c += panel('待办事项', '<ul class="list-simple">'
      + f'<li><span>派单管理 · 3 条运输订单待派单</span><span class="meta"><a href="web-12-dispatch.html" style="color:var(--brand)">去处理</a></span></li>'
      + f'<li><span>任务确认 · 2 条派单待司机确认</span><span class="meta"><a href="web-18-task-progress.html" style="color:var(--brand)">去查看</a></span></li>'
      + f'<li><span>费用审核 · 2 笔报销费用待审核</span><span class="meta"><a href="web-17-expenses.html" style="color:var(--brand)">去审核</a></span></li>'
      + f'<li><span>取消申请 · 1 条取消申请待处理</span><span class="meta"><a href="web-14-cancel-applications.html" style="color:var(--brand)">去处理</a></span></li>'
      + f'<li><span>运输异常 · 1 条异常待处置</span><span class="meta"><a href="web-13-exceptions.html" style="color:var(--brand)">去处置</a></span></li>'
      + '</ul>')
    c += panel('最近运输动态', table(['#任务编号','货物 / 订单','司机 / 车辆','任务状态','更新时间','操作'], [
      ['TASK-251120-0003','热轧钢板 · 32 吨<br><span class="cell-sub">ORDER-251120-0012</span>','王建国 / 沪A·8F231',pill('运输中'),'2026-11-21 08:32',ops('查看进度')],
      ['TASK-251118-0002','水泥 · 80 吨','李海涛 / 沪B·3D772',pill('待司机确认'),'2026-11-18 15:10',ops('查看')],
      ['TASK-251117-0006','机电设备 · 6 件','赵强 / 沪A·5K108',pill('待装货'),'2026-11-17 18:02',ops('查看')],
      ['TASK-251116-0004','冷轧卷板 · 18 吨','孙伟 / 苏E·7M220',pill('异常'),'2026-11-16 12:44',ops('处理异常')],
    ], paginate=False))
    save('web-09-carrier-dashboard.html', web_shell('carrier','web-09-carrier-dashboard.html','工作台',
        '盛达物流有限公司 · 物流公司 · 认证通过', c,
        right='<span style="font-size:13px;color:var(--text-2)">盛达物流有限公司</span>'))

    # ---------- 企业认证 ----------
    b = ('<div class="notice notice-info">' + ico('shield') + '<div>认证状态：' + pill('审核通过')
      + '。资料只读；重要信息变更需触发重新认证。</div></div><div style="height:20px"></div>'
      + panel('企业基本信息', kv([
        ('认证状态',pill('审核通过')),('企业名称','盛达物流有限公司'),('统一社会信用代码','91310114MA1K8XXXXX'),
        ('法定代表人','周明'),('注册资本','500 万元'),('成立日期','2012-03-15'),
        ('注册地址','上海市嘉定区嘉唐公路 66 号'),('联系人 / 电话','周敏 / 13600136000'),
        ('经营范围','道路普通货物运输；大型物件运输'),
        ('营业执照','营业执照_盛达物流.pdf'),('道路运输经营许可证','道路运输经营许可证.pdf')]))
      + panel('认证记录', '<div class="timeline">'
        + '<div class="tl-item done"><div class="tl-title">审核通过</div><div class="tl-meta">2026-09-12 10:02 · 管理员</div></div>'
        + '<div class="tl-item done"><div class="tl-title">提交企业认证资料</div><div class="tl-meta">2026-09-10 16:30 · 物流公司</div></div></div>'))
    save('web-10-carrier-certification.html', web_shell('carrier','web-10-carrier-certification.html','企业认证',
        '企业资料与资质只读展示', b))

    # ---------- 订单池（货源） ----------
    c = page_head('订单池','货源为待承接运输订单的视图 · V1 先到先得，无竞价',
        '<button class="btn btn-text" onclick="toast(\'已刷新货源列表\')">' + ico('clock','icon-sm') + '刷新</button>')
    c += filters([('发货地',inp('请输入发货地')),('收货地',inp('请输入收货地')),
                  ('货物类型',sel(['钢材','建材','机电设备','化工品','冷链食品'])),('车型',sel(['平板车','厢式货车','高栏车'])),
                  ('重量（吨）',inp('最小 ～ 最大')),('发布时间',inp('开始日期 ～ 结束日期')),
                  ('运费区间',inp('最低 ～ 最高'))])
    rows = [
      ['ORDER-251117-0003','机电设备 · 6 件<br><span class="cell-sub">6.5 m³</span>','上海松江','江苏苏州',pill('平板车 / 6.8 米'),'¥ 6,800.00','2026-11-17 10:05',ops('查看货源','承接')],
      ['ORDER-251119-0009','冷轧钢板 · 24 吨','上海青浦','浙江宁波',pill('平板车 / 9.6 米'),'¥ 9,600.00','2026-11-19 13:22',ops('查看货源','承接')],
      ['ORDER-251120-0015','建材辅料 · 15 吨','上海嘉定','江苏常州',pill('高栏车 / 6.8 米'),'¥ 4,200.00','2026-11-20 08:46',ops('查看货源','承接')],
      ['ORDER-251120-0017','冷链食品 · 8 吨','上海松江','浙江杭州',pill('厢式货车 / 4.2 米 · 冷链'),'¥ 7,500.00','2026-11-20 11:30',ops('查看货源','承接')],
    ]
    c += panel('可承接货源', table(['#订单编号','货物','发货地','收货地','车辆要求','#运费报价','发布时间','操作'], rows), tight=True)
    # 详情抽屉
    body = ('<h3 style="margin:0 0 12px;font-size:15px">货源详情 · ORDER-251117-0003</h3>'
      + kv([('订单状态',pill('待承接')),('货物','机电设备 · 6 件 · 6.5 m³'),
            ('发货快照','上海松江中转仓 · 上海市松江区新桥镇新格路 210 号 · 王芳 13700137000'),
            ('收货快照','江苏苏州工业园区星湖街 218 号 · 李工 13650000000'),
            ('运输要求','平板车 / 6.8 米 / 载重 8 吨 · 防雨、特殊装卸'),
            ('运费报价','¥ 6,800.00（固定价，接受议价标记：否）'),
            ('发布时间','2026-11-17 10:05'),('备注','精密设备，需捆扎固定')])
      + '<div style="margin-top:14px"><span style="font-size:13px;color:var(--text-3)">货物照片</span><div class="photos">'
      + ''.join(f'<div class="photo">{ico("cam")}现场图 {i}</div>' for i in [1,2]) + '</div></div>'
      + '<div class="notice notice-info" style="margin-top:16px">' + ico('check')
      + '<div>承接前请确认：具备对应运力、有可用司机与车辆、时间可满足要求，并接受当前运费报价。</div></div>')
    c += drawer('poolDrawer','货源详情', body,
        '<button class="btn btn-secondary" data-act="close">关闭</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'承接成功，订单已进入我的订单待派单\')">确认承接</button>')
    c = c.replace("ops('查看货源','承接')", "ops('查看货源','承接')")
    c = c.replace('<button class="btn btn-text" onclick="toast(\'原型演示：查看货源\')">查看货源</button>',
                  '<button class="btn btn-text" onclick="openDrawer(\'poolDrawer\')">查看货源</button>')
    save('web-11-order-pool.html', web_shell('carrier','web-11-order-pool.html','订单池',
        '当前可承接货源 4 条 · 先到先得', c))

    # ---------- 派单管理 ----------
    c = page_head('派单管理','创建运输任务 · 系统校验司机车辆归属、可用性与时间冲突',
        '<button class="btn btn-primary" onclick="openDrawer(\"dispatchDrawer\")">' + ico('plus','icon-sm') + '新建派单</button>')
    c += filters([('订单编号',inp('请输入编号')),('货主',inp('请输入货主名称')),
                  ('发货地',inp('请输入')),('收货地',inp('请输入')),('承接时间',inp('开始日期 ～ 结束日期'))])
    c += panel('待派单运输订单', table(['#订单编号','货主 / 货物','发货地 → 收货地','计划装货','承接时间','操作'], [
      ['ORDER-251118-0007','华远建材有限公司<br>水泥 · 80 吨','上海嘉定 → 浙江嘉兴','2026-11-22 08:00','2026-11-18 15:02',ops('派单','查看详情')],
      ['ORDER-251117-0003','华远建材有限公司<br>机电设备 · 6 件','上海松江 → 江苏苏州','2026-11-23 09:00','2026-11-17 16:40',ops('派单','查看详情')],
      ['ORDER-251119-0009','宏基物资有限公司<br>冷轧钢板 · 24 吨','上海青浦 → 浙江宁波','2026-11-24 07:30','2026-11-19 14:10',ops('派单','查看详情')],
    ]))
    c += panel('已派单任务', table(['#任务编号','订单 / 货物','司机 / 车辆','任务状态','计划装货','操作'], [
      ['TASK-251118-0002','ORDER-251118-0007 · 水泥','李海涛 / 沪B·3D772',pill('待司机确认'),'2026-11-22 08:00',ops('查看详情','撤回改派')],
      ['TASK-251117-0006','ORDER-251117-0003 · 机电设备','赵强 / 沪A·5K108',pill('待装货'),'2026-11-23 09:00',ops('查看详情','撤回改派')],
    ]))
    db = ('<div class="notice notice-info" style="margin-bottom:16px">' + ico('shield')
      + '<div>派单校验：司机与车辆均须属于本公司且可用、司机具备准驾资格、车辆满足运输要求，且计划时段无冲突。</div></div>'
      + '<div class="field"><label class="field-label"><span class="req">*</span>运输订单</label>'
      + sel(['ORDER-251118-0007 · 水泥 80 吨','ORDER-251117-0003 · 机电设备 6 件']) + '</div>'
      + '<div class="field"><label class="field-label"><span class="req">*</span>司机</label>'
      + sel(['李海涛 · 可派单 · 在职 · 沪B·3D772','赵强 · 可派单 · 在职 · 沪A·5K108','王建国 · 任务占用中']) + '</div>'
      + '<div class="field"><label class="field-label"><span class="req">*</span>车辆</label>'
      + sel(['沪B·3D772 · 可用 · 在册','沪A·5K108 · 可用 · 在册','苏E·7M220 · 占用中']) + '</div>'
      + '<div class="form-grid"><div class="field"><label class="field-label"><span class="req">*</span>计划装货时间</label>' + inp('','2026-11-22 08:00') + '</div>'
      + '<div class="field"><label class="field-label"><span class="req">*</span>计划送达时间</label>' + inp('','2026-11-23 18:00') + '</div></div>'
      + '<div class="field"><label class="field-label">派单备注</label><textarea class="textarea" placeholder="选填，司机端可见"></textarea></div>')
    c += drawer('dispatchDrawer','新建派单', db,
        '<button class="btn btn-secondary" data-act="close">取消</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'派单已创建，等待司机确认\')">确认派单</button>')
    save('web-12-dispatch.html', web_shell('carrier','web-12-dispatch.html','派单管理',
        '待派单 3 · 已派单 2', c))

    # ---------- 司机管理 ----------
    c = page_head('司机管理','司机账号由物流公司创建，司机不可自行注册',
        '<button class="btn btn-primary" onclick="openDrawer(\"driverDrawer\")">' + ico('plus','icon-sm') + '新增司机</button>')
    c += filters([('姓名',inp('请输入姓名')),('认证状态',sel(['未提交','待审核','审核通过','审核不通过'])),
                  ('接单可用性',sel(['可派单','任务占用中','暂停接单'])),('雇佣关系',sel(['在职','离职'])),
                  ('手机号',inp('请输入手机号'))])
    c += panel('司机列表', table(['#姓名','手机号','认证状态','接单可用性','雇佣关系','当前车辆 / 任务','操作'], [
      ['王建国','13810010001',pill('审核通过'),pill('任务占用中'),pill('在职'),'沪A·8F231 / TASK-251120-0003',ops('编辑','查看详情')],
      ['李海涛','13810010002',pill('审核通过'),pill('可派单'),pill('在职'),'沪B·3D772 / —',ops('编辑','暂停接单')],
      ['赵 强','13810010003',pill('审核通过'),pill('可派单'),pill('在职'),'沪A·5K108 / TASK-251117-0006',ops('编辑','查看详情')],
      ['孙 伟','13810010004',pill('审核通过'),pill('暂停接单'),pill('在职'),'苏E·7M220 / —',ops('编辑','恢复接单')],
      ['刘志强','13810010005',pill('待审核'),pill('可派单'),pill('在职'),'— / —',ops('编辑','查看详情')],
      ['陈 明','13810010006',pill('审核通过'),pill('可派单'),pill('离职'),'— / —',ops('查看详情')],
    ]), tight=True)
    dd = ('<div class="notice notice-info" style="margin-bottom:16px">' + ico('shield')
      + '<div>账号状态、认证状态、接单可用性与雇佣关系为相互独立的四个维度，分开呈现。</div></div>'
      + kv([('姓名',inp('请输入姓名')),('手机号',inp('请输入手机号')),('临时密码',inp('系统生成，首次登录强制修改')),
            ('身份证号',inp('请输入')),('准驾车型',sel(['A1','A2','B2','C1'])),('驾驶证号',inp('请输入'))])
      + '<div class="field" style="margin-top:16px"><label class="field-label">初始状态</label><div class="radio-row">'
      + '<label><input type="radio" name="drvst" checked>可派单</label><label><input type="radio" name="drvst">暂停接单</label></div></div>')
    c += drawer('driverDrawer','新增司机', dd,
        '<button class="btn btn-secondary" data-act="close">取消</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'司机账号已创建，待司机首次登录完成身份绑定\')">创建账号</button>')
    save('web-15-drivers.html', web_shell('carrier','web-15-drivers.html','司机管理',
        '在册司机 14 人 · 可派单 8 / 任务占用 4 / 暂停接单 2', c))

    # ---------- 车辆管理 ----------
    c = page_head('车辆管理','可用性与生命周期为两个独立维度；维修中或已停用车辆不可派单',
        '<button class="btn btn-primary" onclick="openDrawer(\"vehDrawer\")">' + ico('plus','icon-sm') + '登记车辆</button>')
    c += filters([('车牌号',inp('请输入车牌')),('车辆类型',sel(['平板车','厢式货车','高栏车','自卸车'])),
                  ('可用性',sel(['可用','占用中','暂停使用'])),('生命周期',sel(['在册','维修中','已停用'])),
                  ('归属',sel(['公司自有','司机自带']))])
    c += panel('车辆列表', table(['#车牌号','类型 / 车长','最大载重','归属 / 实际车主','当前司机','可用性','生命周期','操作'], [
      ['沪A·8F231','平板车 / 13 米','35 吨','公司自有','王建国',pill('占用中'),pill('在册'),ops('编辑','查看详情')],
      ['沪B·3D772','高栏车 / 6.8 米','12 吨','司机自带 / 李海涛','李海涛',pill('可用'),pill('在册'),ops('编辑','查看详情')],
      ['沪A·5K108','平板车 / 6.8 米','10 吨','公司自有','赵强',pill('占用中'),pill('在册'),ops('编辑','查看详情')],
      ['苏E·7M220','厢式货车 / 4.2 米','5 吨','公司自有','孙伟',pill('暂停使用'),pill('维修中'),ops('编辑','查看详情')],
      ['沪C·9T556','自卸车 / 9.6 米','25 吨','司机自带 / 周斌','—',pill('可用'),pill('在册'),ops('编辑','查看详情')],
    ]), tight=True)
    vd = ('<div class="field"><label class="field-label"><span class="req">*</span>车牌号</label>' + inp('请输入车牌号') + '</div>'
      + '<div class="form-grid"><div class="field"><label class="field-label"><span class="req">*</span>车辆类型</label>' + sel(['平板车','厢式货车','高栏车','自卸车']) + '</div>'
      + '<div class="field"><label class="field-label">车长</label>' + sel(['4.2 米','6.8 米','9.6 米','13 米']) + '</div></div>'
      + '<div class="field"><label class="field-label">最大载重（吨）</label>' + inp('请输入') + '</div>'
      + '<div class="field"><label class="field-label">归属</label><div class="radio-row">'
      + '<label><input type="radio" name="own" checked>公司自有</label><label><input type="radio" name="own">司机自带</label></div></div>'
      + '<div class="notice notice-info" style="margin-top:12px">' + ico('warn')
      + '<div>车辆转籍由平台管理员执行，且仅限无进行中任务的车辆。</div></div>')
    c += drawer('vehDrawer','登记车辆', vd,
        '<button class="btn btn-secondary" data-act="close">取消</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'车辆已登记，状态为可用 / 在册\')">保存</button>')
    save('web-16-vehicles.html', web_shell('carrier','web-16-vehicles.html','车辆管理',
        '在册车辆 9 台 · 可用 5 / 占用 3 / 暂停使用 1', c))

    # ---------- 费用审核 ----------
    c = page_head('费用审核','报销费用由司机按运输任务提交 · 单条处理，非批量',
        '<button class="btn btn-text" onclick="toast(\'已刷新待审列表\')">' + ico('clock','icon-sm') + '刷新</button>')
    c += filters([('司机',inp('请输入司机姓名')),('任务编号',inp('请输入任务编号')),
                  ('费用类型',sel(['油费','过路费','停车费','维修','其它'])),('提交时间',inp('开始日期 ～ 结束日期')),
                  ('审核状态',sel(['待审核','审核通过','审核不通过'])),('支付状态',sel(['待支付','已支付']))])
    c += panel('报销费用列表', table(['#费用编号','司机 / 任务','费用类型','#金额','提交时间','审核状态','支付状态','操作'], [
      ['EXP-251120-0007','王建国 / TASK-251120-0003','油费','¥ 860.00','2026-11-21 19:20',pill('待审核'),pill('待支付'),ops('审核','查看详情')],
      ['EXP-251119-0005','李海涛 / TASK-251119-0002','过路费','¥ 320.00','2026-11-20 08:12',pill('待审核'),pill('待支付'),ops('审核','查看详情')],
      ['EXP-251117-0003','赵强 / TASK-251117-0006','停车费','¥ 60.00','2026-11-18 17:40',pill('审核通过'),pill('待支付'),ops('标记已支付')],
      ['EXP-251116-0002','孙伟 / TASK-251116-0004','维修','¥ 1,280.00','2026-11-17 10:05',pill('审核不通过'),pill('待支付'),ops('查看原因')],
    ]), tight=True)
    ed = ('<div class="notice notice-info" style="margin-bottom:16px">' + ico('money')
      + '<div>审核状态与支付状态相互独立：审核通过不代表已支付；线下支付后由本公司单条标记「已支付」并记录操作人与时间。</div></div>'
      + kv([('费用编号','EXP-251120-0007'),('司机','王建国'),('关联任务','TASK-251120-0003'),
            ('费用类型','油费'),('金额','¥ 860.00'),('提交时间','2026-11-21 19:20'),
            ('费用说明','青浦至昆山全程加油，附发票'),('凭证','加油发票_251121.pdf')])
      + '<div class="field" style="margin-top:16px"><label class="field-label">驳回原因（驳回时必填）</label>'
      + '<textarea class="textarea" id="expRejectReason" placeholder="请说明驳回原因，将追加到费用记录"></textarea>'
      + '<div class="help err" id="expRejectReasonTip" style="display:none">驳回原因为必填项。</div></div>')
    c += drawer('expDrawer','费用审核 · EXP-251120-0007', ed,
        '<button class="btn btn-secondary" data-act="close">关闭</button>'
        '<button class="btn btn-danger" onclick="submitReject(\'expRejectReason\',\'报销费用已驳回\')">驳回</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'审核通过，支付状态仍为待支付\')">审核通过</button>')
    md = modal('paidModal','标记已支付',
        '确认已在线下完成支付？提交后将记录操作人与操作时间，支付状态变为「已支付」。',
        '<button class="btn btn-secondary" onclick="closeModal()">取消</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'已标记支付：操作人 周敏 · 时间 2026-11-22 10:15\')">确认已支付</button>')
    c += drawer('paidDrawer', '费用详情 · EXP-251117-0003',
        kv([('费用编号','EXP-251117-0003'),('金额','¥ 60.00'),('审核状态',pill('审核通过')),('支付状态',pill('待支付'))]),
        '<button class="btn btn-secondary" data-act="close">关闭</button>'
        '<button class="btn btn-primary" onclick="openModal(\'paidModal\')">标记已支付</button>')
    c = c.replace('<button class="btn btn-text" onclick="toast(\'原型演示：审核\')">审核</button>',
                  '<button class="btn btn-text" onclick="openDrawer(\'expDrawer\')">审核</button>')
    c = c.replace('<button class="btn btn-text" onclick="toast(\'原型演示：标记已支付\')">标记已支付</button>',
                  '<button class="btn btn-text" onclick="openDrawer(\'paidDrawer\')">标记已支付</button>')
    c += md
    save('web-17-expenses.html', web_shell('carrier','web-17-expenses.html','费用审核',
        '待审核 2 · 审核通过 8 · 审核不通过 1', c))

    # ---------- 运输异常 ----------
    c = page_head('运输异常','异常上报与处置 · 结果追加为异常处理记录，不覆盖原始记录',
        '<button class="btn btn-primary" onclick="openDrawer(\"exDrawer\")">' + ico('plus','icon-sm') + '上报异常</button>')
    c += filters([('异常类型',sel(['车辆故障','事故','封路','拥堵','货物问题','预计延误','位置异常','其它'])),
                  ('上报人',inp('请输入')),('运输任务',inp('请输入任务编号')),('时间',inp('开始日期 ～ 结束日期'))])
    c += panel('异常列表', table(['#异常编号','异常类型 / 任务','上报人','上报时间','现场照片','处理结果','操作'], [
      ['EXC-251120-0002','车辆故障<br><span class="cell-sub">TASK-251120-0003</span>','王建国','2026-11-21 10:14','2 张','—',ops('处置','查看详情')],
      ['EXC-251116-0001','货物问题<br><span class="cell-sub">TASK-251116-0004</span>','孙伟','2026-11-16 12:40','3 张','更换车辆',ops('查看详情')],
      ['EXC-251112-0004','预计延误','赵强','2026-11-12 15:22','1 张','调整送达时间',ops('查看详情')],
    ]), tight=True)
    exd = ('<div class="notice notice-warning" style="margin-bottom:16px">' + ico('warn')
      + '<div>异常类型：车辆故障 · 上报人：司机 王建国 · 上报时间：2026-11-21 10:14 · 任务：TASK-251120-0003</div></div>'
      + kv([('异常说明','运输途中发动机故障灯亮起，已靠边停车'),('现场照片','2 张'),('当前任务状态',pill('运输中'))])
      + '<div class="field" style="margin-top:16px"><label class="field-label"><span class="req">*</span>处理结果</label>'
      + sel(['继续运输','调整送达时间','更换车辆','更换司机','重新安排运输','终止运输']) + '</div>'
      + '<div class="field"><label class="field-label">处理说明</label><textarea class="textarea" placeholder="选填；终止运输必须填写原因"></textarea></div>')
    c += drawer('exDrawer','异常处置 · EXC-251120-0002', exd,
        '<button class="btn btn-secondary" data-act="close">关闭</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'处置结果已追加，运输订单保持运输中\')">提交处置</button>')
    save('web-13-exceptions.html', web_shell('carrier','web-13-exceptions.html','运输异常',
        '待处置 1 · 本月异常 3 条', c))

    # ---------- 取消申请处理 ----------
    c = page_head('取消申请处理','货主对已承接未起运订单提交的取消申请 · 需给出处理结果',
        '<button class="btn btn-primary" onclick="openDrawer(\"caDrawer\")">处理申请</button>')
    c += filters([('订单编号',inp('请输入')),('货主',inp('请输入')),('申请时间',inp('开始日期 ～ 结束日期'))])
    c += panel('取消申请列表', table(['#订单编号','货主 / 货物','申请原因','订单状态','申请时间','操作'], [
      ['ORDER-251116-0011','华远建材有限公司<br>冷轧卷板 · 18 吨','客户临时调整施工计划','取消处理中','2026-11-16 16:25',ops('审核','查看详情')],
      ['ORDER-251114-0008','宏基物资有限公司<br>螺纹钢 · 20 吨','货源信息填写有误','已取消','2026-11-14 09:40',ops('查看详情')],
      ['ORDER-251110-0005','远东实业有限公司<br>镀锌板 · 9 吨','报价高于预算','已取消','2026-11-10 13:58',ops('查看详情')],
    ]), tight=True)
    cad = ('<div class="notice notice-warning" style="margin-bottom:16px">' + ico('warn')
      + '<div>申请通过后订单变为「已取消」；驳回后恢复申请前状态，驳回原因作为追加记录展示给货主。</div></div>'
      + kv([('订单编号','ORDER-251116-0011'),('货主','华远建材有限公司'),('货物','冷轧卷板 · 18 吨'),
            ('申请原因','客户临时调整施工计划'),('申请时间','2026-11-16 16:25'),('当前状态',pill('取消处理中'))])
      + '<div class="field" style="margin-top:16px"><label class="field-label">驳回原因（驳回时必填）</label>'
      + '<textarea class="textarea" id="caReason" placeholder="请说明驳回原因"></textarea>'
      + '<div class="help err" id="caReasonTip" style="display:none">驳回原因为必填项。</div></div>')
    c += drawer('caDrawer','取消申请审核', cad,
        '<button class="btn btn-secondary" data-act="close">关闭</button>'
        '<button class="btn btn-danger" onclick="submitReject(\'caReason\',\'已驳回取消申请，订单恢复原状态\')">驳回申请</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'已同意取消，订单变为已取消\')">同意取消</button>')
    c = c.replace('<button class="btn btn-text" onclick="toast(\'原型演示：审核\')">审核</button>',
                  '<button class="btn btn-text" onclick="openDrawer(\'caDrawer\')">审核</button>')
    save('web-14-cancel-applications.html', web_shell('carrier','web-14-cancel-applications.html','取消申请处理',
        '待处理 1 · 已处理 2', c))

    # ---------- 任务进度 ----------
    c = page_head('任务进度','TASK-251120-0003 · 进行中任务与关键节点打卡',
        '<a class="btn btn-secondary" href="web-18-task-progress.html">刷新</a>')
    c += panel('任务基本信息', kv([
      ('任务编号','TASK-251120-0003'),('关联订单','ORDER-251120-0012'),('任务状态',pill('运输中')),
      ('司机 / 车辆','王建国 / 沪A·8F231'),('计划装货','2026-11-21 08:00'),('计划送达','2026-11-22 18:00'),
      ('运输要求','平板车 / 13 米 / 35 吨 · 防雨')]))
    c += panel('执行节点', '<div class="timeline">'
      + '<div class="tl-item done"><div class="tl-title">起运 · 装货确认</div><div class="tl-meta">2026-11-21 08:32 · 王建国</div>'
      + '<div class="tl-desc">装前 / 装中 / 装后照片齐全，司机已确认货物与车辆</div></div>'
      + '<div class="tl-item done"><div class="tl-title">发货地打卡</div><div class="tl-meta">2026-11-21 07:58 · 距离快照 120 米</div></div>'
      + '<div class="tl-item done"><div class="tl-title">司机确认接单</div><div class="tl-meta">2026-11-20 16:18</div></div>'
      + '<div class="tl-item"><div class="tl-title">到达收货地打卡</div><div class="tl-meta">待执行</div></div>'
      + '<div class="tl-item"><div class="tl-title">签收与凭证</div><div class="tl-meta">待执行</div></div>'
      + '</div>', hint='可查看司机提交的打卡与现场照片')
    c += panel('关联报销费用', table(['#费用编号','类型','#金额','审核状态','支付状态','提交时间'], [
      ['EXP-251120-0007','油费','¥ 860.00',pill('待审核'),pill('待支付'),'2026-11-21 19:20'],
    ], paginate=False))
    save('web-18-task-progress.html', web_shell('carrier','web-18-task-progress.html','任务进度',
        'TASK-251120-0003 · 运输中', c))
