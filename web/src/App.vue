<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
*, *::before, *::after { box-sizing: border-box; }

html, body { margin: 0; padding: 0; }

body {
  font-family: var(--font-sans);
  font-size: var(--font-size-md);
  line-height: var(--line-height);
  color: var(--color-text);
  background: var(--color-bg);
  -webkit-font-smoothing: antialiased;
}

a { color: inherit; text-decoration: none; }
button, input, select, textarea { font-family: inherit; font-size: inherit; }

.num, .amount { font-variant-numeric: tabular-nums; text-align: right; }

/* ---------- 通用面板 ---------- */
.panel {
  margin-bottom: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}
.panel:last-child { margin-bottom: 0; }
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  height: 48px;
  padding: 0 var(--space-5);
  border-bottom: 1px solid var(--color-border);
}
.panel-title { font-size: var(--font-size-md); font-weight: 600; }
.panel-hint { font-size: var(--font-size-sm); color: var(--color-text-3); }
.panel-body { padding: var(--space-5); }
.panel-body--tight { padding: 0; }
.section-title {
  margin: var(--space-6) 0 var(--space-3);
  font-size: var(--font-size-md);
  font-weight: 600;
}

/* ---------- 统计卡与栅格 ---------- */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: var(--space-3);
}

/* ---------- 筛选区 ---------- */
.filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-3) var(--space-4);
  padding: 0 var(--space-4) var(--space-4);
}
.filter-grid .field { margin: 0; }
.filter-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: 0 var(--space-4) var(--space-4);
}

/* ---------- 表单 ---------- */
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 var(--space-5); }
.form-grid--3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.field { margin-bottom: var(--space-4); }
.field__label {
  display: block;
  margin-bottom: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-2);
  font-weight: 500;
}
.field__req { color: var(--color-error); margin-right: 3px; }
.field__help { margin-top: var(--space-1); font-size: var(--font-size-xs); color: var(--color-text-3); }
.field__error { margin-top: var(--space-1); font-size: var(--font-size-xs); color: var(--color-error); }
.check-row { display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-5); align-items: center; min-height: 36px; }
.check-row label { display: inline-flex; align-items: center; gap: var(--space-2); color: var(--color-text-2); cursor: pointer; }
.check-row input { accent-color: var(--color-accent); width: 15px; height: 15px; }
.readonly-box {
  padding: var(--space-3) var(--space-4);
  background: var(--color-fill);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  font-size: var(--font-size-sm);
  color: var(--color-text-2);
}
.form-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  padding-top: var(--space-1);
}
.form-actions .el-button + .el-button { margin-left: 0; }

/* ---------- 表格 ---------- */
.table-wrap { width: 100%; overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-md); }
.data-table th {
  background: var(--color-fill);
  color: var(--color-text-2);
  font-weight: 500;
  font-size: var(--font-size-sm);
  text-align: left;
  padding: 0 var(--space-4);
  height: 40px;
  white-space: nowrap;
  border-bottom: 1px solid var(--color-border);
}
.data-table td {
  height: 48px;
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}
.data-table tr:last-child td { border-bottom: 0; }
.data-table tbody tr:hover { background: var(--color-accent-soft); }
.data-table .ops { text-align: right; white-space: nowrap; }
.data-table .ops .el-button + .el-button { margin-left: 0; }
.cell-sub { margin-top: 2px; font-size: var(--font-size-xs); color: var(--color-text-3); }
.cell-link { color: var(--color-accent); cursor: pointer; }
.pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
  font-size: var(--font-size-sm);
  color: var(--color-text-3);
}

/* ---------- 详情键值 ---------- */
.kv { display: grid; grid-template-columns: 96px 1fr; gap: var(--space-3) var(--space-4); font-size: var(--font-size-md); }
.kv dt { color: var(--color-text-3); font-size: var(--font-size-sm); }
.kv dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
.summary-list { display: grid; grid-template-columns: 92px 1fr; gap: var(--space-2) var(--space-3); margin: 0; font-size: var(--font-size-sm); }
.summary-list dt { color: var(--color-text-3); }
.summary-list dd { margin: 0; color: var(--color-text); }
.list-simple { margin: 0; padding: 0; list-style: none; }
.list-simple li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-sm);
}
.list-simple li:last-child { border-bottom: 0; }
.list-simple .meta { font-size: var(--font-size-xs); color: var(--color-text-3); font-variant-numeric: tabular-nums; }

/* ---------- 响应式 ---------- */
@media (max-width: 900px) {
  .filter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .form-grid, .form-grid--3 { grid-template-columns: 1fr; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
</style>
