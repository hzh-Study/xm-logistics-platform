# -*- coding: utf-8 -*-
"""Web 端：登录 + 货主全套页面"""
from common import *

def build():
    # ---------- 登录 ----------
    c = head('登录 · 物流运输管理平台')
    c += ('<div class="login-page"><div class="login-card">'
      '<div class="login-logo"><span class="brand-mark">运</span><span class="login-title">物流运输管理平台</span></div>'
      '<p class="login-sub">账号登录</p>'
      '<div class="login-hint">开发演示态：账号与密码已预填，直接点击「登录」即可进入对应身份工作台。</div>'
      '<form onsubmit="return false">'
      '<div class="field"><label class="field-label">手机号</label>'
      '<input class="input" value="13800138000" placeholder="请输入手机号"></div>'
      '<div class="field"><div class="pwd-wrap"><input class="input" type="password" value="demo12345" placeholder="请输入密码">'
      '<button type="button" class="pwd-toggle" data-act="pwd" aria-label="显示密码">'
      + ico('eye','icon-sm') + '</button></div></div>'
      '<button class="btn btn-primary btn-block" onclick="toast(\'登录成功，正在进入工作台\')">登录</button>'
      '</form>'
      '<div class="login-foot"><button class="btn btn-text" id="registerToggle" onclick="toggleRegister()">注册新账号</button></div>'
      '<div class="register-zone" id="registerZone">'
      '<p class="panel-hint" style="margin:0 0 12px">选择主体类型后填写资料，注册通过后进入对应工作台。</p>'
      '<div class="field"><label class="field-label">主体类型</label><div class="radio-row">'
      '<label><input type="radio" name="regtype" checked>货主</label>'
      '<label><input type="radio" name="regtype">物流公司</label></div></div>'
      '<div class="field"><label class="field-label"><span class="req">*</span>手机号</label>' + inp('请输入手机号') + '</div>'
      '<div class="field"><label class="field-label"><span class="req">*</span>密码</label>' + inp('至少 8 位', '', 'password')
      + '<div class="help">密码不少于 8 位，建议使用字母与数字组合。</div></div>'
      '<div class="field" id="regCompany" style="display:none"><label class="field-label"><span class="req">*</span>企业名称</label>'
      + inp('请输入营业执照上的企业名称') + '</div>'
      '<button class="btn btn-primary btn-block" onclick="toast(\'注册成功，请完成认证\')">注册并进入</button>'
      '</div></div></div>')
    # 注册时显示企业名（物流公司）
    c += ('<script>document.addEventListener("change",function(e){if(e.target&&e.target.name==="regtype"){'
          'document.getElementById("regCompany").style.display=e.target.value==="物流公司"?"block":"none";'
          '}});</script>')
    #  radio value 修正
    c = c.replace('<input type="radio" name="regtype">物流公司', '<input type="radio" name="regtype" value="物流公司">物流公司')
    c = c.replace('<input type="radio" name="regtype" checked>货主', '<input type="radio" name="regtype" value="货主" checked>货主')
    c += foot()
    save('web-01-login.html', c)

    # ---------- 货主工作台 ----------
    content = stats([('3','仓库数'),('18','订单总数'),('4','待承接'),('2','已承接'),
                     ('5','运输中'),('6','已完成'),('1','已取消')])
    content += '<div style="height:16px"></div>'
    content += ('<div class="notice notice-info">' + ico('shield')
      + '<div>当前认证状态：' + pill('审核通过') + '。认证已通过，可发布运输订单。<a href="web-03-shipper-certification.html">查看认证信息</a></div></div>')
    content += '<div style="height:16px"></div>'
    content += panel('最近运输订单',
        table(['#编号','货物','发货地 → 收货地','订单状态','发布时间','操作'], [
          ['ORDER-251120-0012<br><span class="cell-sub">华远建材有限公司</span>','热轧钢板 · 32 吨','上海青浦 → 江苏昆山',pill('运输中'),'2026-11-20 09:12',ops('查看进度','查看详情')],
          ['ORDER-251118-0007','水泥 · 80 吨','上海嘉定 → 浙江嘉兴',pill('已承接'),'2026-11-18 14:30',ops('查看','取消申请')],
          ['ORDER-251117-0003','机电设备 · 6 件','上海松江 → 江苏苏州',pill('待承接'),'2026-11-17 10:05',ops('查看')],
          ['ORDER-251112-0019','冷轧卷板 · 18 吨','上海青浦 → 安徽马鞍山',pill('已完成'),'2026-11-12 08:40',ops('查看')],
        ], paginate=False),
        hint='<a href="web-06-shipper-orders.html" style="color:var(--brand)">查看全部</a>')
    content += panel('系统通知', notices([
        ('ORDER-251120-0012 已起运，当前运输中','2026-11-21 08:32'),
        ('ORDER-251118-0007 已被盛达物流有限公司承接','2026-11-18 15:02'),
        ('货主认证审核通过','2026-11-10 11:20')]), tight=False)
    content += panel('快捷入口',
        '<div style="display:flex;gap:8px;flex-wrap:wrap">'
        '<a class="btn btn-secondary" href="web-04-shipper-warehouses.html">' + ico('box','icon-sm') + '仓库管理</a>'
        '<a class="btn btn-secondary" href="web-05-shipper-order-new.html">' + ico('plus','icon-sm') + '发布运输订单</a>'
        '<a class="btn btn-secondary" href="web-06-shipper-orders.html">' + ico('doc','icon-sm') + '我的订单</a></div>')
    save('web-02-shipper-dashboard.html', web_shell('shipper','web-02-shipper-dashboard.html','工作台',
        '华远建材有限公司 · 货主 · ' + pill('审核通过'), content,
        right='<span style="font-size:13px;color:var(--text-2)">华远建材有限公司</span>'))

    # ---------- 货主认证 ----------
    body = (f'<div class="notice notice-info">{ico("shield")}<div>认证状态：{pill("审核通过")}。'
      '审核通过后资料不可自行修改；如需变更，请联系平台管理员。</div></div><div style="height:20px"></div>'
      + '<div class="panel"><div class="panel-head"><span class="panel-title">企业基本信息</span>'
      + '<button class="btn btn-secondary btn-sm" onclick="toast(\'认证通过后资料只读\')">查看历史</button></div>'
      + '<div class="panel-body">' + kv([
        ('认证类型','企业'),('企业名称','华远建材有限公司'),('统一社会信用代码','91310118MA1K3XXXXX'),
        ('法定代表人','陈建国'),('成立日期','2015-06-18'),('注册地址','上海市青浦区华新镇华志路 128 号'),
        ('联系人 / 电话','陈静 / 13800138000'),('营业执照','营业执照_华远建材.pdf')]) + '</div></div>'
      + '<div class="panel"><div class="panel-head"><span class="panel-title">认证记录</span></div>'
      + '<div class="panel-body"><div class="timeline">'
      + '<div class="tl-item done"><div class="tl-title">审核通过</div><div class="tl-meta">2026-11-10 11:20 · 管理员</div></div>'
      + '<div class="tl-item done"><div class="tl-title">提交认证资料</div><div class="tl-meta">2026-11-08 09:42 · 货主</div></div>'
      + '<div class="tl-item done"><div class="tl-title">未提交</div><div class="tl-meta">2026-11-05 注册完成</div></div>'
      + '</div></div></div>')
    save('web-03-shipper-certification.html', web_shell('shipper','web-03-shipper-certification.html','货主认证',
        '认证信息只读展示，业务记录追加式不可改写', body))

    # ---------- 仓库管理 ----------
    content = page_head('仓库管理','发货地点主数据，可停用或删除；已固化在订单上的发货快照不受影响',
        '<button class="btn btn-primary" onclick="toast(\'打开新增仓库表单\')">' + ico('plus','icon-sm') + '新增仓库</button>')
    content += filters([('仓库名称',inp('请输入仓库名称')),('所在地区',sel(['上海市','江苏省','浙江省'])),
                        ('仓库类型',sel(['自有仓','租用仓','第三方仓'])),('状态',sel(['启用','停用']))])
    content += panel('仓库列表',
        table(['#仓库名称','所在地区','详细地址','联系人 / 电话','类型','状态','操作'], [
          ['上海青浦钢材仓<br><span class="cell-sub">默认发货仓</span>','上海市 / 青浦区','华新镇华志路 128 号','陈静 / 13800138000','自有仓','<span class="pill pill--success">启用</span>',ops('编辑','停用')],
          ['嘉定原料仓','上海市 / 嘉定区','嘉定工业区嘉唐公路 66 号','刘伟 / 13900139000','租用仓','<span class="pill pill--success">启用</span>',ops('编辑','停用')],
          ['松江中转仓','上海市 / 松江区','新桥镇新格路 210 号','王芳 / 13700137000','第三方仓','<span class="pill">停用</span>',ops('编辑','启用')],
        ]), tight=True)
    save('web-04-shipper-warehouses.html', web_shell('shipper','web-04-shipper-warehouses.html','仓库管理',
        '共 3 个仓库', content))

    # ---------- 发布运输订单 ----------
    sections = ''
    sections += '<section class="panel"><div class="panel-body"><h2 class="form-section-title">货物信息</h2><div class="form-grid">'
    sections += '<div class="field"><label class="field-label"><span class="req">*</span>货物名称</label>' + inp('如：热轧钢板') + '</div>'
    sections += '<div class="field"><label class="field-label"><span class="req">*</span>货物类型</label>' + sel(['钢材','建材','机电设备','化工品','冷链食品','其他']) + '</div>'
    sections += '<div class="field"><label class="field-label"><span class="req">*</span>数量</label>' + inp('请输入数量') + '</div>'
    sections += '<div class="field"><label class="field-label"><span class="req">*</span>重量（吨）</label>' + inp('请输入重量') + '</div>'
    sections += '<div class="field"><label class="field-label">体积（m³）</label>' + inp('选填') + '</div>'
    sections += '<div class="field"><label class="field-label">包装</label>' + sel(['裸装','木箱','托盘','编织袋','其他']) + '</div>'
    sections += '</div><div class="field"><label class="field-label">货物照片</label>'
    sections += '<div class="photos"><div class="photo">' + ico('cam') + '添加照片</div></div>'
    sections += '<div class="field" style="margin-top:16px"><label class="field-label">备注</label>' + '<textarea class="textarea" placeholder="特殊装载要求、注意事项等"></textarea></div>'
    sections += '</div></div></section>'

    sections += '<section class="panel"><div class="panel-body"><h2 class="form-section-title">发货信息（发货快照）</h2>'
    sections += '<div class="field"><label class="field-label"><span class="req">*</span>发货方式</label><select class="select" id="shipFrom"><option>选择已有仓库</option><option>临时地址</option></select></div>'
    sections += '<div class="field"><label class="field-label"><span class="req">*</span>发货仓库</label>' + sel(['上海青浦钢材仓','嘉定原料仓']) + '</div>'
    sections += '<div id="tempAddressBox" style="display:none"><div class="field"><label class="field-label"><span class="req">*</span>临时发货地址</label>' + inp('请输入详细地址') + '</div></div>'
    sections += '<div class="readonly-box">发布时固化以下信息为 <b>发货快照</b>，后续仓库改名、停用或删除均不回写：上海青浦钢材仓 · 上海市青浦区华新镇华志路 128 号 · 陈静 13800138000</div>'
    sections += '</div></section>'

    sections += '<section class="panel"><div class="panel-body"><h2 class="form-section-title">收货信息（收货快照）</h2><div class="form-grid">'
    sections += '<div class="field"><label class="field-label"><span class="req">*</span>收货联系人</label>' + inp('请输入姓名') + '</div>'
    sections += '<div class="field"><label class="field-label"><span class="req">*</span>收货电话</label>' + inp('请输入手机号') + '</div>'
    sections += '<div class="field"><label class="field-label"><span class="req">*</span>收货地址</label>' + inp('省 / 市 / 区 / 详细地址') + '</div>'
    sections += '<div class="field"><label class="field-label">预计送达时间</label>' + inp('', '2026-11-25 18:00', 'text') + '</div>'
    sections += '</div></div></section>'

    sections += '<section class="panel"><div class="panel-body"><h2 class="form-section-title">运输要求</h2><div class="form-grid cols-3">'
    sections += '<div class="field"><label class="field-label">车型</label>' + sel(['平板车','厢式货车','高栏车','自卸车']) + '</div>'
    sections += '<div class="field"><label class="field-label">车长</label>' + sel(['4.2 米','6.8 米','9.6 米','13 米']) + '</div>'
    sections += '<div class="field"><label class="field-label">载重要求（吨）</label>' + inp('请输入') + '</div>'
    sections += '</div><div class="field"><label class="field-label">特殊要求</label><div class="check-row">'
    for x in ['冷链','防雨','封闭式车厢','特殊装卸','需要叉车']:
        sections += f'<label><input type="checkbox">{x}</label>'
    sections += '</div></div></div></section>'

    sections += '<section class="panel"><div class="panel-body"><h2 class="form-section-title">运费报价</h2>'
    sections += '<div class="notice notice-info" style="margin-bottom:16px">' + ico('money')
    sections += '<div>运费报价仅货主与物流公司可见，司机端不会展示该字段，也不构成双方结算。</div></div>'
    sections += '<div class="form-grid"><div class="field"><label class="field-label"><span class="req">*</span>报价方式</label>'
    sections += '<select class="select" id="quoteMethod"><option>固定价</option><option>可议</option><option>其它</option></select></div>'
    sections += '<div class="field"><label class="field-label"><span class="req">*</span>报价金额（元）</label>' + inp('请输入金额') + '</div></div>'
    sections += '<div class="field" id="negotiableBox" style="display:none"><label><input type="checkbox">接受议价标记（在货源列表展示）</label></div>'
    sections += '</div></section>'

    sections += ('<div class="panel"><div class="panel-body"><div class="form-actions">'
      '<button class="btn btn-secondary" onclick="toast(\'已保存草稿\')">保存草稿</button>'
      '<button class="btn btn-primary" onclick="demoValidate(\'orderForm\',\'publishModal\')">发布前确认</button>'
      '</div></div></div>')
    content = web_shell('shipper','web-05-shipper-order-new.html','发布运输订单',
        '发布前需确认全部信息；发货与收货信息将固化为准', sections, right='')
    # 包裹 form id
    content = content.replace('<main class="content">', '<main class="content"><form id="orderForm" onsubmit="return false">')
    content = content.replace('</main></div></div>', '</form></main></div></div>')
    # 增加确认弹层
    confirm = modal('publishModal','确认发布运输订单',
        '<dl class="summary-list"><dt>货物</dt><dd>热轧钢板 · 32 吨 · 钢材</dd>'
        '<dt>发货快照</dt><dd>上海青浦钢材仓 · 上海市青浦区华新镇华志路 128 号</dd>'
        '<dt>收货快照</dt><dd>江苏昆山开发区前进西路 88 号 · 张经理 13900000000</dd>'
        '<dt>运输要求</dt><dd>平板车 / 13 米 / 载重 35 吨 · 防雨</dd>'
        '<dt>运费报价</dt><dd class="num" style="text-align:left">¥ 12,800.00（固定价）</dd></dl>'
        '<p style="margin:14px 0 0;font-size:13px;color:var(--text-3)">发布后进入「待承接」，货源对所有已认证物流公司可见。</p>',
        '<button class="btn btn-secondary" onclick="closeModal()">返回修改</button>'
        '<button class="btn btn-primary" onclick="submitAction(\'发布成功，运输订单进入待承接\')">确认发布</button>')
    content = content.replace('</main></div></div>', confirm + '</main></div></div>')
    save('web-05-shipper-order-new.html', content)

    # ---------- 我的订单 ----------
    content = page_head('我的订单','仅展示当前货主发布的运输订单',
        '<a class="btn btn-primary" href="web-05-shipper-order-new.html">' + ico('plus','icon-sm') + '发布运输订单</a>')
    content += filters([('订单编号',inp('请输入编号')),('订单状态',sel(['待承接','已承接','运输中','已完成','取消处理中','已取消','异常处理中'])),
                        ('发货地',inp('请输入发货地')),('收货地',inp('请输入收货地')),
                        ('货物名称',inp('请输入货物名称')),('发布时间',inp('开始日期 ～ 结束日期'))])
    rows = [
     ['ORDER-251120-0012','热轧钢板 · 32 吨','上海青浦 → 江苏昆山',pill('运输中'),'2026-11-20 09:12',ops('查看进度','查看详情')],
     ['ORDER-251118-0007','水泥 · 80 吨','上海嘉定 → 浙江嘉兴',pill('已承接'),'2026-11-18 14:30',ops('查看详情','申请取消')],
     ['ORDER-251117-0003','机电设备 · 6 件','上海松江 → 江苏苏州',pill('待承接'),'2026-11-17 10:05',ops('查看详情','直接取消')],
     ['ORDER-251116-0011','冷轧卷板 · 18 吨','上海青浦 → 安徽马鞍山',pill('取消处理中'),'2026-11-16 16:20',ops('查看进度','撤销申请')],
     ['ORDER-251115-0004','建材辅料 · 12 吨','上海嘉定 → 江苏无锡',pill('异常处理中'),'2026-11-15 11:08',ops('查看进度')],
     ['ORDER-251112-0019','冷轧卷板 · 18 吨','上海青浦 → 安徽马鞍山',pill('已完成'),'2026-11-12 08:40',ops('查看详情')],
     ['ORDER-251110-0002','镀锌板 · 9 吨','上海松江 → 浙江杭州',pill('已取消'),'2026-11-10 13:55',ops('查看详情')],
    ]
    content += panel('订单列表', table(['#编号','货物','发货地 → 收货地','订单状态','发布时间','操作'], rows), tight=True)
    save('web-06-shipper-orders.html', web_shell('shipper','web-06-shipper-orders.html','我的订单',
        '发布与取消入口 · 全流程状态可追踪', content))

    # ---------- 订单进度 ----------
    content = page_head('订单进度','ORDER-251120-0012 · 运输进度为订单状态投影，司机与打卡记录只读',
        '<a class="btn btn-secondary" href="web-06-shipper-orders.html">返回列表</a>')
    content += panel('订单基本信息', kv([
      ('订单编号','ORDER-251120-0012'),('订单状态',pill('运输中')),('货主','华远建材有限公司'),
      ('承接公司','盛达物流有限公司'),('货物','热轧钢板 · 32 吨 · 钢材'),
      ('发货快照','上海青浦钢材仓 · 上海市青浦区华新镇华志路 128 号 · 陈静 13800138000'),
      ('收货快照','江苏昆山开发区前进西路 88 号 · 张经理 13900000000'),
      ('运费报价','¥ 12,800.00（固定价）'),('发布时间','2026-11-20 09:12')]))
    steps = [('发布',True,'11-20 09:12'),('承接',True,'11-20 14:30'),('派单',True,'11-20 16:05'),
             ('起运',True,'11-21 08:32'),('到达收货地',False,'预计 11-22'),('签收',False,'—'),('完成',False,'—')]
    st = '<div class="stepper">'
    for i,(lab,done,tm) in enumerate(steps):
        cls = 'done' if done else ('current' if i==4 else '')
        st += f'<div class="step {cls}"><div class="step-dot">{"✓" if done else (i+1)}</div><div class="step-label">{lab}</div><div class="step-time">{tm}</div></div>'
    st += '</div>'
    content += panel('运输进度', st, hint='当前节点：到达收货地')
    content += panel('运输过程记录', '<div class="timeline">'
      + '<div class="tl-item done"><div class="tl-title">起运打卡</div><div class="tl-meta">2026-11-21 08:32 · 司机 王建国 · 沪A·8F231</div>'
      + '<div class="tl-desc">定位正常，现场照片 3 张（装前 / 装中 / 装后）</div><div class="photos">'
      + ''.join(f'<div class="photo">{ico("cam")}{x}</div>' for x in ['装前','装中','装后']) + '</div></div>'
      + '<div class="tl-item done"><div class="tl-title">到达发货地打卡</div><div class="tl-meta">2026-11-21 07:58 · 司机 王建国</div>'
      + '<div class="tl-desc">距离发货快照 120 米，定位正常</div></div>'
      + '<div class="tl-item done"><div class="tl-title">司机确认接单</div><div class="tl-meta">2026-11-20 16:18 · 运输任务 TASK-251120-0003</div></div>'
      + '<div class="tl-item done"><div class="tl-title">物流公司派单</div><div class="tl-meta">2026-11-20 16:05 · 派单 DISP-251120-0002</div></div>'
      + '<div class="tl-item done"><div class="tl-title">物流公司承接订单</div><div class="tl-meta">2026-11-20 14:30 · 盛达物流有限公司</div></div>'
      + '</div>', hint='货主只读，不可修改司机提交的打卡与凭证')
    content += panel('关联运输任务', table(['#任务编号','司机 / 车辆','任务状态','计划装货','计划送达','操作'], [
      ['TASK-251120-0003','王建国 / 沪A·8F231',pill('运输中'),'2026-11-21 08:00','2026-11-22 18:00',ops('查看详情')],
    ], paginate=False))
    save('web-07-order-progress.html', web_shell('shipper','web-07-order-progress.html','订单进度',
        'ORDER-251120-0012 · 只读', content))

    # ---------- 订单取消 ----------
    content = page_head('订单取消','ORDER-251118-0007 · 已承接未起运，需提交取消申请等待物流公司确认',
        '<a class="btn btn-secondary" href="web-06-shipper-orders.html">返回列表</a>')
    content += panel('订单摘要', kv([
      ('订单编号','ORDER-251118-0007'),('当前状态',pill('已承接')),('货物','水泥 · 80 吨'),
      ('承接公司','盛达物流有限公司'),('发货快照','上海嘉定原料仓 → 浙江嘉兴'),('承接时间','2026-11-18 15:02')]))
    content += '<section class="panel"><div class="panel-body"><h2 class="form-section-title">取消申请</h2>'
    content += '<div class="notice notice-warning" style="margin-bottom:16px">' + ico('warn')
    content += '<div>订单已承接但尚未起运，提交后订单进入「取消处理中」，由物流 company 确认后变为「已取消」；如被驳回则恢复原状态并展示驳回原因。</div></div>'
    content += '<div class="field"><label class="field-label"><span class="req">*</span>取消原因</label>'
    content += '<textarea class="textarea" id="cancelReason" data-required placeholder="请填写取消原因（必填）"></textarea>'
    content += '<div class="help err" style="display:none">取消原因为必填项，请说明具体原因。</div></div>'
    content += '<div class="field"><label class="field-label">补充说明</label><textarea class="textarea" placeholder="选填"></textarea></div>'
    content += '<div class="form-actions"><button class="btn btn-secondary">返回</button>'
    content += '<button class="btn btn-danger" onclick="demoValidate(\'cancelForm\',\'cancelModal\')">提交取消申请</button></div>'
    content += '</div></section>'
    cm = modal('cancelModal','确认提交取消申请',
        '提交后订单状态变为「取消处理中」，等待物流公司处理，期间不可重复提交。',
        '<button class="btn btn-secondary" onclick="closeModal()">返回修改</button>'
        '<button class="btn btn-danger" onclick="submitAction(\'申请已提交，订单进入取消处理中\')">确认提交</button>')
    content = web_shell('shipper','web-08-order-cancel.html','订单取消','取消申请 · 原因必填', content)
    content = content.replace('<main class="content">', '<main class="content"><form id="cancelForm" onsubmit="return false">')
    content = content.replace('</main></div></div>', cm + '</form></main></div></div>')
    content = content.replace('物流 company', '物流公司')
    save('web-08-order-cancel.html', content)
