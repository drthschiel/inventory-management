<template>
  <div class="app" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-backdrop" :class="{ visible: sidebarOpen }" @click="closeSidebar"></div>
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-brand">
        <div class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l9 5v10l-9 5-9-5V7l9-5zM12 12l9-5M12 12v10M12 12L3 7"/></svg>
        </div>
        <div class="brand-text">
          <h1>{{ t('nav.companyName') }}</h1>
          <span class="subtitle">{{ t('nav.subtitle') }}</span>
        </div>
        <button
          class="collapse-toggle"
          type="button"
          :aria-label="t('nav.toggleSidebar')"
          :title="t('nav.toggleSidebar')"
          :aria-expanded="String(!isCollapsed)"
          @click="toggleCollapsed"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="isCollapsed ? 'M9 6l6 6-6 6' : 'M15 6l-6 6 6 6'"/></svg>
        </button>
      </div>
      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          :title="item.label"
          :aria-label="item.label"
          class="nav-link"
          :class="{ active: $route.path === item.to }"
          @click="closeSidebar"
        >
          <svg class="nav-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="item.icon"/></svg>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>

    <div class="content-area">
      <header class="topbar">
        <button class="menu-button" type="button" aria-label="Open navigation" @click="sidebarOpen = true">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
        </button>
        <h2 class="topbar-title">{{ pageTitle }}</h2>
        <FilterBar class="topbar-filters" />
        <div class="topbar-actions">
          <LanguageSwitcher />
          <ProfileMenu
            @show-profile-details="showProfileDetails = true"
            @show-tasks="showTasks = true"
          />
        </div>
      </header>
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const route = useRoute()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Shell: sidebar navigation (slide-over drawer on narrow screens)
    const sidebarOpen = ref(false)
    const navItems = computed(() => [
      { to: '/', label: t('nav.overview'), icon: 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z' },
      { to: '/inventory', label: t('nav.inventory'), icon: 'M21 8l-9-5-9 5v8l9 5 9-5V8zM3.3 7.5L12 12.5l8.7-5M12 12.5V21' },
      { to: '/orders', label: t('nav.orders'), icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2 2 2 0 00-2-2h-2a2 2 0 00-2 2M9 12h6M9 16h4' },
      { to: '/spending', label: t('nav.finance'), icon: 'M12 2v20M17 6H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6' },
      { to: '/demand', label: t('nav.demandForecast'), icon: 'M3 17l6-6 4 4 8-8M15 7h6v6' },
      { to: '/restocking', label: t('nav.restocking'), icon: 'M21 12a9 9 0 11-3-6.7M21 4v5h-5' },
      { to: '/reports', label: t('nav.reports'), icon: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zM14 2v6h6M8 13h8M8 17h8M8 9h2' }
    ])
    const pageTitle = computed(() => {
      const match = navItems.value.find(n => n.to === route.path)
      return match ? match.label : t('nav.companyName')
    })
    const closeSidebar = () => { sidebarOpen.value = false }

    // Collapsible rail: manual choice (persisted) overrides auto-collapse at medium widths
    const STORAGE_KEY = 'sidebarCollapsed'
    let storedChoice = null
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw === 'true' || raw === 'false') storedChoice = raw === 'true'
    } catch (e) { /* storage unavailable */ }
    const manualCollapsed = ref(storedChoice)
    const isMobile = ref(false)
    const isMedium = ref(false)
    let mobileMql = null
    let mediumMql = null
    const syncMedia = () => {
      isMobile.value = mobileMql.matches
      isMedium.value = mediumMql.matches
    }
    const isCollapsed = computed(() => {
      if (isMobile.value) return false
      return manualCollapsed.value !== null ? manualCollapsed.value : isMedium.value
    })
    const toggleCollapsed = () => {
      manualCollapsed.value = !isCollapsed.value
      try {
        localStorage.setItem(STORAGE_KEY, String(manualCollapsed.value))
      } catch (e) { /* storage unavailable */ }
    }
    onMounted(() => {
      if (typeof window === 'undefined' || !window.matchMedia) return
      mobileMql = window.matchMedia('(max-width: 900px)')
      mediumMql = window.matchMedia('(max-width: 1200px)')
      syncMedia()
      mobileMql.addEventListener('change', syncMedia)
      mediumMql.addEventListener('change', syncMedia)
    })
    onBeforeUnmount(() => {
      if (mobileMql) mobileMql.removeEventListener('change', syncMedia)
      if (mediumMql) mediumMql.removeEventListener('change', syncMedia)
    })
    watch(() => route.path, closeSidebar)

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      navItems,
      pageTitle,
      sidebarOpen,
      closeSidebar,
      isCollapsed,
      toggleCollapsed,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
:root {
  color-scheme: dark;
  --bg: #0b1220;
  --sidebar-bg: #0a101c;
  --surface: #111c2e;
  --surface-2: #1e293b;
  --border: #263449;
  --border-strong: #334155;
  --text: #e2e8f0;
  --text-strong: #f8fafc;
  --text-muted: #94a3b8;
  --accent: #3b82f6;
  --accent-hover: #2563eb;
  --accent-soft: rgba(59, 130, 246, 0.15);
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --info: #3b82f6;
  --success-text: #34d399;
  --warning-text: #fbbf24;
  --danger-text: #f87171;
  --info-text: #60a5fa;
  --purple-text: #a78bfa;
  --success-bg: rgba(16, 185, 129, 0.16);
  --warning-bg: rgba(245, 158, 11, 0.16);
  --danger-bg: rgba(239, 68, 68, 0.16);
  --info-bg: rgba(59, 130, 246, 0.16);
  --success-border: rgba(16, 185, 129, 0.4);
  --warning-border: rgba(245, 158, 11, 0.4);
  --danger-border: rgba(239, 68, 68, 0.4);
  --info-border: rgba(59, 130, 246, 0.4);
  --radius: 12px;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 4px 16px rgba(0, 0, 0, 0.2);
  --shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.45);
  --sidebar-width: 240px;
  --sidebar-width-collapsed: 72px;
  --topbar-height: 64px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

::selection { background: rgba(59, 130, 246, 0.4); }

input, select, textarea, button { font-family: inherit; }

input, select, textarea {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border-strong);
}

