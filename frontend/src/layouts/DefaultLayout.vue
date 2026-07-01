<template>
  <el-container style="min-height: 100vh">
    <el-aside width="220px">
      <div class="sidebar-logo">
        <h2>JSM</h2>
        <span>Java Service Manager</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/servers">
          <el-icon><Monitor /></el-icon>
          <span>Servers</span>
        </el-menu-item>
        <el-menu-item index="/multi-server">
          <el-icon><Operation /></el-icon>
          <span>Batch Operations</span>
        </el-menu-item>
        <el-menu-item index="/operations">
          <el-icon><Tickets /></el-icon>
          <span>Operation Logs</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-breadcrumb">
          <el-breadcrumb>
            <el-breadcrumb-item :to="{ path: '/' }">Home</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute" :to="{ path: currentRoute }">
              {{ currentRoute }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/servers')) return '/servers'
  if (path.startsWith('/services')) return ''
  return path
})
const currentRoute = computed(() => route.path)
</script>

<style scoped>
.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #263445;
  color: #fff;
  gap: 8px;
}
.sidebar-logo h2 {
  margin: 0;
  font-size: 18px;
}
.sidebar-logo span {
  font-size: 12px;
  color: #bfcbd9;
}
.el-header {
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  padding: 0 20px;
}
.el-menu {
  border-right: none;
}
</style>
