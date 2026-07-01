<template>
  <el-container style="min-height: 100vh">
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar-container">
      <div class="sidebar-logo">
        <h2 v-if="!isCollapsed">JSM</h2>
        <span v-if="!isCollapsed">Java Service Manager</span>
        <h2 v-else class="sidebar-logo-collapsed">J</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        :collapse="isCollapsed"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        class="sidebar-menu"
      >
        <el-menu-item index="/servers">
          <el-icon><Monitor /></el-icon>
          <template #title>Servers</template>
        </el-menu-item>
        <el-menu-item index="/multi-server">
          <el-icon><Operation /></el-icon>
          <template #title>Batch Operations</template>
        </el-menu-item>
        <el-menu-item index="/operations">
          <el-icon><Tickets /></el-icon>
          <template #title>Operation Logs</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapsed = !isCollapsed">
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
          <div class="header-breadcrumb">
            <el-breadcrumb>
              <el-breadcrumb-item :to="{ path: '/' }">Home</el-breadcrumb-item>
              <el-breadcrumb-item v-if="currentRoute" :to="{ path: currentRoute }">
                {{ currentRoute }}
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const isCollapsed = ref(false)

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/servers')) return '/servers'
  if (path.startsWith('/services')) return ''
  return path
})
const currentRoute = computed(() => route.path)
</script>

<style scoped>
.sidebar-container {
  background-color: #304156;
  transition: width 0.3s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #263445;
  color: #fff;
  gap: 8px;
  flex-shrink: 0;
  transition: all 0.3s ease;
}
.sidebar-logo h2 {
  margin: 0;
  font-size: 18px;
  white-space: nowrap;
}
.sidebar-logo span {
  font-size: 12px;
  color: #bfcbd9;
  white-space: nowrap;
}
.sidebar-logo-collapsed {
  font-size: 20px !important;
}
.sidebar-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}
.el-header {
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  padding: 0 20px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
  transition: color 0.2s;
  flex-shrink: 0;
}
.collapse-btn:hover {
  color: #409eff;
}
.header-breadcrumb {
  display: flex;
  align-items: center;
}
</style>
