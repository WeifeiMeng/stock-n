<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import html2pdf from 'html2pdf.js';

const theme = ref(localStorage.getItem('theme') || 'light');
const date = ref(today());
const stocks = ref([]);
const loading = ref(false);
const runningFilter = ref(false);
const error = ref('');
const filterLogs = ref([]);
const filterSummary = ref('');
const filterResult = ref(null);
const pdfRef = ref(null);

const stockCount = computed(() => stocks.value.length);
const hasStocks = computed(() => stocks.value.length > 0);
const canExport = computed(() => hasStocks.value && !loading.value);

watch(theme, (value) => {
  document.documentElement.dataset.theme = value;
  localStorage.setItem('theme', value);
});

onMounted(() => {
  document.documentElement.dataset.theme = theme.value;
  queryStockN();
});

function today() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function calcPrices(basePrice) {
  const buy1 = basePrice * 1.03;
  const buy2 = basePrice * 1.04;
  const buy3 = basePrice * 1.05;

  return {
    buy1,
    profit1: buy1 * 1.05,
    loss1: buy1 * 0.95,
    buy2,
    profit2: buy2 * 1.05,
    loss2: buy2 * 0.95,
    buy3,
    profit3: buy3 * 1.05,
    loss3: buy3 * 0.95,
  };
}

function withPrices(item) {
  const prices = calcPrices(item.base_price);
  const warned =
    prices.profit1 > item.current_price ||
    prices.profit2 > item.current_price ||
    prices.profit3 > item.current_price;

  return { ...item, prices, warned };
}

async function queryStockN() {
  if (!date.value) {
    error.value = '请选择日期';
    return;
  }

  loading.value = true;
  error.value = '';
  stocks.value = [];

  try {
    const response = await fetch(`/stock-n/${date.value}`);
    if (!response.ok) {
      const detail = await readError(response);
      throw new Error(detail || `HTTP ${response.status}`);
    }
    const data = await response.json();
    stocks.value = Array.isArray(data) ? data.map(withPrices) : [];
  } catch (err) {
    error.value = `查询失败：${err.message}`;
  } finally {
    loading.value = false;
  }
}

async function readError(response) {
  try {
    const data = await response.json();
    return data.detail || data.message || '';
  } catch {
    return await response.text();
  }
}

function parseSseFrame(frame) {
  const lines = frame.split('\n');
  let event = 'message';
  let data = '';

  for (const line of lines) {
    if (line.startsWith('event: ')) {
      event = line.slice(7).trim();
    } else if (line.startsWith('data: ')) {
      data += line.slice(6);
    } else if (line.startsWith('data:')) {
      data += line.slice(5);
    }
  }

  if (!data) return null;

  try {
    return { event, data: JSON.parse(data) };
  } catch {
    return null;
  }
}

