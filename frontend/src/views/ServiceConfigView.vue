<template>
  <div class="config-view">
    <div class="page-header">
      <div>
        <h2>Configuration Files</h2>
        <span class="subtitle" v-if="service">{{ service.name }}</span>
      </div>
    </div>

    <div class="config-layout" v-if="service">
      <div class="file-list">
        <h4>Files</h4>
        <div class="ext-filter">
          <el-input
            v-model="extFilter"
            size="small"
            placeholder="yml,yaml,xml"
            @change="loadFiles"
          >
            <template #prepend>Ext</template>
          </el-input>
        </div>
        <el-menu v-if="files.length > 0" :default-active="activeKey" @select="handleSelect">
          <el-menu-item v-for="f in files" :key="f.dir + '/' + f.name" :index="f.dir + '/' + f.name">
            <el-icon><Document /></el-icon>
            <span class="file-item">
              <span class="file-name">{{ f.name }}</span>
              <el-tag size="small" type="info">{{ f.dir }}</el-tag>
            </span>
          </el-menu-item>
        </el-menu>
        <el-empty v-else description="No matching config files" />
      </div>

      <div class="editor-area">
        <div v-if="activeFile" class="editor-header">
          <span class="file-path">{{ activeDir }}/{{ activeFile }}</span>
          <div class="editor-actions">
            <el-button size="small" text @click="toggleSearch">
              <el-icon><Search /></el-icon> Search
            </el-button>
            <el-button type="primary" size="small" @click="handleSave" :loading="saving">
              Save Changes
            </el-button>
          </div>
        </div>

        <div v-if="activeFile" class="codemirror-wrapper" ref="editorWrapper">
          <codemirror
            v-model="editContent"
            :extensions="cmExtensions"
            :style="{ height: '100%' }"
            :indent-with-tab="true"
            :tab-size="2"
            @ready="handleEditorReady"
          />
        </div>

        <div v-if="!activeFile" class="editor-placeholder">
          <el-empty description="Select a file from the left to edit" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Codemirror } from 'vue-codemirror'
import { yaml } from '@codemirror/lang-yaml'
import { xml } from '@codemirror/lang-xml'
import { search, searchKeymap, openSearchPanel, closeSearchPanel } from '@codemirror/search'
import { oneDark } from '@codemirror/theme-one-dark'
import { keymap } from '@codemirror/view'
import { EditorView } from '@codemirror/view'
import * as configApi from '@/api/configs'
import * as serviceApi from '@/api/services'
import * as serverApi from '@/api/servers'

const route = useRoute()
const serviceId = ref(parseInt(route.params.id))
const service = ref(null)
const server = ref(null)
const files = ref([])
const extFilter = ref('')
const activeFile = ref('')
const activeDir = ref('conf')
const activeKey = ref('')
const editContent = ref('')
const saving = ref(false)
const editorView = shallowRef(null)

const cmExtensions = computed(() => {
  const exts = []
  // language mode based on file extension
  if (activeFile.value.endsWith('.xml')) {
    exts.push(xml())
  } else {
    exts.push(yaml())
  }
  exts.push(oneDark)
  exts.push(search({ top: true }))
  exts.push(keymap.of(searchKeymap))
  exts.push(keymap.of([
    { key: 'Mod-s', run: () => { handleSave(); return true } },
  ]))
  exts.push(EditorView.theme({
    '&': { height: '100%' },
    '.cm-scroller': { overflow: 'auto' },
  }))
  return exts
})

function handleEditorReady(view) {
  editorView.value = view
}

function toggleSearch() {
  if (editorView.value) {
    openSearchPanel(editorView.value)
  }
}

async function loadService() {
  const { data } = await serviceApi.getService(serviceId.value)
  service.value = data
  // load server to get default config_extensions
  const srvResp = await serverApi.getServer(data.server_id)
  server.value = srvResp.data
  extFilter.value = server.value.config_extensions || 'yml,yaml,xml'
}

async function loadFiles() {
  const ext = extFilter.value.trim() || null
  const { data } = await configApi.getConfigFiles(serviceId.value, ext)
  files.value = data
}

async function handleSelect(key) {
  activeKey.value = key
  const [dir, ...nameParts] = key.split('/')
  const filename = nameParts.join('/')
  activeDir.value = dir
  activeFile.value = filename
  const { data } = await configApi.getConfigContent(serviceId.value, filename, dir)
  editContent.value = data.content
}

async function handleSave() {
  try {
    await ElMessageBox.confirm(
      'A backup of the original file will be created before saving. Continue?',
      'Confirm Save',
      { confirmButtonText: 'Save', cancelButtonText: 'Cancel', type: 'warning' }
    )
  } catch {
    return
  }

  saving.value = true
  try {
    await configApi.updateConfig(serviceId.value, activeFile.value, editContent.value, activeDir.value)
    ElMessage.success('Configuration saved. Original file backed up.')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Save failed')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await loadService()
  await loadFiles()
})
</script>

<style scoped>
.page-header {
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0 0 4px 0;
}
.subtitle {
  font-size: 13px;
  color: #909399;
}
.config-layout {
  display: flex;
  gap: 16px;
  height: calc(100vh - 160px);
}
.file-list {
  width: 260px;
  flex-shrink: 0;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow-y: auto;
}
.file-list h4 {
  margin: 0;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}
.ext-filter {
  padding: 8px 12px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}
.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 8px;
}
.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.editor-area {
  flex: 1;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #282c34;
  border-bottom: 1px solid #181a1f;
  color: #abb2bf;
}
.file-path {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}
.editor-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.codemirror-wrapper {
  flex: 1;
  overflow: hidden;
  background: #282c34;
}
.codemirror-wrapper :deep(.cm-editor) {
  height: 100%;
}
.codemirror-wrapper :deep(.cm-scroller) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
}
.codemirror-wrapper :deep(.cm-search) {
  background: #21252b;
  padding: 4px 8px;
}
.codemirror-wrapper :deep(.cm-textfield) {
  background: #1e1e1e;
  color: #abb2bf;
  border: 1px solid #3e4452;
  border-radius: 3px;
  padding: 2px 6px;
}
.editor-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
