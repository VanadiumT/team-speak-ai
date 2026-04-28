<template>
  <div id="app">
    <AppLayout />
  </div>
</template>

<script setup>
import AppLayout from './components/layout/AppLayout.vue'
</script>

<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&family=Space+Grotesk:wght@500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

/* ── Reset ── */
* { margin: 0; padding: 0; box-sizing: border-box; }

/* ── Body ── */
body {
  font-family: 'Inter', sans-serif;
  background: #10131b;
  color: #e0e2ed;
  font-size: 16px;
  line-height: 1.6;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app { min-height: 100vh; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #10131b; }
::-webkit-scrollbar-thumb { background: #31353d; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #414754; }

/* ── Selection ── */
::selection {
  background: rgba(233, 69, 96, 0.3);
  color: #fff;
}

/* ── Button reset ── */
button { font-family: inherit; }

/* ── Glass card ── */
.glass-card {
  background: rgba(28, 32, 39, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 8px;
  border: 1px solid rgba(65, 71, 84, 0.5);
}

/* ── Global node card hover ── */
.node-card { transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s; }
.node-card:hover { transform: translateY(-2px); z-index: 20 !important; }

/* ── Streaming text cursor ── */
@keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
.stream-cursor { animation: blink 0.8s step-end infinite; color: #4a8eff; }

/* ── Node pulse ── */
@keyframes nodePulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(173, 199, 255, 0.4); }
  50% { box-shadow: 0 0 20px 4px rgba(173, 199, 255, 0.15); }
}

/* ── Flow dash ── */
@keyframes flowDash {
  to { stroke-dashoffset: -24; }
}
</style>
