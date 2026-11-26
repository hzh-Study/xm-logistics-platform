# -*- coding: utf-8 -*-
"""原型生成公共组件：设计 token 已在 assets/prototype.css，这里只拼装 HTML 片段。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = 'assets/prototype.css'
JS = 'assets/prototype.js'

# ---------------- 线性图标（禁止 emoji） ----------------
_P = {
 'grid': '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
 'user': '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/>',
 'users': '<circle cx="9" cy="8" r="3"/><path d="M2 20c0-3.3 3-5 7-5s7 1.7 7 5M17 8a3 3 0 0 1 0 6M18 15c2.4.6 4 2.2 4 5"/>',
 'box': '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="M3 7v10l9 5 9-5V7M12 12v10"/>',
 'truck': '<path d="M2 6h11v11H2zM13 10h4l4 4v3h-8z"/><circle cx="6" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
 'clip': '<path d="M9 4h6M9 4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2"/><path d="M9 10h6M9 14h6"/>',
 'shield': '<path d="M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5l-8-3Z"/><path d="m9 12 2 2 4-4"/>',
 'bell': '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 8h18s-3-1-3-8M10 20h4"/>',
 'warn': '<path d="M12 3 2 21h20L12 3Z"/><path d="M12 9v5M12 18h.01"/>',
 'card': '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
 'swap': '<path d="M4 8h13l-3-3M20 16H7l3 3"/>',
 'doc': '<path d="M6 2h8l5 5v15H6z"/><path d="M14 2v5h5M9 12h7M9 16h7"/>',
 'pin': '<path d="M12 21s7-6 7-12a7 7 0 1 0-14 0c0 6 7 12 7 12Z"/><circle cx="12" cy="9" r="2.5"/>',
 'cam': '<path d="M4 7h4l2-2h4l2 2h4v12H4z"/><circle cx="12" cy="13" r="3"/>',
 'logout': '<path d="M10 4H5v16h5M14 8l4 4-4 4M18 12H9"/>',
 'search': '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
 'plus': '<path d="M12 5v14M5 12h14"/>',
 'chev': '<path d="m9 6 6 6-6 6"/>',
 'back': '<path d="m15 6-6 6 6 6"/>',
 'close': '<path d="M6 6l12 12M18 6 6 18"/>',
 'check': '<path d="m5 12 4 4L19 6"/>',
 'edit': '<path d="M4 20h4L20 8l-4-4L4 16v4ZM14 6l4 4"/>',
 'eye': '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z"/><circle cx="12" cy="12" r="2.5"/>',
 'inbox': '<path d="M3 12h5l2 3h4l2-3h5"/><path d="M5 5h14l2 7v7H3v-7l2-7Z"/>',
 'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 'money': '<circle cx="12" cy="12" r="9"/><path d="M8 9h8M8 13h8M12 6v12"/>',
 'settings': '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>',
 'ban': '<circle cx="12" cy="12" r="9"/><path d="m5 5 14 14"/>',
 'list': '<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/>',
}
def ico(name, cls=''):
    return f'<svg class="icon {cls}" viewBox="0 0 24 24" aria-hidden="true">{_P.get(name, _P["box"])}</svg>'

# ---------------- 状态字面值 → 语义档位（逐字使用第 7 节） ----------------
STATUS = {
 '未提交':'', '待审核':'warning', '审核通过':'success', '审核不通过':'error',
 '正常使用':'success', '已禁用':'error', '已注销':'',
 '待承接':'warning', '已承接':'brand', '运输中':'brand', '已完成':'success',
 '取消处理中':'warning', '已取消':'error', '异常处理中':'error',
 '待司机确认':'warning', '待装货':'warning', '待签收':'warning', '待确认完成':'warning',
 '异常':'error', '已拒绝':'error',
 '可派单':'success', '任务占用中':'warning', '暂停接单':'warning',
 '在职':'success', '离职':'error',
 '可用':'success', '占用中':'warning', '暂停使用':'warning',
 '在册':'success', '维修中':'warning', '已停用':'error',
 '待支付':'warning', '已支付':'success',
 '待派单':'warning',
}
def pill(text, override=None):
    k = override if override is not None else STATUS.get(text, '')
    return f'<span class="pill' + (f' pill--{k}' if k else '') + f'">{text}</span>'

# ---------------- 导航结构 ----------------
NAV = {
 'shipper': [
   ('工作台', [('工作台','web-02-shipper-dashboard.html','grid')]),
   ('认证与设置', [('货主认证','web-03-shipper-certification.html','shield'),('仓库管理','web-04-shipper-warehouses.html','box')]),
   ('运输订单', [('发布运输订单','web-05-shipper-order-new.html','plus'),('我的订单','web-06-shipper-orders.html','doc'),('订单进度','web-07-order-progress.html','clock')]),
 ],
 'carrier': [
   ('工作台', [('工作台','web-09-carrier-dashboard.html','grid')]),
   ('资质与资源', [('企业认证','web-10-carrier-certification.html','shield'),('司机管理','web-15-drivers.html','users'),('车辆管理','web-16-vehicles.html','truck')]),
   ('订单与派单', [('订单池','web-11-order-pool.html','inbox'),('派单管理','web-12-dispatch.html','swap'),('取消申请处理','web-14-cancel-applications.html','ban')]),
   ('运输执行', [('运输异常','web-13-exceptions.html','warn'),('任务进度','web-18-task-progress.html','clock')]),
   ('财务', [('费用审核','web-17-expenses.html','money')]),
 ],
 'admin': [
   ('工作台', [('工作台','web-20-admin-dashboard.html','grid')]),
   ('审核中心', [('统一认证审核','web-21-certifications.html','shield'),('货主认证审核','web-28-shipper-certifications.html','user'),('公司认证审核','web-29-carrier-certifications.html','users')]),
   ('查询与监督', [('平台主体查询','web-22-accounts.html','search'),('运输订单查询','web-23-admin-orders.html','doc'),('运输任务查询','web-24-admin-tasks.html','truck'),('平台异常管理','web-26-platform-exceptions.html','warn'),('车辆转籍','web-27-vehicle-transfers.html','swap')]),
   ('平台运营', [('平台公告与通知','web-25-announcements.html','bell')]),
 ],
}
ROLE_NAME = {'shipper':'货主','carrier':'物流公司','admin':'管理员'}

def head(title, h5=False):
    vp = 'width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no' if h5 else 'width=device-width,initial-scale=1'
    return (f'<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="{vp}">\n<title>{title}</title>\n'
            f'<link rel="stylesheet" href="{CSS}">\n</head>\n<body>\n')

def foot(extra=''):
    return extra + f'\n<script src="{JS}"></script>\n</body>\n</html>\n'

def web_shell(role, active, title, sub, content, right=''):
    nav = ''
    for gname, items in NAV[role]:
        nav += f'<div class="nav-group"><div class="nav-group-title">{gname}</div>'
        for label, href, ic in items:
            cls = ' active' if href == active else ''
            nav += f'<a class="nav-item{cls}" href="{href}">{ico(ic)}<span>{label}</span></a>'
        nav += '</div>'
    r = ROLE_NAME[role]
    html = head(title)
    html += ('<div class="app"><aside class="sidebar">'
      '<div class="brand"><span class="brand-mark">运</span><span>物流运输管理<span class="brand-sub">平台</span></span></div>'
      f'<nav class="nav">{nav}</nav>'
      '<div class="nav-foot"><a href="index.html">← 返回原型索引</a></div></aside>'
      '<div class="main">'
      f'<header class="topbar"><div class="crumb">{r} <span style="color:var(--border-strong)">/</span> <b>{title}</b></div>'
      f'<div class="top-right">{right}<span class="role-tag">{r}</span>'
      f'<span class="top-user"><span class="avatar">{(right or "账")[0]}</span>账号</span>'
      f'<button class="btn btn-text btn-sm" onclick="toast(\'退出登录，会话已失效\')">{ico("logout","icon-sm")}退出</button></div></header>'
      f'<main class="content"><div class="page-head"><div><h1 class="page-title">{title}</h1>'
      f'<p class="page-sub">{sub}</p></div></div>{content}</main></div></div>')
    html += foot()
    return html

def h5_shell(title, body, bottom='', status='9:41'):
    return (head(title, True)
      + '<div class="h5-stage"><div class="phone">'
      + f'<div class="h5-status"><span>{status}</span><span>信号 · Wi-Fi · 100%</span></div>'
      + body
      + f'<div class="h5-bottom">{bottom}</div>'
      + '</div></div>' + foot())

def page_head(title, sub, actions=''):
    return (f'<div class="page-head"><div><h1 class="page-title">{title}</h1>'
            f'<p class="page-sub">{sub}</p></div><div class="head-actions">{actions}</div></div>')

def stats(items):
    return '<div class="stats">' + ''.join(
        f'<div class="stat"><div class="stat-num">{n}</div><div class="stat-label">{l}</div></div>' for n, l in items) + '</div>'

def panel(title, body, hint='', tight=False):
    h = f'<section class="panel"><div class="panel-head"><span class="panel-title">{title}</span>'
    if hint: h += f'<span class="panel-hint">{hint}</span>'
    h += f'</div><div class="panel-body{" tight" if tight else ""}">{body}</div></section>'
    return h

def filters(fields, collapsed=False):
    g = ''
    for lab, ctrl in fields:
        g += f'<div class="field"><label class="field-label">{lab}</label>{ctrl}</div>'
    btn = ('展开筛选 ' + ico('chev','icon-sm')) if collapsed else ('收起筛选 ' + ico('back','icon-sm'))
    return (f'<div class="filterbar{" collapsed" if collapsed else ""}">'
      f'<div class="filter-head"><span class="filter-title">{ico("search","icon-sm")}筛选条件</span>'
      f'<button class="btn btn-text btn-sm" data-act="filter">{btn}</button></div>'
      f'<div class="filter-grid">{g}</div>'
      '<div class="filter-foot"><button class="btn btn-secondary btn-sm" onclick="toast(\'筛选条件已重置\')">重置</button>'
      '<button class="btn btn-primary btn-sm" onclick="toast(\'已按条件查询\')">查询</button></div></div>')

def inp(ph='', val='', typ='text'):
    return f'<input class="input" type="{typ}" placeholder="{ph}" value="{val}">'
def sel(options, first='全部'):
    o = f'<option>{first}</option>' + ''.join(f'<option>{x}</option>' for x in options)
    return f'<select class="select">{o}</select>'

def table(cols, rows, empty=None, paginate=True, total='共 24 条'):
    if not rows and empty:
        return f'<div class="empty">{ico("inbox")}<span>{empty}</span></div>'
    h = '<div class="table-wrap"><table class="tbl"><thead><tr>'
    for c in cols:
        cls = ' class="num"' if c.startswith('#') else ''
        h += f'<th{cls}>{c.lstrip("#")}</th>'
    h += '</tr></thead><tbody>'
    for row in rows:
        h += '<tr>'
        for cell in row:
            h += f'<td>{cell}</td>'
        h += '</tr>'
    h += '</tbody></table></div>'
    if paginate:
        h += ('<div class="pagination"><span>' + total + '</span>'
          '<button class="page-btn" disabled>‹</button><button class="page-btn on">1</button>'
          '<button class="page-btn">2</button><button class="page-btn">3</button>'
          '<button class="page-btn">›</button></div>')
    return h

def ops(*labels):
    return '<div class="ops">' + ''.join(f'<button class="btn btn-text" onclick="toast(\'原型演示：{l}\')">{l}</button>' for l in labels) + '</div>'

def drawer(id_, title, body, foot_html=''):
    return (f'<div class="drawer" id="{id_}"><div class="drawer-head">'
      f'<span class="drawer-title">{title}</span>'
      f'<button class="icon-btn" data-act="close">{ico("close")}</button></div>'
      f'<div class="drawer-body">{body}</div>'
      f'<div class="drawer-foot">{foot_html}</div></div>')

def modal(id_, title, body, foot_html):
    return (f'<div class="modal" id="{id_}"><div class="modal-head">{title}</div>'
      f'<div class="modal-body">{body}</div><div class="modal-foot">{foot_html}</div></div>')

def kv(pairs):
    return '<dl class="kv">' + ''.join(f'<dt>{k}</dt><dd>{v}</dd>' for k, v in pairs) + '</dl>'

def notices(items):
    return '<ul class="list-simple">' + ''.join(
      f'<li><span>{t}</span><span class="meta">{m}</span></li>' for t, m in items) + '</ul>'

def save(name, html):
    (ROOT / name).write_text(html, encoding='utf-8')
    print('  ->', name)