input::placeholder, textarea::placeholder { color: #64748b; }

input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

option { background: var(--surface-2); color: var(--text); }

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 8px; border: 2px solid var(--bg); }
::-webkit-scrollbar-track { background: transparent; }

.app {
  min-height: 100vh;
  --sidebar-current: var(--sidebar-width);
}

.app.collapsed {
  --sidebar-current: var(--sidebar-width-collapsed);
}

/* Sidebar */
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: var(--sidebar-current);
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  z-index: 200;
  transition: transform 0.25s ease, width 0.25s ease;
  overflow-x: hidden;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  height: var(--topbar-height);
  padding: 0 1.25rem;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.brand-text { min-width: 0; }

.brand-text h1 {
  font-size: 0.938rem;
  font-weight: 700;
  color: var(--text-strong);
  letter-spacing: -0.01em;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.subtitle {
  display: block;
  font-size: 0.688rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 1rem 0.75rem;
  overflow-y: auto;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  color: var(--text-muted);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
  border-radius: 8px;
  position: relative;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-link:hover {
  color: var(--text-strong);
  background: rgba(148, 163, 184, 0.1);
}

.nav-link.active {
  color: var(--info-text);
  background: var(--accent-soft);
}

.nav-link.active::before {
  content: '';
  position: absolute;
  left: -0.75rem;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--accent);
}

.nav-icon { flex-shrink: 0; }

.sidebar-backdrop {
  display: none;
}

.collapse-toggle {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 8px;
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--text-muted);
  cursor: pointer;
}

.collapse-toggle:hover { color: var(--text-strong); background: var(--surface-2); }

.collapse-toggle:focus-visible,
.nav-link:focus-visible,
.menu-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.nav-label { white-space: nowrap; }

