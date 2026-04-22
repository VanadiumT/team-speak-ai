<template>
  <div id="app">
    <AppLayout />
  </div>
</template>

<script setup>
import AppLayout from './components/layout/AppLayout.vue'
import { useAppStore } from '@/stores/app'
import { onMounted } from 'vue'

const appStore = useAppStore()

onMounted(() => {
  appStore.initWebSocket()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, 'Helvetica Neue', sans-serif;
  background-color: #1a1a2e;
  color: #eaeaea;
  min-height: 100vh;
}

#app {
  min-height: 100vh;
}
</style>