async function runFilter() {
  if (!date.value) {
    error.value = '请选择日期';
    return;
  }

  runningFilter.value = true;
  error.value = '';
  filterLogs.value = [];
  filterSummary.value = '';
  filterResult.value = null;

  try {
    const response = await fetch(`/stock-n/filter/stream?date=${encodeURIComponent(date.value)}`, {
      headers: { Accept: 'text/event-stream' },
    });

    if (!response.ok || !response.body) {
      const detail = await readError(response);
      throw new Error(detail || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop();

      for (const frame of frames) {
        const parsed = parseSseFrame(frame);
        if (!parsed) continue;

        if (parsed.event === 'progress') {
          const data = parsed.data;
          const passed = Boolean(data.stock?.passed);
          filterLogs.value.push({
            passed,
            text: `[${data.current}/${data.total}] ${data.stock.code} ${data.stock.name} - ${
              passed ? '通过' : data.stock.reason || '未通过'
            }`,
          });
          filterSummary.value = `进度 ${data.current}/${data.total}，通过 ${data.passed}，淘汰 ${data.rejected}`;
        }

        if (parsed.event === 'complete') {
          filterResult.value = parsed.data;
        }
      }
    }

    await queryStockN();
  } catch (err) {
    error.value = `筛选失败：${err.message}`;
  } finally {
    runningFilter.value = false;
  }
}

async function exportToPdf() {
  if (!canExport.value) return;

  await nextTick();
  const options = {
    margin: 10,
    filename: `N规则股票池_${date.value}.pdf`,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' },
  };

  await html2pdf().set(options).from(pdfRef.value).save();
}
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <h1>N 规则股票池</h1>
        <p>按交易日查询股票池，计算买入价、止盈价和止损价。</p>
      </div>

      <div class="top-actions">
        <button class="secondary-btn" :disabled="!canExport" @click="exportToPdf">导出 PDF</button>
        <label class="theme-toggle">
          <span>深色</span>
          <input v-model="theme" type="checkbox" true-value="dark" false-value="light" />
        </label>
      </div>
    </header>

    <section class="controls">
      <label>
        <span>交易日期</span>
        <input v-model="date" type="date" @change="queryStockN" />
      </label>
      <button :disabled="loading" @click="queryStockN">查询</button>
      <button class="run-btn" :disabled="runningFilter" @click="runFilter">
        {{ runningFilter ? '筛选中...' : '运行筛选' }}
      </button>
    </section>

    <section class="stats">
      <div>
        <strong>{{ loading ? '-' : stockCount }}</strong>
        <span>股票数量</span>
      </div>
      <div>
        <strong>{{ date }}</strong>
        <span>当前日期</span>
      </div>
      <div>
        <strong>{{ runningFilter ? '运行中' : '就绪' }}</strong>
        <span>筛选状态</span>
      </div>
    </section>

    <p v-if="error" class="error-message">{{ error }}</p>

    <section v-if="filterLogs.length || filterResult" class="filter-log">
      <p v-if="filterSummary" class="filter-summary">{{ filterSummary }}</p>
      <div v-if="filterResult" class="filter-result">
        <strong>筛选完成</strong>
        <span>
          涨停股票 {{ filterResult.zt_total }} 只，通过 {{ filterResult.passed_count }} 只，淘汰
          {{ filterResult.rejected_count }} 只，入库 {{ filterResult.stock_n_inserted }} 条。
        </span>
      </div>
      <ul>
        <li v-for="(log, index) in filterLogs" :key="index" :class="{ passed: log.passed }">
          {{ log.passed ? '通过' : '淘汰' }} {{ log.text }}
        </li>
      </ul>
    </section>

    <section class="table-panel">
      <div v-if="loading" class="state">加载中...</div>
      <div v-else-if="!hasStocks" class="state">当前日期没有股票池数据。</div>
      <div v-else class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>当前价</th>
              <th>基准价</th>
              <th class="group-1">买 1</th>
              <th class="group-1">止盈 1</th>
              <th class="group-1">止损 1</th>
              <th class="group-2">买 2</th>
              <th class="group-2">止盈 2</th>
              <th class="group-2">止损 2</th>
              <th class="group-3">买 3</th>
              <th class="group-3">止盈 3</th>
              <th class="group-3">止损 3</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="stock in stocks" :key="`${stock.code}-${stock.name}`" :class="{ warned: stock.warned }">
              <td class="code">{{ stock.code }}</td>
              <td class="name">{{ stock.name }}</td>
              <td>{{ stock.current_price.toFixed(2) }}</td>
              <td>{{ stock.base_price.toFixed(2) }}</td>
              <td class="buy group-1">{{ stock.prices.buy1.toFixed(2) }}</td>
              <td class="profit group-1">{{ stock.prices.profit1.toFixed(2) }}</td>
              <td class="loss group-1">{{ stock.prices.loss1.toFixed(2) }}</td>
              <td class="buy group-2">{{ stock.prices.buy2.toFixed(2) }}</td>
              <td class="profit group-2">{{ stock.prices.profit2.toFixed(2) }}</td>
              <td class="loss group-2">{{ stock.prices.loss2.toFixed(2) }}</td>
              <td class="buy group-3">{{ stock.prices.buy3.toFixed(2) }}</td>
              <td class="profit group-3">{{ stock.prices.profit3.toFixed(2) }}</td>
              <td class="loss group-3">{{ stock.prices.loss3.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <footer>数据仅供参考，不构成投资建议。</footer>

    <div class="pdf-export" ref="pdfRef">
      <h2>N 规则股票池</h2>
      <p>交易日期：{{ date }}，共 {{ stockCount }} 只股票</p>
      <table>
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>当前价</th>
            <th>基准价</th>
            <th>买 1</th>
            <th>止盈 1</th>
            <th>止损 1</th>
            <th>买 2</th>
            <th>止盈 2</th>
            <th>止损 2</th>
            <th>买 3</th>
            <th>止盈 3</th>
            <th>止损 3</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stock in stocks" :key="`pdf-${stock.code}-${stock.name}`">
            <td>{{ stock.code }}</td>
            <td>{{ stock.name }}</td>
            <td>{{ stock.current_price.toFixed(2) }}</td>
            <td>{{ stock.base_price.toFixed(2) }}</td>
            <td>{{ stock.prices.buy1.toFixed(2) }}</td>
            <td>{{ stock.prices.profit1.toFixed(2) }}</td>
            <td>{{ stock.prices.loss1.toFixed(2) }}</td>
            <td>{{ stock.prices.buy2.toFixed(2) }}</td>
            <td>{{ stock.prices.profit2.toFixed(2) }}</td>
            <td>{{ stock.prices.loss2.toFixed(2) }}</td>
            <td>{{ stock.prices.buy3.toFixed(2) }}</td>
            <td>{{ stock.prices.profit3.toFixed(2) }}</td>
            <td>{{ stock.prices.loss3.toFixed(2) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
