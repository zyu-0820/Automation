<template>
  <div class="config-view">
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:4px">
        <el-button text @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div>
          <h2>Configuration Files</h2>
          <span class="subtitle" v-if="service">{{ service.name }}</span>
        </div>
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

    <!-- Diff Preview Dialog -->
    <el-dialog
      v-model="diffDialogVisible"
      width="960px"
      :close-on-click-modal="false"
      destroy-on-close
      class="diff-dialog"
    >
      <template #header>
        <div class="diff-header">
          <span class="diff-title">Review Changes</span>
          <span class="diff-stats">
            <span class="stat-add">+{{ diffStats.additions }}</span>
            <span class="stat-del">−{{ diffStats.deletions }}</span>
          </span>
        </div>
      </template>

      <div class="diff-outer" v-if="diffPairs.length > 0">
        <!-- Column headers — fixed, no horizontal scroll -->
        <div class="diff-column-headers">
          <div class="diff-col-label">Before (Original)</div>
          <div class="diff-col-label">After (Modified)</div>
        </div>

        <!-- Body: vertical scroll only, each column scrolls horizontally (scrollbar hidden) -->
        <div class="diff-body">
          <div class="diff-columns">
            <!-- LEFT column -->
            <div class="diff-col" ref="leftColScroll" @scroll="onColScroll('left')">
              <div class="diff-col-inner" :style="{ minWidth: leftColWidth + 'px' }">
                <div
                  v-for="(pair, idx) in diffPairs"
                  :key="'l' + idx"
                  class="diff-cell"
                  :class="{
                    'diff-cell-remove': pair.type === 'remove',
                    'diff-cell-modify': pair.type === 'modify',
                    'diff-cell-placeholder': pair.left === null,
                  }"
                >
                  <span class="line-num">{{ pair.leftNum || '' }}</span>
                  <span class="line-text">
                    <template v-if="pair.type === 'modify' && pair.left !== null">
                      <span class="inline-same">{{ pair.inline.prefix }}</span>
                      <span class="inline-del">{{ pair.inline.oldMid }}</span>
                      <span class="inline-same">{{ pair.inline.suffix }}</span>
                    </template>
                    <template v-else>{{ pair.left || '' }}</template>
                  </span>
                </div>
              </div>
            </div>

            <!-- RIGHT column -->
            <div class="diff-col" ref="rightColScroll" @scroll="onColScroll('right')">
              <div class="diff-col-inner" :style="{ minWidth: rightColWidth + 'px' }">
                <div
                  v-for="(pair, idx) in diffPairs"
                  :key="'r' + idx"
                  class="diff-cell"
                  :class="{
                    'diff-cell-add': pair.type === 'add',
                    'diff-cell-modify': pair.type === 'modify',
                    'diff-cell-placeholder': pair.right === null,
                  }"
                >
                  <span class="line-num">{{ pair.rightNum || '' }}</span>
                  <span class="line-text">
                    <template v-if="pair.type === 'modify' && pair.right !== null">
                      <span class="inline-same">{{ pair.inline.prefix }}</span>
                      <span class="inline-add">{{ pair.inline.newMid }}</span>
                      <span class="inline-same">{{ pair.inline.suffix }}</span>
                    </template>
                    <template v-else>{{ pair.right || '' }}</template>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Horizontal scroll bar row — always visible -->
        <div class="diff-hscroll-row">
          <div class="diff-hscroll-track" ref="leftHScroll" @scroll="onHScroll('left')">
            <div class="diff-hscroll-spacer" :style="{ width: leftColWidth + 'px' }"></div>
          </div>
          <div class="diff-hscroll-track" ref="rightHScroll" @scroll="onHScroll('right')">
            <div class="diff-hscroll-spacer" :style="{ width: rightColWidth + 'px' }"></div>
          </div>
        </div>
      </div>
      <div v-else class="diff-empty">
        <el-empty description="No changes detected" :image-size="80" />
      </div>

      <template #footer>
        <el-button @click="diffDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="confirmSave">
          Confirm &amp; Save
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
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
const originalContent = ref('')
const saving = ref(false)
const editorView = shallowRef(null)

