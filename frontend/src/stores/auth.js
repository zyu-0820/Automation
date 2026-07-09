import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const STORAGE_KEY = 'jsm_auth'

// Default admin credentials
const DEFAULT_USERNAME = 'admin'
const DEFAULT_PASSWORD = '123456'

function loadFromStorage() {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    if (data) {
      return JSON.parse(data)
    }
  } catch {
    // ignore
  }
  return null
}

function saveToStorage(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

function clearStorage() {
  localStorage.removeItem(STORAGE_KEY)
}

export const useAuthStore = defineStore('auth', () => {
  const stored = loadFromStorage()

  // Initialize credentials with defaults or stored values
  const username = ref(stored?.username || DEFAULT_USERNAME)
  const password = ref(stored?.password || DEFAULT_PASSWORD)
  // isLoggedIn: only true if the user has explicitly logged in this session (or previous persisted session)
  const isLoggedIn = ref(stored?.isLoggedIn || false)

  const isAuthenticated = computed(() => isLoggedIn.value)

  // Persist initial defaults if nothing stored yet
  if (!stored) {
    saveToStorage({
      username: DEFAULT_USERNAME,
      password: DEFAULT_PASSWORD,
      isLoggedIn: false,
    })
  }

  function persist() {
    saveToStorage({
      username: username.value,
      password: password.value,
      isLoggedIn: isLoggedIn.value,
    })
  }

  function login(inputUsername, inputPassword) {
    if (inputUsername === username.value && inputPassword === password.value) {
      isLoggedIn.value = true
      persist()
      return { success: true }
    }
    return { success: false, message: '用户名或密码错误' }
  }

  function logout() {
    isLoggedIn.value = false
    persist()
  }

  function changePassword(oldPassword, newPassword) {
    if (oldPassword !== password.value) {
      return { success: false, message: '原密码错误' }
    }
    if (!newPassword || newPassword.length < 1) {
      return { success: false, message: '新密码不能为空' }
    }
    password.value = newPassword
    persist()
    return { success: true }
  }

  return {
    username,
    password,
    isAuthenticated,
    login,
    logout,
    changePassword,
  }
})
