/// <reference types="vite/client" />

// 全局组件类型：让 vue-tsc 认识 app.use(Vant) 注册的组件，
// 拼错组件名或用错 props 会在 build 阶段报错（而非运行时才发现）。
declare module 'vue' {
  export interface GlobalComponents {
    VanField: typeof import('vant')['Field']
    VanButton: typeof import('vant')['Button']
  }
}

export {}
