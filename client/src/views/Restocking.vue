<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

const { t, currentLocale, currentCurrency, translateProductName } = useI18n()

const STEP = 100
const DEBOUNCE_MS = 250

const loading = ref(true)
const error = ref(null)
const maxBudget = ref(0)
const budget = ref(0)
const recommendation = ref(null)
const fetching = ref(false)

const submitting = ref(false)
const submitError = ref(null)
const placedOrder = ref(null)

let debounceTimer = null
let requestId = 0

const items = computed(() => recommendation.value?.items ?? [])
const hasItems = computed(() => items.value.length > 0)

const money = (amount, decimals = 2) =>
  formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)

const formatDate = (dateString) => {
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString
  return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const trendClass = (trend) => ['increasing', 'decreasing', 'stable'].includes(trend) ? trend : 'stable'
const trendLabel = (trend) => {
  const key = `trends.${trend}`
  const label = t(key)
  return label === key ? trend : label
}

// Ignore out-of-order responses while the slider is moving
const loadRecommendations = async () => {
  const id = ++requestId
  fetching.value = true
  try {
    const data = await api.getRestockingRecommendations(budget.value)
    if (id !== requestId) return
    recommendation.value = data
    error.value = null
  } catch (err) {
    if (id !== requestId) return
    error.value = t('restocking.loadError')
    console.error(err)
  } finally {
    if (id === requestId) fetching.value = false
  }
}

const init = async () => {
  loading.value = true
  error.value = null
  try {
    // budget=0 reveals max_budget for the slider range
    const data = await api.getRestockingRecommendations(0)
    maxBudget.value = Math.ceil(data.max_budget)
    budget.value = 0
    recommendation.value = data
  } catch (err) {
    error.value = t('restocking.loadError')
    console.error(err)
  } finally {
    loading.value = false
  }
}

watch(budget, () => {
  placedOrder.value = null
  submitError.value = null
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadRecommendations, DEBOUNCE_MS)
})

const placeOrder = async () => {
  if (!hasItems.value || submitting.value) return
  // Flush any pending debounce so the order matches what the user sees
  clearTimeout(debounceTimer)
  submitting.value = true
  submitError.value = null
  placedOrder.value = null
  try {
    const order = await api.createRestockingOrder({
      budget: recommendation.value.budget,
      items: items.value.map(i => ({ sku: i.sku, quantity: i.quantity }))
    })
    placedOrder.value = order
    await loadRecommendations()
  } catch (err) {
    submitError.value = err.response?.data?.detail || err.message || t('restocking.orderError')
  } finally {
    submitting.value = false
  }
}

onMounted(init)
onBeforeUnmount(() => clearTimeout(debounceTimer))
</script>

<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error && !recommendation" class="error">{{ error }}</div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budget') }}</h3>
          <span class="budget-value">{{ formatCurrency(budget, currentCurrency) }}</span>
        </div>
        <input
          v-model.number="budget"
          type="range"
          class="budget-slider"
          min="0"
          :max="maxBudget"
          :step="STEP"
          :aria-label="t('restocking.budget')"
        />
        <div class="slider-scale">
          <span>{{ formatCurrency(0, currentCurrency) }}</span>
          <span>{{ t('restocking.maxBudget', { amount: formatCurrency(maxBudget, currentCurrency) }) }}</span>
        </div>
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <div v-if="recommendation" class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ formatCurrency(recommendation.budget, currentCurrency) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.totalCost') }}</div>
          <div class="stat-value">{{ formatCurrency(recommendation.total_cost, currentCurrency) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ formatCurrency(recommendation.remaining, currentCurrency) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.leadTime') }}</div>
          <div class="stat-value">{{ t('restocking.leadTimeDays', { days: recommendation.lead_time_days }) }}</div>
        </div>
      </div>

      <div v-if="placedOrder" class="success-message" role="status">
        <span>
          {{ t('restocking.orderSuccess', {
            orderNumber: placedOrder.order_number,
            date: formatDate(placedOrder.expected_delivery)
          }) }}
        </span>
        <router-link to="/orders">{{ t('restocking.viewOrders') }}</router-link>
      </div>
      <div v-if="submitError" class="error" role="alert">
        {{ t('restocking.orderError') }}: {{ submitError }}
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ items.length }})</h3>
          <button
            type="button"
            class="place-order-btn"
            :disabled="!hasItems || submitting || fetching"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
          </button>
        </div>

        <p v-if="!hasItems" class="empty-note">{{ t('restocking.emptyState') }}</p>
        <div v-else class="table-container" :class="{ stale: fetching }">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.sku') }}</th>
                <th>{{ t('restocking.name') }}</th>
                <th>{{ t('restocking.trend') }}</th>
                <th class="num">{{ t('restocking.forecastDemand') }}</th>
                <th class="num">{{ t('restocking.onHand') }}</th>
                <th class="num">{{ t('restocking.quantity') }}</th>
                <th class="num">{{ t('restocking.unitCost') }}</th>
                <th class="num">{{ t('restocking.lineTotal') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td><span :class="['badge', trendClass(item.trend)]">{{ trendLabel(item.trend) }}</span></td>
                <td class="num">{{ item.forecasted_demand.toLocaleString() }}</td>
                <td class="num">{{ item.quantity_on_hand.toLocaleString() }}</td>
                <td class="num"><strong>{{ item.quantity.toLocaleString() }}</strong></td>
                <td class="num">{{ money(item.unit_cost) }}</td>
                <td class="num"><strong>{{ money(item.total_cost) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-strong);
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
  cursor: pointer;
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.375rem;
  font-size: 0.813rem;
  color: var(--text-muted);
}

.num {
  text-align: right;
}

.stale {
  opacity: 0.6;
  transition: opacity 0.15s ease;
}

.empty-note {
  color: var(--text-muted);
  font-size: 0.938rem;
  padding: 1rem 0;
}

.place-order-btn {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: var(--border-strong);
  color: var(--text-muted);
  cursor: not-allowed;
}

.success-message {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  background: var(--success-bg);
  border: 1px solid var(--success-border);
  color: var(--success-text);
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
}

.success-message a {
  color: var(--success-text);
  font-weight: 600;
}
</style>
