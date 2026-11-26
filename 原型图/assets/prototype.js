/* ============================================================
   物流运输管理平台 · 原型通用交互
   目的：让静态原型可演示基础交互流程（展开/收起、抽屉、确认、步骤、校验）
   ============================================================ */

(function () {
  'use strict';

  /* ---------- 轻提示 ---------- */
  window.toast = function (msg) {
    var el = document.getElementById('__toast');
    if (!el) {
      el = document.createElement('div');
      el.id = '__toast';
      el.style.cssText = 'position:fixed;left:50%;bottom:32px;transform:translateX(-50%);background:#14171F;color:#fff;padding:10px 16px;border-radius:6px;font-size:13px;z-index:999;opacity:0;transition:opacity .18s ease;pointer-events:none;max-width:80vw;text-align:center';
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.style.opacity = '1';
    clearTimeout(window.__toastTimer);
    window.__toastTimer = setTimeout(function () { el.style.opacity = '0'; }, 2200);
  };

  /* ---------- 密码显隐 ---------- */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-act="pwd"]');
    if (btn) {
      var input = btn.parentNode.querySelector('input');
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.setAttribute('aria-label', show ? '隐藏密码' : '显示密码');
      btn.innerHTML = show
        ? '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>'
        : '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M3 3l18 18M10.6 10.7a2 2 0 0 0 2.8 2.8M9.9 5.3A10.6 10.6 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3 3.7M6.2 6.2C3.6 8 2 12 2 12s3.5 7 10 7a10.8 10.8 0 0 0 4-.7"/></svg>';
    }
  });

  /* ---------- 注册区展开 ---------- */
  window.toggleRegister = function () {
    var z = document.getElementById('registerZone');
    if (!z) return;
    var open = z.classList.toggle('show');
    var btn = document.getElementById('registerToggle');
    if (btn) btn.textContent = open ? '收起注册' : '注册新账号';
    if (open) z.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  /* ---------- 筛选区折叠 ---------- */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-act="filter"]');
    if (!btn) return;
    var bar = btn.closest('.filterbar');
    bar.classList.toggle('collapsed');
    btn.innerHTML = bar.classList.contains('collapsed')
      ? '展开筛选 <svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>'
      : '收起筛选 <svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m18 15-6-6-6 6"/></svg>';
  });

  /* ---------- 抽屉 ---------- */
  window.openDrawer = function (id) {
    var d = document.getElementById(id);
    var o = document.getElementById('__overlay');
    if (!d) return;
    if (!o) {
      o = document.createElement('div');
      o.id = '__overlay'; o.className = 'overlay';
      o.addEventListener('click', closeAll);
      document.body.appendChild(o);
    }
    closeAll(true);
    requestAnimationFrame(function () { o.classList.add('show'); d.classList.add('show'); });
    document.body.style.overflow = 'hidden';
  };
  window.closeDrawer = closeAll;
  function closeAll(keepOverlay) {
    document.querySelectorAll('.drawer.show, .modal.show').forEach(function (n) { n.classList.remove('show'); });
    if (!keepOverlay) {
      var o = document.getElementById('__overlay');
      if (o) o.classList.remove('show');
      document.body.style.overflow = '';
    }
  }

  /* ---------- 弹层 ---------- */
  window.openModal = function (id) { window.openDrawer(id); };
  window.closeModal = closeAll;
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-act="close"]')) closeAll();
  });

  /* ---------- Tab 切换 ---------- */
  window.switchTab = function (el, group) {
    var scope = el.closest('.tab-scope') || document;
    scope.querySelectorAll('.tab[data-group="' + group + '"]').forEach(function (t) { t.classList.remove('active'); });
    el.classList.add('active');
    scope.querySelectorAll('.tabpane[data-group="' + group + '"]').forEach(function (p) {
      p.classList.toggle('active', p.getAttribute('data-name') === el.getAttribute('data-name'));
    });
  };

  /* ---------- 驳回必填原因 ---------- */
  window.submitReject = function (inputId, label) {
    var input = document.getElementById(inputId);
    var tip = document.getElementById(inputId + 'Tip');
    if (!input || !input.value.trim()) {
      if (tip) { tip.style.display = 'block'; }
      input && input.classList.add('err');
      input && input.focus();
      return;
    }
    if (tip) tip.style.display = 'none';
    input && input.classList.remove('err');
    closeAll();
    toast((label || '已驳回') + '，原因已作为追加记录保存');
  };

  window.submitAction = function (msg) { closeAll(); toast(msg); };

  /* ---------- 表单校验演示 ---------- */
  window.demoValidate = function (formId, modalId) {
    var form = document.getElementById(formId);
    var bad = 0;
    form.querySelectorAll('[data-required]').forEach(function (el) {
      var empty = !el.value || !el.value.trim();
      var tip = el.parentNode.querySelector('.help.err');
      if (empty) {
        bad++;
        el.classList.add('err');
        if (tip) tip.style.display = 'block';
      } else {
        el.classList.remove('err');
        if (tip) tip.style.display = 'none';
      }
    });
    if (bad) { toast('还有 ' + bad + ' 项必填未填写，请按字段提示修改'); form.querySelector('.err') && form.querySelector('.err').focus(); return; }
    if (modalId) openModal(modalId); else toast('校验通过');
  };

  /* ---------- H5 分步流程 ---------- */
  window.h5Step = 1;
  window.goStep = function (n) {
    window.h5Step = Math.max(1, Math.min(3, n));
    for (var i = 1; i <= 3; i++) {
      var pane = document.getElementById('step' + i);
      var dot = document.getElementById('stepDot' + i);
      if (pane) pane.style.display = window.h5Step === i ? 'block' : 'none';
      if (dot) {
        dot.className = 'h5-step ' + (window.h5Step === i ? 'on' : (i < window.h5Step ? 'done' : ''));
        dot.querySelector('i').textContent = i < window.h5Step ? '✓' : String(i);
      }
    }
    for (var j = 1; j <= 2; j++) {
      var next = document.getElementById('nextBtn' + j);
      var prev = document.getElementById('prevBtn' + j);
      if (next) next.style.display = window.h5Step === j ? 'inline-flex' : 'none';
      if (prev) prev.style.display = window.h5Step === j + 1 ? 'inline-flex' : 'none';
    }
    var done = document.getElementById('doneBtn');
    if (done) done.style.display = window.h5Step === 3 ? 'inline-flex' : 'none';
  };

  /* ---------- 上传占位交互 ---------- */
  document.addEventListener('click', function (e) {
    var up = e.target.closest('[data-act="upload"]');
    if (!up) return;
    var done = up.classList.toggle('done');
    var t = up.querySelector('span');
    if (t) t.textContent = done ? '已选择 1 张现场照片' : '点击上传现场照片';
    toast(done ? '原型演示：照片已加入待提交列表' : '已取消照片选择');
  });

  /* ---------- 单选联动演示 ---------- */
  document.addEventListener('change', function (e) {
    if (e.target && e.target.id === 'quoteMethod') {
      var box = document.getElementById('negotiableBox');
      if (box) box.style.display = e.target.value === '可议' ? 'block' : 'none';
    }
    if (e.target && e.target.id === 'shipFrom') {
      var box = document.getElementById('tempAddressBox');
      if (box) box.style.display = e.target.value === '临时地址' ? 'block' : 'none';
    }
    if (e.target && e.target.id === 'locationState') {
      var bar = document.getElementById('locationWarn');
      if (bar) bar.style.display = e.target.value === '异常' ? 'flex' : 'none';
    }
    if (e.target && e.target.id === 'expenseType') {
      var box = document.getElementById('otherExpenseBox');
      if (box) box.style.display = e.target.value === '其它' ? 'block' : 'none';
    }
  });

  /* ---------- 全选 ---------- */
  document.addEventListener('change', function (e) {
    if (e.target && e.target.id === 'checkAll') {
      document.querySelectorAll('[data-rowcheck]').forEach(function (c) { c.checked = e.target.checked; });
    }
  });

  /* ---------- 索引页导航 ---------- */
  document.addEventListener('click', function (e) {
    var link = e.target.closest('[data-preview]');
    if (!link) return;
    e.preventDefault();
    var url = link.getAttribute('data-preview');
    var frame = document.getElementById('previewFrame');
    if (frame) frame.src = url;
    document.querySelectorAll('.hub-link').forEach(function (n) { n.classList.remove('active'); });
    link.classList.add('active');
    var t = document.getElementById('hubTitle');
    if (t) t.textContent = link.getAttribute('data-title');
    var s = document.getElementById('hubSub');
    if (s) s.textContent = link.getAttribute('data-sub') || '';
    var o = document.getElementById('openNew');
    if (o) o.href = url;
    try { localStorage.setItem('protoLast', url); } catch (err) {}
  });

  var last = null;
  try { last = localStorage.getItem('protoLast'); } catch (err) {}
  if (last && document.getElementById('previewFrame')) {
    var m = document.querySelector('[data-preview="' + last + '"]');
    if (m) { document.getElementById('previewFrame').src = last; m.click(); }
  }
})();
