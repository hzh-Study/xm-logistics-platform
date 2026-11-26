# -*- coding: utf-8 -*-
"""司机 H5：按 375px 宽设计，单列卡片 + 底部固定操作"""
from common import *

def nav(title, back=None):
    b = f'<span class="back" onclick="history.back()">{ico("back")}</span>' if back else ''
    return f'<div class="h5-nav">{b}{title}</div>'

def row(k, v):
    return f'<div class="h5-row"><span class="k">{k}</span><span class="v">{v}</span></div>'

def build():
    # ---------- H5 登录 ----------
    b = nav('司机登录') if False else '<div class="h5-nav">司机登录</div>'
    b += '<div class="h5-scroll"><div style="padding:24px 0 8px">'
    b += '<div style="font-size:20px;font-weight:600">司机登录</div>'
    b += '<div style="font-size:13px;color:var(--text-3);margin-top:4px">使用物流公司分配的账号登录</div></div>'
    b += '<div class="h5-card"><label class="h5-label">手机号</label>' + inp('请输入手机号', '13810010001')
    b += '<label class="h5-label">密码</label><div class="pwd-wrap">' + inp('请输入密码', 'temp@2026', 'password')
    b += '<button type="button" class="pwd-toggle" data-act="pwd" aria-label="显示密码">' + ico('eye','icon-sm') + '</button></div>'
    b += '<div class="help" style="margin-top:10px">首次登录将强制修改临时密码并完成身份绑定。</div></div>'
    b += '<div class="notice notice-info">' + ico('ban') + '<div>司机账号由物流公司创建，不支持自行注册，也无法承接公共货源。</div></div>'
    b += '</div>'
    save('h5-01-login.html', web_shell if False else h5_shell('司机登录', b,
        '<button class="btn btn-primary" onclick="toast(\'登录成功，进入身份绑定\')">登录</button>'))

    # ---------- H5 身份绑定 ----------
    b = nav('身份绑定')
    b += '<div class="h5-scroll">'
    b += '<div class="h5-steps">'
    for i,lab in enumerate(['修改密码','身份资料','确认'],1):
        b += f'<div class="h5-step{" on" if i==1 else ""}" id="stepDot{i}"><i>{i}</i>{lab}</div>'
    b += '</div>'
    # step1
    b += '<div id="step1"><div class="h5-card"><div class="h5-card-title">修改初始密码</div>'
    b += '<div class="h5-card-sub">首次登录必须修改临时密码</div>'
    b += '<label class="h5-label">当前临时密码</label>' + inp('请输入', 'temp@2026', 'password')
    b += '<label class="h5-label">新密码</label>' + inp('至少 8 位', '', 'password')
    b += '<label class="h5-label">确认新密码</label>' + inp('请再次输入', '', 'password')
    b += '<div class="help">新密码不少于 8 位，包含字母与数字。</div></div></div>'
    # step2
    b += '<div id="step2" style="display:none"><div class="h5-card"><div class="h5-card-title">身份与驾照资料</div>'
    b += '<label class="h5-label">真实姓名</label>' + inp('请输入姓名', '王建国')
    b += '<label class="h5-label">身份证号</label>' + inp('请输入身份证号')
    b += '<label class="h5-label">准驾车型</label>' + sel(['A1','A2','B2','C1'], 'A2')
    b += '<label class="h5-label">驾驶证号</label>' + inp('请输入驾驶证号')
    b += '<label class="h5-label">驾驶证有效期</label>' + inp('', '2030-06-30')
    b += '<label class="h5-label">身份证 / 驾驶证照片</label>'
    b += '<div class="h5-upload" data-act="upload">' + ico('cam') + '<span>点击上传证件照片</span></div>'
    b += '</div></div>'
    # step3
    b += '<div id="step3" style="display:none"><div class="h5-card"><div class="h5-card-title">确认绑定信息</div>'
    b += row('姓名','王建国') + row('所属公司','盛达物流有限公司') + row('准驾车型','A2')
    b += row('账号状态',pill('正常使用')) + row('雇佣关系',pill('在职'))
    b += '<div class="notice notice-info" style="margin-top:12px">' + ico('shield')
    b += '<div>确认后完成身份绑定，公司归属不可自行变更。</div></div></div></div>'
    b += '</div>'
    bottom = ('<button class="btn btn-secondary" id="prevBtn2" style="display:none" onclick="goStep(2)">上一步</button>'
      '<button class="btn btn-primary" id="nextBtn1" onclick="goStep(2)">下一步</button>'
      '<button class="btn btn-secondary" id="prevBtn3" style="display:none" onclick="goStep(2)">上一步</button>'
      '<button class="btn btn-primary" id="nextBtn2" style="display:none" onclick="goStep(3)">下一步</button>'
      '<button class="btn btn-primary" id="doneBtn" style="display:none" onclick="toast(\'身份绑定完成，进入工作台\')">完成绑定</button>')
    save('h5-02-onboarding.html', h5_shell('身份绑定', b, bottom))

    # ---------- H5 账号阻断 ----------
    b = nav('账号不可用')
    b += '<div class="h5-scroll"><div class="h5-card h5-blocked">' + ico('ban')
    b += '<h3>账号暂不可用</h3><div style="font-size:13px;color:var(--text-2);line-height:1.7">'
    b += '账号状态：' + pill('已禁用') + '<br>阻断原因：所属物流公司账号异常，已暂停司机端业务。<br>'
    b += '请联系所属物流公司处理，历史任务与报销记录均予保留。</div></div>'
    b += '<div class="h5-card"><div class="h5-card-title">其他阻断情形</div>'
    b += row('账号状态', pill('已禁用') + ' / ' + pill('已注销'))
    b += row('雇佣关系', pill('离职'))
    b += row('所属公司', pill('已禁用'))
    b += '<div class="help" style="margin-top:8px">以上任一情形均会阻断运输业务，页面只读且无可执行操作。</div></div>'
    b += '</div>'
    save('h5-03-blocked.html', h5_shell('账号不可用', b,
        '<button class="btn btn-secondary" onclick="toast(\'已退出登录\')">退出登录</button>'))

    # ---------- H5 工作台 ----------
    b = '<div class="h5-nav">工作台</div><div class="h5-scroll">'
    b += '<div class="h5-card"><div class="h5-card-title">王建国</div>'
    b += '<div class="h5-card-sub">盛达物流有限公司 · 沪A·8F231 · ' + pill('可派单') + '</div></div>'
    b += '<div class="h5-stats">'
    for n,l in [('3','今日任务'),('1','待确认'),('1','待装货'),('1','运输中'),('1','待签收'),('2','待报销')]:
        b += f'<div class="h5-stat"><b>{n}</b><span>{l}</span></div>'
    b += '</div><div style="height:12px"></div>'
    b += '<div class="h5-card"><div class="h5-card-title">最近任务</div><div style="margin-top:8px">'
    b += row('TASK-251120-0003','热轧钢板 · 32 吨')
    b += row('任务状态',pill('运输中'))
    b += row('计划送达','2026-11-22 18:00')
    b += '</div></div>'
    b += '<div class="h5-card"><div class="h5-card-title">公司通知</div><div style="margin-top:8px">'
    b += row('司机端打卡功能更新','2026-11-15')
    b += row('关于冬季运输安全的提醒','2026-11-08')
    b += '</div></div></div>'
    save('h5-04-home.html', h5_shell('工作台', b,
        '<a class="btn btn-primary" href="h5-05-tasks.html">查看任务</a>'))

    # ---------- H5 任务列表 ----------
    b = nav('我的任务')
    b += '<div class="h5-scroll"><div class="tabs tab-scope">'
    for i,(nm,on) in enumerate([('待确认',True),('进行中',False),('已完成',False)]):
        b += f'<div class="tab{" active" if on else ""}" data-group="h5task" data-name="{nm}" onclick="switchTab(this,\'h5task\')">{nm}</div>'
    b += '</div>'
    b += '<div class="tabpane active" data-group="h5task" data-name="待确认">'
    b += '<div class="h5-card"><div style="display:flex;justify-content:space-between;align-items:center">'
    b += '<span class="h5-card-title">TASK-251118-0002</span>' + pill('待司机确认') + '</div>'
    b += '<div class="h5-card-sub">ORDER-251118-0007 · 华远建材有限公司</div><div style="margin-top:10px">'
    b += row('货物','水泥 · 80 吨')
    b += row('起运地','上海嘉定原料仓')
    b += row('送达地','浙江嘉兴')
    b += row('计划装货','2026-11-22 08:00')
    b += row('计划送达','2026-11-23 18:00')
    b += row('车辆','沪B·3D772 · 高栏车')
    b += '</div></div></div>'
    b += '<div class="tabpane" data-group="h5task" data-name="进行中">'
    b += '<div class="h5-card"><div style="display:flex;justify-content:space-between;align-items:center">'
    b += '<span class="h5-card-title">TASK-251120-0003</span>' + pill('运输中') + '</div>'
    b += '<div class="h5-card-sub">热轧钢板 · 32 吨 · 上海青浦 → 江苏昆山</div>'
    b += '<div style="margin-top:8px"><a href="h5-06-departure.html" style="color:var(--brand);font-size:13px">查看执行节点 →</a></div></div></div>'
    b += '<div class="tabpane" data-group="h5task" data-name="已完成">'
    b += '<div class="empty">' + ico('inbox') + '<span>暂无已完成的运输任务</span></div></div>'
    b += '</div>'
    bottom = ('<button class="btn btn-secondary" onclick="openModal(\'rejectModal\')">拒绝</button>'
      '<button class="btn btn-primary" onclick="submitAction(\'已接单，任务进入待装货\')">接单</button>')
    b += modal('rejectModal','拒绝任务',
        '<div class="field" style="margin:0"><label class="field-label"><span class="req">*</span>拒绝原因</label>'
        '<textarea class="textarea" id="h5RejectReason" placeholder="请填写拒绝原因，将通知物流公司"></textarea>'
        '<div class="help err" id="h5RejectReasonTip" style="display:none">拒绝原因为必填项。</div></div>',
        '<button class="btn btn-secondary" onclick="closeModal()">取消</button>'
        '<button class="btn btn-danger" onclick="submitReject(\'h5RejectReason\',\'任务已拒绝，原因已提交\')">确认拒绝</button>')
    save('h5-05-tasks.html', h5_shell('我的任务', b, bottom))

    # ---------- H5 起运 / 装货打卡 ----------
    b = nav('起运 / 装货打卡')
    b += '<div class="h5-scroll">'
    b += '<div class="h5-card"><div class="h5-card-title">发货地打卡</div><div class="h5-card-sub">TASK-251120-0003 · 上海青浦钢材仓</div>'
    b += '<div class="h5-map" style="margin-top:10px">' + ico('pin') + '<span>地图定位区（原型占位，不渲染真实地图）</span></div>'
    b += row('定位','上海市青浦区华新镇华志路 128 号')
    b += row('距离快照','120 米 · ' + pill('正常', 'success'))
    b += row('打卡时间','2026-11-21 07:58')
    b += '<label class="h5-label">模拟定位状态（演示异常提示）</label>'
    b += '<select class="select" id="locationState"><option>正常</option><option>异常</option></select>'
    b += '<div class="notice notice-warning" id="locationWarn" style="display:none;margin:10px 0">' + ico('warn')
    b += '<div>当前位置超出允许范围，请填写异常说明后提交。</div></div>'
    b += '<label class="h5-label">现场照片</label>'
    b += '<div class="h5-upload" data-act="upload">' + ico('cam') + '<span>点击上传现场照片</span></div>'
    b += '<label class="h5-label">备注</label><textarea class="textarea" placeholder="选填"></textarea></div>'
    b += '<div class="h5-card"><div class="h5-card-title">装货照片</div><div class="h5-card-sub">三阶段均需上传</div>'
    for x in ['装车前','装车中','装车后']:
        b += f'<label class="h5-label">{x}</label><div class="h5-upload" data-act="upload">' + ico('cam') + '<span>点击上传现场照片</span></div>'
    b += '<label class="h5-label">装货异常（如有）</label>'
    b += '<select class="select">' + ''.join(f'<option>{x}</option>' for x in ['无','数量不符','货物破损','描述不符','无法装货','超载','其它']) + '</select>'
    b += '</div>'
    b += '<div class="h5-card"><div class="h5-card-title">车辆与货物确认</div>'
    b += row('车辆','沪A·8F231 · 平板车')
    b += row('确认','<label><input type="checkbox" checked> 已核对车辆与货物</label>')
    b += '</div></div>'
    save('h5-06-departure.html', h5_shell('起运打卡', b,
        '<button class="btn btn-primary" onclick="submitAction(\'装货完成，运输任务进入运输中\')">确认装货完成并起运</button>'))

    # ---------- H5 签收 ----------
    b = nav('签收')
    b += '<div class="h5-scroll">'
    b += '<div class="h5-card"><div class="h5-card-title">收货信息</div><div class="h5-card-sub">TASK-251120-0003</div>'
    b += row('收货快照','江苏昆山开发区前进西路 88 号')
    b += row('收货人','张经理 · 13900000000')
    b += row('计划送达','2026-11-22 18:00')
    b += row('当前状态',pill('待签收'))
    b += '<div class="h5-map" style="margin-top:10px">' + ico('pin') + '<span>收货地定位区（原型占位）</span></div>'
    b += row('距离快照','85 米 · ' + pill('正常','success'))
    b += '</div>'
    b += '<div class="h5-card"><div class="h5-card-title">卸货与签收资料</div>'
    b += '<label class="h5-label">卸货前 / 中 / 后照片</label>'
    for x in ['卸货前','卸货中','卸货后']:
        b += f'<div class="h5-upload" data-act="upload" style="margin-bottom:8px">' + ico('cam') + f'<span>上传{x}照片</span></div>'
    b += '<label class="h5-label">收货状况</label>'
    b += '<div class="radio-row"><label><input type="radio" name="rcv" checked>完好</label><label><input type="radio" name="rcv">破损</label><label><input type="radio" name="rcv">数量不符</label></div>'
    b += '<label class="h5-label">签收人</label>' + inp('请输入签收人姓名', '张经理')
    b += '<label class="h5-label">签收时间</label>' + inp('', '2026-11-22 17:36')
    b += '<label class="h5-label">签收凭证</label>'
    b += '<div class="h5-upload" data-act="upload">' + ico('doc') + '<span>上传签收凭证</span></div>'
    b += '<label class="h5-label">备注</label><textarea class="textarea" placeholder="选填"></textarea></div></div>'
    save('h5-07-signoff.html', h5_shell('签收', b,
        '<button class="btn btn-primary" onclick="submitAction(\'签收已提交，等待物流公司确认完成\')">确认签收</button>'))

    # ---------- H5 异常处理 ----------
    b = nav('异常处理')
    b += '<div class="h5-scroll">'
    b += '<div class="h5-card"><div class="h5-card-title">上报运输异常</div><div class="h5-card-sub">TASK-251120-0003 · 上海青浦 → 江苏昆山</div>'
    b += '<label class="h5-label"><span style="color:var(--error)">*</span>异常类型</label>'
    b += '<select class="select">' + ''.join(f'<option>{x}</option>' for x in ['车辆故障','事故','封路','拥堵','货物问题','预计延误','其它']) + '</select>'
    b += '<label class="h5-label">现场照片</label>'
    b += '<div class="h5-upload" data-act="upload">' + ico('cam') + '<span>点击上传现场照片</span></div>'
    b += '<label class="h5-label"><span style="color:var(--error)">*</span>异常说明</label>'
    b += '<textarea class="textarea" placeholder="请描述异常情况与当前位置"></textarea>'
    b += '<div class="notice notice-info" style="margin-top:12px">' + ico('warn')
    b += '<div>提交后由物流公司处置；车辆更换、司机更换等变更均由公司通过异常流程处理，司机不可自行换车。</div></div>'
    b += '</div>'
    b += '<div class="h5-card"><div class="h5-card-title">异常处理记录</div><div style="margin-top:8px">'
    b += row('EXC-251120-0002','车辆故障 · 2026-11-21 10:14')
    b += row('处理结果','—（待公司处置）')
    b += '</div><div class="help" style="margin-top:8px">处理结果为追加记录，原上报内容保留。</div></div></div>'
    save('h5-08-exception.html', h5_shell('异常处理', b,
        '<button class="btn btn-primary" onclick="submitAction(\'异常已上报，等待物流公司处置\')">提交异常</button>'))

    # ---------- H5 费用提交 ----------
    b = nav('费用提交')
    b += '<div class="h5-scroll">'
    b += '<div class="notice notice-info" style="margin-bottom:12px">' + ico('money')
    b += '<div>单次提交一笔报销费用，凭证与关联任务需填写完整。报销进度可在费用记录中查看。</div></div>'
    b += '<div class="h5-card"><label class="h5-label"><span style="color:var(--error)">*</span>费用类型</label>'
    b += '<select class="select" id="expenseType">' + ''.join(f'<option>{x}</option>' for x in ['油费','过路费','停车费','维修','其它']) + '</select>'
    b += '<div id="otherExpenseBox" style="display:none"><label class="h5-label">其它费用说明</label>' + inp('请输入') + '</div>'
    b += '<label class="h5-label"><span style="color:var(--error)">*</span>金额（元）</label>' + inp('请输入金额', '', 'number')
    b += '<label class="h5-label"><span style="color:var(--error)">*</span>关联运输任务</label>'
    b += '<select class="select"><option>TASK-251120-0003 · 热轧钢板 · 上海青浦 → 昆山</option><option>TASK-251118-0002 · 水泥 · 嘉定 → 嘉兴</option></select>'
    b += '<label class="h5-label"><span style="color:var(--error)">*</span>费用凭证</label>'
    b += '<div class="h5-upload" data-act="upload">' + ico('cam') + '<span>上传凭证（支持多张）</span></div>'
    b += '<label class="h5-label">费用说明</label><textarea class="textarea" placeholder="选填"></textarea></div></div>'
    save('h5-09-expense.html', h5_shell('费用提交', b,
        '<a class="btn btn-secondary" href="h5-10-expense-records.html">费用记录</a>'
        '<button class="btn btn-primary" onclick="submitAction(\'报销费用已提交，等待审核\')">提交</button>'))

    # ---------- H5 费用记录 ----------
    b = nav('费用记录')
    b += '<div class="h5-scroll"><div class="tabs tab-scope">'
    for i,(nm,on) in enumerate([('全部',True),('待审核',False),('已通过',False),('已驳回',False)]):
        b += f'<div class="tab{" active" if on else ""}" data-group="h5exp" data-name="{nm}" onclick="switchTab(this,\'h5exp\')">{nm}</div>'
    b += '</div>'
    cards = [
      ('EXP-251120-0007','油费','¥ 860.00','2026-11-21 19:20','待审核','待支付','待审核', ''),
      ('EXP-251119-0005','过路费','¥ 320.00','2026-11-20 08:12','审核通过','待支付','审核通过', ''),
      ('EXP-251116-0002','维修','¥ 1,280.00','2026-11-17 10:05','审核不通过','待支付','审核不通过',
       '<div class="notice notice-error" style="margin-top:10px">' + ico('warn') + '<div>驳回原因：缺少维修明细清单，请补充后重新提交。</div></div>'),
      ('EXP-251110-0003','停车费','¥ 60.00','2026-11-12 17:40','审核通过','已支付','审核通过', ''),
    ]
    for name in ['全部','待审核','已通过','已驳回']:
        b += f'<div class="tabpane{" active" if name=="全部" else ""}" data-group="h5exp" data-name="{name}">'
        shown = [x for x in cards if (name=='全部' or x[6]==name)]
        if not shown:
            b += '<div class="empty">' + ico('inbox') + '<span>暂无该状态的报销费用</span></div>'
        for no,typ,amt,tm,st,pay,key,extra in shown:
            b += '<div class="h5-card"><div style="display:flex;justify-content:space-between;align-items:center">'
            b += f'<span class="h5-card-title">{typ}</span><span class="num" style="font-size:16px;font-weight:600">{amt}</span></div>'
            b += f'<div class="h5-card-sub">{no} · {tm}</div><div style="margin-top:8px">'
            b += row('审核状态',pill(st)) + row('支付状态',pill(pay)) + row('关联任务','TASK-251120-0003')
            b += '</div>' + extra
            if key=='审核不通过':
                b += '<div style="margin-top:10px"><button class="btn btn-secondary btn-sm" onclick="toast(\'已基于原驳回记录新建一笔报销费用\')">重新提交</button></div>'
            b += '</div>'
        b += '</div>'
    b += '</div>'
    save('h5-10-expense-records.html', h5_shell('费用记录', b,
        '<a class="btn btn-primary" href="h5-09-expense.html">提交新费用</a>'))
