<template>
  <div id="app">
    <AppLayout />
  </div>
</template>

<script setup>
import AppLayout from './components/layout/AppLayout.vue'
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: radial-gradient(ellipse at 50% 0%, #0d1117 0%, #0a0a1a 100%);
  color: rgba(255, 255, 255, 0.87);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app { min-height: 100vh; }

/* 优雅滚动条 */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(79, 195, 247, 0.2); border-radius: 3px; transition: all 0.3s; }
::-webkit-scrollbar-thumb:hover { background: rgba(79, 195, 247, 0.4); }
::-webkit-scrollbar-corner { background: transparent; }

/* 选中颜色 */
::selection {
  background: rgba(233, 69, 96, 0.3);
  color: #fff;
}

/* 全局过渡 */
* {
  transition-property: background-color, border-color, color;
  transition-duration: 0.2s;
  transition-timing-function: ease;
}

/* 按钮重置 */
button {
  font-family: inherit;
}

/* 卡片通用样式 */
.glass-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(12px);
  border-radius: 14px;
}
</style>