// Diff dialog state
const diffDialogVisible = ref(false)
const diffPairs = ref([])
const diffStats = ref({ additions: 0, deletions: 0 })

// Column scroll & scroll track refs
const leftColScroll = ref(null)
const rightColScroll = ref(null)
const leftHScroll = ref(null)
const rightHScroll = ref(null)

// Per-column content width for horizontal scroll
const leftColWidth = ref(400)
const rightColWidth = ref(400)
let hScrollLock = false

function calcColWidths() {
  const oldLines = originalContent.value.split('\n')
  const newLines = editContent.value.split('\n')
  const oldMax = oldLines.reduce((max, l) => Math.max(max, l.length), 0)
  const newMax = newLines.reduce((max, l) => Math.max(max, l.length), 0)
  leftColWidth.value = Math.max(400, Math.ceil(oldMax * 7.8 + 56))
  rightColWidth.value = Math.max(400, Math.ceil(newMax * 7.8 + 56))
}

function syncScrollLeft(val, source) {
  // Sync all 4 elements, skipping only the source that fired the event
  if (leftColScroll.value && leftColScroll.value !== source) leftColScroll.value.scrollLeft = val
  if (rightColScroll.value && rightColScroll.value !== source) rightColScroll.value.scrollLeft = val
  if (leftHScroll.value && leftHScroll.value !== source) leftHScroll.value.scrollLeft = val
  if (rightHScroll.value && rightHScroll.value !== source) rightHScroll.value.scrollLeft = val
}

function onColScroll(side) {
  if (hScrollLock) return
  hScrollLock = true
  const src = side === 'left' ? leftColScroll.value : rightColScroll.value
  syncScrollLeft(src?.scrollLeft || 0, src)
  requestAnimationFrame(() => { hScrollLock = false })
}

function onHScroll(side) {
  if (hScrollLock) return
  hScrollLock = true
  const src = side === 'left' ? leftHScroll.value : rightHScroll.value
  syncScrollLeft(src?.scrollLeft || 0, src)
  requestAnimationFrame(() => { hScrollLock = false })
}

// ----- Side-by-side diff (LCS + modify merge + inline highlights) -----

function levenshteinSimilarity(a, b) {
  const m = a.length, n = b.length
  if (m === 0 && n === 0) return 1
  const dp = new Int32Array(n + 1)
  for (let j = 0; j <= n; j++) dp[j] = j
  for (let i = 1; i <= m; i++) {
    let prev = dp[0]
    dp[0] = i
    for (let j = 1; j <= n; j++) {
      const temp = dp[j]
      if (a[i - 1] === b[j - 1]) {
        dp[j] = prev
      } else {
        dp[j] = Math.min(dp[j], dp[j - 1], prev) + 1
      }
      prev = temp
    }
  }
  return 1 - dp[n] / Math.max(m, n)
}

function inlineDiff(oldStr, newStr) {
  // Find common prefix
  let pre = 0
  const minLen = Math.min(oldStr.length, newStr.length)
  while (pre < minLen && oldStr[pre] === newStr[pre]) pre++

  // Find common suffix (after prefix)
  let suf = 0
  const oldRem = oldStr.length - pre
  const newRem = newStr.length - pre
  const maxSuf = Math.min(oldRem, newRem)
  while (suf < maxSuf && oldStr[oldStr.length - 1 - suf] === newStr[newStr.length - 1 - suf]) suf++

  return {
    prefix: oldStr.slice(0, pre),
    oldMid: oldStr.slice(pre, oldStr.length - suf),
    newMid: newStr.slice(pre, newStr.length - suf),
    suffix: suf > 0 ? oldStr.slice(oldStr.length - suf) : '',
  }
}

