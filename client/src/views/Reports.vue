<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t('reports.title') }}</h2>
      <p>{{ t('reports.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="isEmpty" class="card">
      <p class="empty-note">{{ t('common.noData') }}</p>
    </div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.quarterly.title') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.quarterly.quarter') }}</th>
                <th>{{ t('reports.quarterly.totalOrders') }}</th>
                <th>{{ t('reports.quarterly.totalRevenue') }}</th>
                <th>{{ t('reports.quarterly.avgOrderValue') }}</th>
                <th>{{ t('reports.quarterly.fulfillmentRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td><strong>{{ q.quarter }}</strong></td>
                <td>{{ q.total_orders }}</td>
                <td>{{ formatMoney(q.total_revenue, 2) }}</td>
                <td>{{ formatMoney(q.avg_order_value, 2) }}</td>
                <td>
                  <span :class="getFulfillmentClass(q.fulfillment_rate)">
                    {{ q.fulfillment_rate }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.trend.title') }}</h3>
        </div>
        <div class="chart-container">
          <div class="bar-chart">
            <div v-for="row in monthlyRows" :key="row.month" class="bar-wrapper">
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: row.barHeight + 'px' }"
                  :title="formatMoney(row.revenue, 2)"
                ></div>
              </div>
              <div class="bar-label">{{ row.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.mom.title') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.mom.month') }}</th>
                <th>{{ t('reports.mom.orders') }}</th>
                <th>{{ t('reports.mom.revenue') }}</th>
                <th>{{ t('reports.mom.change') }}</th>
                <th>{{ t('reports.mom.growthRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in monthlyRows" :key="row.month">
                <td><strong>{{ row.label }}</strong></td>
                <td>{{ row.order_count }}</td>
                <td>{{ formatMoney(row.revenue, 2) }}</td>
                <td>
                  <span v-if="row.changeText" :class="row.changeClass">{{ row.changeText }}</span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="row.growthText" :class="row.changeClass">{{ row.growthText }}</span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalRevenue') }}</div>
          <div class="stat-value">{{ formatMoney(totalRevenue, 2) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.avgMonthlyRevenue') }}</div>
          <div class="stat-value">{{ formatMoney(avgMonthlyRevenue, 2) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalOrders') }}</div>
          <div class="stat-value">{{ totalOrders }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.bestQuarter') }}</div>
          <div class="stat-value">{{ bestQuarter }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const MONTH_KEYS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
const MAX_BAR_HEIGHT = 200 // px, must match .bar-container height

// Coerce possibly-missing API numbers to a finite number
const num = (v) => (Number.isFinite(Number(v)) ? Number(v) : 0)

export default {
  name: 'Reports',
  setup() {
    const { t, currentCurrency } = useI18n()
    const { selectedPeriod, selectedLocation, selectedCategory, selectedStatus, getCurrentFilters } = useFilters()

    const loading = ref(true)
    const error = ref(null)
    const quarterlyData = ref([])
    const monthlyData = ref([])

    const loadData = async () => {
      loading.value = true
      error.value = null
      try {
        const filters = getCurrentFilters()
        const [quarterly, monthly] = await Promise.all([
          api.getQuarterlyReports(filters),
          api.getMonthlyTrends(filters)
        ])
        quarterlyData.value = Array.isArray(quarterly) ? quarterly : []
        monthlyData.value = Array.isArray(monthly) ? monthly : []
      } catch (err) {
        error.value = t('reports.loadError')
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    // Reload whenever any global filter changes
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadData()
    })

    onMounted(() => {
      loadData()
    })

    const formatMoney = (amount, decimals = 0) =>
      formatCurrencyWithDecimals(num(amount), currentCurrency.value, decimals)

    // Sign is taken from the raw (USD) delta, so it stays correct after JPY conversion/rounding
    const formatSignedMoney = (amount) => {
      if (amount > 0) return '+' + formatMoney(amount, 2)
      if (amount < 0) return '-' + formatMoney(Math.abs(amount), 2)
      return formatMoney(0, 2)
    }

    // Convert "YYYY-MM" to a localized "Mon YYYY"; falls back to the raw input (or '-') if malformed
    const formatMonth = (monthStr) => {
      if (typeof monthStr !== 'string') return '-'
      const match = /^(\d{4})-(\d{1,2})$/.exec(monthStr.trim())
      if (!match) return monthStr || '-'
      const key = MONTH_KEYS[parseInt(match[2], 10) - 1]
      if (!key) return monthStr
      return `${t('months.' + key)} ${match[1]}`
    }

    const getFulfillmentClass = (rate) => {
      const r = num(rate)
      if (r >= 90) return 'badge success'
      if (r >= 75) return 'badge warning'
      return 'badge danger'
    }

    const isEmpty = computed(() => quarterlyData.value.length === 0 && monthlyData.value.length === 0)

    const totalRevenue = computed(() => monthlyData.value.reduce((s, m) => s + num(m.revenue), 0))

    const avgMonthlyRevenue = computed(() =>
      monthlyData.value.length ? totalRevenue.value / monthlyData.value.length : 0
    )

    const totalOrders = computed(() => monthlyData.value.reduce((s, m) => s + num(m.order_count), 0))

    const bestQuarter = computed(() => {
      let best = null
      for (const q of quarterlyData.value) {
        if (!best || num(q.total_revenue) > num(best.total_revenue)) best = q
      }
      return best && best.quarter ? best.quarter : '-'
    })

    // Computed once per data change (not once per bar per render)
    const maxRevenue = computed(() =>
      monthlyData.value.reduce((max, m) => Math.max(max, num(m.revenue)), 0)
    )

    // One row per month: label, bar height and change vs. the previous month
    const monthlyRows = computed(() =>
      monthlyData.value.map((m, i, arr) => {
        const revenue = num(m.revenue)
        const row = {
          month: m.month,
          label: formatMonth(m.month),
          order_count: num(m.order_count),
          revenue,
          barHeight: maxRevenue.value > 0 ? (revenue / maxRevenue.value) * MAX_BAR_HEIGHT : 0,
          changeText: '',
          growthText: '',
          changeClass: ''
        }
        if (i > 0) {
          const prev = num(arr[i - 1].revenue)
          const change = revenue - prev
          row.changeText = formatSignedMoney(change)
          row.changeClass = change > 0 ? 'positive-change' : change < 0 ? 'negative-change' : ''
          if (prev === 0) {
            row.growthText = t('reports.mom.notAvailable') // growth from a zero base is undefined
          } else {
            const rate = (change / prev) * 100
            row.growthText = (rate > 0 ? '+' : '') + rate.toFixed(1) + '%'
          }
        }
        return row
      })
    )

    return {
      t,
      loading,
      error,
      quarterlyData,
      monthlyRows,
      isEmpty,
      totalRevenue,
      avgMonthlyRevenue,
      totalOrders,
      bestQuarter,
      formatMoney,
      getFulfillmentClass
    }
  }
}
</script>

<style scoped>
.reports {
  padding: 0;
}

.empty-note {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
  margin: 0;
}

.reports-table {
  width: 100%;
  border-collapse: collapse;
}

.reports-table th {
  background: var(--surface-2);
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 2px solid var(--border);
}

.reports-table td {
  padding: 0.75rem;
  border-bottom: 1px solid var(--border);
}

.reports-table tr:hover {
  background: var(--surface-2);
}

.chart-container {
  padding: 2rem 1rem;
  min-height: 300px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: 0.5rem;
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  background: linear-gradient(to top, #3b82f6, #60a5fa);
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  cursor: pointer;
}

.bar:hover {
  background: linear-gradient(to top, #2563eb, #3b82f6);
}

.bar-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: 1.5rem;
}

.stats-grid {
  margin-top: 1.5rem;
}

.positive-change {
  color: var(--success-text);
  font-weight: 600;
}

.negative-change {
  color: var(--danger-text);
  font-weight: 600;
}
</style>
