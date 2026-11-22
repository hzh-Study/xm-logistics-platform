# 组件样式

适用范围：写 `<style>`、CSS 变量、主题。视觉风格另见 `../ui/`。

## 规则

- MUST 非布局组件用 `<style scoped>` 并用 class 选择器；MUST NOT 在 scoped 下用裸元素选择器。理由：官方 Priority A，scoped 下元素选择器更慢且易误伤。
- MUST 全局样式只放 `App.vue` 或布局组件，组件内不写全局规则。理由：限制样式作用域。
- MUST `:deep()` / `:slotted()` / `:global()` 只在必要时用，且附一行 `NOTE` 说明原因（见 `../comments/markers.md`）。理由：穿透作用域是例外，需可追溯。
- MUST 设计 token（颜色、间距、圆角、字号）以 CSS 自定义属性放 `src/assets/styles/`，组件只引用变量，不写死色值。理由：统一主题、避免魔法值。
- MUST NOT 用用户可控的 inline `:style`；确需动态样式时用对象语法 + 属性白名单。理由：防样式注入与点击劫持。
- MUST 主题值用 CSS `v-bind()` 绑定组件状态，MUST NOT 拼字符串进 style。理由：类型安全且可维护。
- MUST 不写渐变、装饰性 blob / 网格背景（见 `../ui/anti-ai-patterns.md`）。理由：统一克制视觉。

## Checklist

- [ ] scoped + class 选择器，无裸元素选择器
- [ ] 全局样式仅在 App / 布局
- [ ] 穿透器有 NOTE，设计 token 化
- [ ] 无用户可控 inline style，无渐变装饰