function computeSideBySide(oldText, newText) {
  const oldLines = oldText.split('\n')
  const newLines = newText.split('\n')
  const m = oldLines.length
  const n = newLines.length

  // LCS table
  const dp = Array.from({ length: m + 1 }, () => new Int32Array(n + 1))
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (oldLines[i - 1] === newLines[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
      }
    }
  }

  // Backtrack — produce raw pairs
  const raw = []
  let i = m, j = n
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
      raw.unshift({ type: 'same', left: oldLines[i - 1], right: newLines[j - 1], leftNum: i, rightNum: j })
      i--; j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      raw.unshift({ type: 'add', left: null, right: newLines[j - 1], leftNum: null, rightNum: j })
      j--
    } else {
      raw.unshift({ type: 'remove', left: oldLines[i - 1], right: null, leftNum: i, rightNum: null })
      i--
    }
  }

  // Post-process: merge adjacent remove+add into modify when related
  function commonPrefixLen(a, b) {
    let i = 0
    const lim = Math.min(a.length, b.length)
    while (i < lim && a[i] === b[i]) i++
    return i
  }

  function isModifyPair(a, b) {
    // Two lines are a "modify" if they share a significant common prefix
    // (same config key) OR have high overall similarity (minor value tweak)
    const cpl = commonPrefixLen(a, b)
    const minLen = Math.min(a.length, b.length)
    const prefixRatio = minLen > 0 ? cpl / minLen : 0
    // Shared prefix ≥ 40% of the shorter line → same key, different value
    if (prefixRatio >= 0.4) return true
    // Or high character-level similarity → small edit on same-length line
    if (levenshteinSimilarity(a, b) >= 0.5) return true
    return false
  }

  const pairs = []
  let additions = 0, deletions = 0
  for (let k = 0; k < raw.length; k++) {
    const cur = raw[k]
    const next = raw[k + 1]

    if (cur.type === 'remove' && next && next.type === 'add' && isModifyPair(cur.left, next.right)) {
      const idiff = inlineDiff(cur.left, next.right)
      pairs.push({
        type: 'modify',
        left: cur.left,
        right: next.right,
        leftNum: cur.leftNum,
        rightNum: next.rightNum,
        inline: idiff,
      })
      k++
    } else if (cur.type === 'add' && next && next.type === 'remove' && isModifyPair(next.left, cur.right)) {
      const idiff = inlineDiff(next.left, cur.right)
      pairs.push({
        type: 'modify',
        left: next.left,
        right: cur.right,
        leftNum: next.leftNum,
        rightNum: cur.rightNum,
        inline: idiff,
      })
      k++
    } else if (cur.type === 'add') {
      additions++
      pairs.push(cur)
    } else if (cur.type === 'remove') {
      deletions++
      pairs.push(cur)
    } else {
      pairs.push(cur)
    }
  }

  return { pairs, stats: { additions, deletions } }
}

function buildDiff() {
  const { pairs, stats } = computeSideBySide(originalContent.value, editContent.value)
  diffPairs.value = pairs
  diffStats.value = stats
  calcColWidths()
}

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
  originalContent.value = data.content
}

async function handleSave() {
  if (editContent.value === originalContent.value) {
    ElMessage.info('No changes detected.')
    return
  }
  buildDiff()
  diffDialogVisible.value = true
}