.app.collapsed .sidebar-brand {
  flex-direction: column;
  justify-content: center;
  gap: 0.375rem;
  padding: 0;
}
.app.collapsed .brand-text,
.app.collapsed .nav-label { display: none; }
.app.collapsed .collapse-toggle { margin-left: 0; width: 26px; height: 22px; }
.app.collapsed .nav-link { justify-content: center; padding: 0.75rem 0; }
.app.collapsed .nav-link.active::before { left: -0.75rem; }

/* Content area and top bar */
.content-area {
  margin-left: var(--sidebar-current);
  transition: margin-left 0.25s ease;
  min-height: 100vh;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  min-height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 0.5rem 2rem;
  background: rgba(11, 18, 32, 0.88);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
}

.topbar-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-strong);
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.topbar-filters { flex: 1; min-width: 0; }

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-left: auto;
}

.menu-button {
  display: none;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 8px;
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
}

.menu-button:hover { background: var(--surface-2); }

.main-content {
  flex: 1;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 1.75rem 2rem 2.5rem;
}

@media (max-width: 1280px) {
  .topbar { flex-wrap: wrap; row-gap: 0.5rem; }
  .topbar-filters { order: 5; flex-basis: 100%; }
}

@media (max-width: 900px) {
  .sidebar {
    transform: translateX(-100%);
    box-shadow: var(--shadow-lg);
  }
  .sidebar.open { transform: translateX(0); }
  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(2, 6, 15, 0.65);
    z-index: 150;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.25s ease;
  }
  .sidebar-backdrop.visible { opacity: 1; pointer-events: auto; }
  .content-area { margin-left: 0; }
  .menu-button { display: inline-flex; }
  .topbar { padding: 0.5rem 1rem; gap: 0.75rem; }
  .main-content { padding: 1.25rem 1rem 2rem; }
}

/* Page header */
.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-strong);
  margin-bottom: 0.375rem;
  letter-spacing: -0.025em;
}

.page-header p {
  color: var(--text-muted);
  font-size: 0.938rem;
}

/* Stat cards */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--surface);
  padding: 1.25rem 1.5rem;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  transition: border-color 0.2s ease;
}

.stat-card:hover {
  border-color: var(--border-strong);
}

.stat-label {
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-strong);
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value { color: var(--warning-text); }
.stat-card.success .stat-value { color: var(--success-text); }
.stat-card.danger .stat-value { color: var(--danger-text); }
.stat-card.info .stat-value { color: var(--info-text); }

/* Cards */
.card {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 1.5rem;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  margin-bottom: 1.25rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.875rem;
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-strong);
  letter-spacing: -0.01em;
}

/* Tables */
.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--surface-2);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

th {
  text-align: left;
  padding: 0.625rem 0.875rem;
  font-weight: 600;
  color: var(--text-muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

td {
  padding: 0.625rem 0.875rem;
  border-top: 1px solid var(--border);
  color: var(--text);
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: rgba(148, 163, 184, 0.07);
}

/* Badges */
.badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 999px;
  font-size: 0.688rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.badge.success,
.badge.increasing { background: var(--success-bg); color: var(--success-text); }

.badge.warning,
.badge.medium { background: var(--warning-bg); color: var(--warning-text); }

.badge.danger,
.badge.decreasing,
.badge.high { background: var(--danger-bg); color: var(--danger-text); }

.badge.info,
.badge.low { background: var(--info-bg); color: var(--info-text); }

.badge.stable { background: rgba(129, 140, 248, 0.16); color: #a5b4fc; }

/* Buttons */
.btn,
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  border: 1px solid transparent;
  background: var(--accent);
  color: #fff;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.btn:hover,
.btn-primary:hover { background: var(--accent-hover); }

.btn-secondary {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border-strong);
}

.btn-secondary:hover { background: var(--border-strong); }

/* Loading and error */
.loading {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
  font-size: 0.938rem;
}

.error {
  background: var(--danger-bg);
  border: 1px solid var(--danger-border);
  color: var(--danger-text);
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