async function confirmSave() {
  saving.value = true
  try {
    await configApi.updateConfig(serviceId.value, activeFile.value, editContent.value, activeDir.value)
    originalContent.value = editContent.value
    diffPairs.value = []
    ElMessage.success('Configuration saved. Original file backed up.')
    diffDialogVisible.value = false
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

<style>
/* Side-by-side diff dialog — unscoped because el-dialog teleports to body */
.diff-dialog .diff-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.diff-dialog .diff-title {
  font-size: 16px;
  font-weight: 600;
}
.diff-dialog .diff-stats {
  font-size: 14px;
  font-family: 'Consolas', 'Monaco', monospace;
  display: flex;
  gap: 14px;
}
.diff-dialog .stat-add {
  color: #67c23a;
  font-weight: 600;
}
.diff-dialog .stat-del {
  color: #f56c6c;
  font-weight: 600;
}

/* Outer wrapper — fixed border, no scroll */
.diff-dialog .diff-outer {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

/* Column headers — fixed, no scroll */
.diff-dialog .diff-column-headers {
  display: flex;
  border-bottom: 1px solid #e4e7ed;
}
.diff-dialog .diff-col-label {
  flex: 1;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  padding: 6px 0;
  background: #f5f7fa;
}
.diff-dialog .diff-col-label:first-child {
  border-right: 1px solid #e4e7ed;
}

/* Body: vertical scroll only */
.diff-dialog .diff-body {
  max-height: 440px;
  overflow-y: auto;
  overflow-x: hidden;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}
.diff-dialog .diff-columns {
  display: flex;
}

/* Each column — native scroll, scrollbar hidden */
.diff-dialog .diff-col {
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;          /* Firefox */
  -ms-overflow-style: none;       /* IE */
}
.diff-dialog .diff-col::-webkit-scrollbar {
  display: none;                  /* Chrome/Safari */
}
.diff-dialog .diff-col:first-child {
  border-right: 1px solid #e4e7ed;
}

/* Inner wrapper — sets min-width to force scroll */
.diff-dialog .diff-col-inner {
  min-width: 400px;
}

/* Horizontal scroll bar row — always visible at bottom */
.diff-dialog .diff-hscroll-row {
  display: flex;
  height: 14px;
  border-top: 1px solid #e4e7ed;
}
.diff-dialog .diff-hscroll-track {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
}
.diff-dialog .diff-hscroll-track:first-child {
  border-right: 1px solid #e4e7ed;
}
.diff-dialog .diff-hscroll-track::-webkit-scrollbar {
  height: 14px;
}
.diff-dialog .diff-hscroll-track::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 7px;
}
.diff-dialog .diff-hscroll-track::-webkit-scrollbar-track {
  background: #f5f7fa;
}
.diff-dialog .diff-hscroll-spacer {
  height: 1px;
}

/* Each cell = one row in one column */
.diff-dialog .diff-cell {
  display: flex;
  padding: 0 4px;
  min-height: 22px;
  border-bottom: 1px solid #f0f0f0;
  background: #fff;
}

/* Line numbers — sticky so they stay visible during horizontal scroll */
.diff-dialog .line-num {
  width: 40px;
  flex-shrink: 0;
  text-align: right;
  color: #bbb;
  padding-right: 8px;
  user-select: none;
  position: sticky;
  left: 0;
  z-index: 1;
}
/* Inherit cell background for sticky line-num */
.diff-dialog .diff-cell .line-num {
  background: inherit;
}
.diff-dialog .diff-cell-remove .line-num {
  background: #ffebe9;
}
.diff-dialog .diff-cell-add .line-num {
  background: #e6ffec;
}
.diff-dialog .diff-cell-modify .line-num {
  background: #fff7e6;
}
.diff-dialog .diff-cell-placeholder .line-num {
  background: #f9f9f9;
}

/* Line text — natural width, outer wrapper scrolls */
.diff-dialog .line-text {
  white-space: pre;
}

/* Removed row — red */
.diff-dialog .diff-cell-remove {
  background: #ffebe9 !important;
}
.diff-dialog .diff-cell-remove .line-num {
  color: #f56c6c;
}

/* Added row — green */
.diff-dialog .diff-cell-add {
  background: #e6ffec !important;
}
.diff-dialog .diff-cell-add .line-num {
  color: #67c23a;
}

/* Modified row — orange */
.diff-dialog .diff-cell-modify {
  background: #fff7e6 !important;
}
.diff-dialog .diff-cell-modify .line-num {
  color: #e6a23c;
}

/* Placeholder cell (empty side of add/remove) */
.diff-dialog .diff-cell-placeholder {
  background: #f9f9f9 !important;
}

/* Inline highlights within modified lines */
.diff-dialog .inline-same {
  /* unchanged portion — inherit background from parent */
}
.diff-dialog .inline-del {
  background: #fbb4b4;
  border-radius: 2px;
  padding: 0 1px;
}
.diff-dialog .inline-add {
  background: #a3e635;
  border-radius: 2px;
  padding: 0 1px;
}

/* Empty cell placeholders */
.diff-dialog .diff-cell-empty {
  background: #f9f9f9 !important;
}

.diff-dialog .diff-empty {
  padding: 20px 0;
}
</style>
