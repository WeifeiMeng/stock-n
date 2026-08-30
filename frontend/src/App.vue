<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { jsPDF } from 'jspdf';
import simHeiFontUrl from './assets/fonts/simhei.ttf?url';

const pdfFontName = 'SimHei';
let simHeiFontBase64Promise = null;

const theme = ref(localStorage.getItem('theme') || 'light');
const date = ref(today());
const stocks = ref([]);
const positions = ref([]);
const loading = ref(false);
const runningFilter = ref(false);
const updatingPositions = ref(false);
const error = ref('');
const filterLogs = ref([]);
const filterSummary = ref('');
const filterResult = ref(null);
const positionSummary = ref('');
const exportingPdf = ref(false);

const stockCount = computed(() => stocks.value.length);
const hasStocks = computed(() => stocks.value.length > 0);
const positionStocks = computed(() => positions.value);
const positionCount = computed(() => positions.value.length);
const hasPositions = computed(() => positions.value.length > 0);
const canExport = computed(
  () => (hasStocks.value || hasPositions.value) && !loading.value && !updatingPositions.value && !exportingPdf.value,
);

watch(theme, (value) => {
  document.documentElement.dataset.theme = value;
  localStorage.setItem('theme', value);
});

onMounted(() => {
  document.documentElement.dataset.theme = theme.value;
  queryStockN();
  queryPositions();
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

  return {
    ...item,
    highest_price: Number(item.highest_price ?? 0),
    lowest_price: Number(item.lowest_price ?? 0),
    buy1_price: Number(item.buy1_price) > 0 ? Number(item.buy1_price) : prices.buy1,
    buy_lots: Number(item.buy_lots ?? 0),
    buy_shares: Number(item.buy_shares ?? 0),
    buy_amount: Number(item.buy_amount ?? 0),
    position_triggered: Boolean(item.position_triggered),
    prices,
    warned,
  };
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

async function queryPositions() {
  if (!date.value) return;

  try {
    const response = await fetch(`/stock-position/${date.value}`);
    if (!response.ok) {
      const detail = await readError(response);
      throw new Error(detail || `HTTP ${response.status}`);
    }
    const data = await response.json();
    positions.value = Array.isArray(data)
      ? data.map((item) => ({
          ...item,
          base_price: Number(item.base_price ?? 0),
          highest_price: Number(item.highest_price ?? 0),
          lowest_price: Number(item.lowest_price ?? 0),
          buy1_price: Number(item.buy1_price ?? 0),
          buy_level: item.buy_level || 'B1',
          buy_lots: Number(item.buy_lots ?? 0),
          buy_shares: Number(item.buy_shares ?? 0),
          buy_amount: Number(item.buy_amount ?? 0),
          sell_date: item.sell_date || '',
          sell_price: Number(item.sell_price ?? 0),
          sell_amount: Number(item.sell_amount ?? 0),
          profit_amount: Number(item.profit_amount ?? 0),
          profit_rate: Number(item.profit_rate ?? 0),
          profit_status: item.profit_status || '',
          exit_reason: item.exit_reason || '',
          status: item.status || 'holding',
        }))
      : [];
  } catch (err) {
    error.value = `持仓加载失败：${err.message}`;
  }
}

async function updatePositions() {
  if (!date.value) {
    error.value = '请选择日期';
    return;
  }

  updatingPositions.value = true;
  error.value = '';
  positionSummary.value = '';

  try {
    const response = await fetch(`/stock-position/update?date=${encodeURIComponent(date.value)}`, {
      method: 'POST',
    });
    if (!response.ok) {
      const detail = await readError(response);
      throw new Error(detail || `HTTP ${response.status}`);
    }
    const result = await response.json();
    positionSummary.value = `持仓更新完成：检查历史持仓 ${result.open_positions_checked || 0} 条，卖出 ${result.positions_sold || 0} 条；读取 ${result.source_date} 股票池 ${result.source_total} 只，买入 ${result.positions_inserted} 条。`;
    await queryPositions();
  } catch (err) {
    error.value = `持仓更新失败：${err.message}`;
  } finally {
    updatingPositions.value = false;
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
    await queryPositions();
  } catch (err) {
    error.value = `筛选失败：${err.message}`;
  } finally {
    runningFilter.value = false;
  }
}

async function exportToPdf() {
  if (!canExport.value) return;

  exportingPdf.value = true;
  error.value = '';

  try {
    const doc = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'landscape' });
    await registerPdfFont(doc);
    const margin = 8;
    const pageHeight = doc.internal.pageSize.getHeight();
    let y = margin;

    const ensureSpace = (height) => {
      if (y + height <= pageHeight - margin) return;
      doc.addPage();
      y = margin;
    };

    const drawTitle = (title) => {
      doc.setFont(pdfFontName, 'bold');
      doc.setFontSize(14);
      doc.text(toPdfText(title), margin, y);
      y += 7;
    };

    const drawText = (text) => {
      doc.setFont(pdfFontName, 'normal');
      doc.setFontSize(9);
      doc.text(toPdfText(text), margin, y);
      y += 6;
    };

    const drawTable = (title, columns, rows) => {
      if (!rows.length) return;

      ensureSpace(18);
      doc.setFont(pdfFontName, 'bold');
      doc.setFontSize(11);
      doc.text(toPdfText(title), margin, y);
      y += 6;

      const headerHeight = 7;
      const rowHeight = 6;
      const tableWidth = columns.reduce((sum, column) => sum + column.width, 0);
      const startX = margin;

      const drawHeader = () => {
        doc.setFont(pdfFontName, 'bold');
        doc.setFontSize(7);
        doc.setFillColor(243, 244, 246);
        doc.rect(startX, y, tableWidth, headerHeight, 'F');

        let x = startX;
        for (const column of columns) {
          doc.rect(x, y, column.width, headerHeight);
          doc.text(toPdfText(column.label), x + 1.5, y + 4.8, { maxWidth: column.width - 3 });
          x += column.width;
        }
        y += headerHeight;
      };

      drawHeader();
      doc.setFont(pdfFontName, 'normal');
      doc.setFontSize(7);

      for (const row of rows) {
        if (y + rowHeight > pageHeight - margin) {
          doc.addPage();
          y = margin;
          drawHeader();
          doc.setFont(pdfFontName, 'normal');
          doc.setFontSize(7);
        }

        let x = startX;
        for (const column of columns) {
          const value = column.getValue(row);
          doc.rect(x, y, column.width, rowHeight);
          doc.text(toPdfText(value), x + 1.5, y + 4.2, { maxWidth: column.width - 3 });
          x += column.width;
        }
        y += rowHeight;
      }

      y += 4;
    };

    drawTitle('N 规则复盘');
    drawText(`交易日期：${date.value}    股票池：${stockCount.value}    持仓触发：${positionCount.value}`);

    drawTable(
      '持仓触发',
      [
        { label: '代码', width: 24, getValue: (stock) => stock.code },
        { label: '名称', width: 38, getValue: (stock) => stock.name },
        { label: '最高价', width: 24, getValue: (stock) => formatNumber(stock.highest_price) },
        { label: '最低价', width: 24, getValue: (stock) => formatNumber(stock.lowest_price) },
        { label: '档位', width: 16, getValue: (stock) => stock.buy_level || 'B1' },
        { label: '买入价格', width: 24, getValue: (stock) => formatNumber(stock.buy1_price) },
        { label: '买入手数', width: 22, getValue: (stock) => stock.buy_lots },
        { label: '买入股数', width: 24, getValue: (stock) => stock.buy_shares },
        { label: '买入金额', width: 30, getValue: (stock) => formatNumber(stock.buy_amount) },
        { label: '卖出价', width: 22, getValue: (stock) => formatOptionalNumber(stock.sell_price) },
        { label: '盈亏', width: 24, getValue: (stock) => formatOptionalNumber(stock.profit_amount) },
      ],
      positionStocks.value,
    );

    drawTable(
      '股票池明细',
      [
        { label: '代码', width: 20, getValue: (stock) => stock.code },
        { label: '名称', width: 28, getValue: (stock) => stock.name },
        { label: '当前价', width: 18, getValue: (stock) => formatNumber(stock.current_price) },
        { label: '基准价', width: 18, getValue: (stock) => formatNumber(stock.base_price) },
        { label: '最高价', width: 18, getValue: (stock) => formatNumber(stock.highest_price) },
        { label: '最低价', width: 18, getValue: (stock) => formatNumber(stock.lowest_price) },
        { label: '买 1', width: 18, getValue: (stock) => formatNumber(stock.prices.buy1) },
        { label: '止盈 1', width: 18, getValue: (stock) => formatNumber(stock.prices.profit1) },
        { label: '止损 1', width: 18, getValue: (stock) => formatNumber(stock.prices.loss1) },
        { label: '买 2', width: 18, getValue: (stock) => formatNumber(stock.prices.buy2) },
        { label: '止盈 2', width: 18, getValue: (stock) => formatNumber(stock.prices.profit2) },
        { label: '止损 2', width: 18, getValue: (stock) => formatNumber(stock.prices.loss2) },
        { label: '买 3', width: 18, getValue: (stock) => formatNumber(stock.prices.buy3) },
        { label: '止盈 3', width: 18, getValue: (stock) => formatNumber(stock.prices.profit3) },
        { label: '止损 3', width: 18, getValue: (stock) => formatNumber(stock.prices.loss3) },
      ],
      stocks.value,
    );

    doc.save(`N规则复盘_${date.value}.pdf`);
  } catch (err) {
    error.value = `导出失败：${err.message}`;
  } finally {
    exportingPdf.value = false;
  }
}

function formatNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(2) : '';
}

function formatOptionalNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) && number !== 0 ? number.toFixed(2) : '-';
}

function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) && number !== 0 ? `${number.toFixed(2)}%` : '-';
}

function statusText(status) {
  return status === 'closed' ? '已卖出' : '持仓中';
}

function exitReasonText(reason) {
  if (reason === 'take_profit') return '止盈';
  if (reason === 'stop_loss') return '止损';
  return '-';
}

function toPdfText(value) {
  return String(value ?? '');
}

async function registerPdfFont(doc) {
  const fontBase64 = await loadSimHeiFontBase64();
  doc.addFileToVFS('simhei.ttf', fontBase64);
  doc.addFont('simhei.ttf', pdfFontName, 'normal');
  doc.addFont('simhei.ttf', pdfFontName, 'bold');
  doc.setFont(pdfFontName, 'normal');
}

function loadSimHeiFontBase64() {
  if (!simHeiFontBase64Promise) {
    simHeiFontBase64Promise = fetch(simHeiFontUrl)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`字体加载失败：HTTP ${response.status}`);
        }
        return response.arrayBuffer();
      })
      .then(arrayBufferToBase64);
  }
  return simHeiFontBase64Promise;
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = '';

  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }

  return btoa(binary);
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
        <button class="secondary-btn" :disabled="!canExport" @click="exportToPdf">
          {{ exportingPdf ? '导出中...' : '导出 PDF' }}
        </button>
        <label class="theme-toggle">
          <span>深色</span>
          <input v-model="theme" type="checkbox" true-value="dark" false-value="light" />
        </label>
      </div>
    </header>

    <section class="controls">
      <label>
        <span>交易日期</span>
        <input v-model="date" type="date" @change="() => { queryStockN(); queryPositions(); }" />
      </label>
      <button :disabled="loading" @click="queryStockN">查询</button>
      <button class="run-btn" :disabled="runningFilter" @click="runFilter">
        {{ runningFilter ? '筛选中...' : '运行筛选' }}
      </button>
      <button class="position-btn" :disabled="updatingPositions" @click="updatePositions">
        {{ updatingPositions ? '更新中...' : '更新持仓' }}
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
      <div>
        <strong>{{ loading ? '-' : positionCount }}</strong>
        <span>持仓触发</span>
      </div>
    </section>

    <p v-if="error" class="error-message">{{ error }}</p>
    <p v-if="positionSummary" class="success-message">{{ positionSummary }}</p>

    <section v-if="filterLogs.length || filterResult" class="filter-log">
      <p v-if="filterSummary" class="filter-summary">{{ filterSummary }}</p>
      <div v-if="filterResult" class="filter-result">
        <strong>筛选完成</strong>
        <span>
          涨停股票 {{ filterResult.zt_total }} 只，通过 {{ filterResult.passed_count }} 只，淘汰
          {{ filterResult.rejected_count }} 只，入库 {{ filterResult.stock_n_inserted }} 条，持仓
          {{ filterResult.stock_positions_inserted || 0 }} 条。
        </span>
      </div>
      <ul>
        <li v-for="(log, index) in filterLogs" :key="index" :class="{ passed: log.passed }">
          {{ log.passed ? '通过' : '淘汰' }} {{ log.text }}
        </li>
      </ul>
    </section>

    <section class="table-panel position-panel">
      <div class="section-heading">
        <h2>持仓触发</h2>
        <span>手动更新后，按前一交易日股票池和所选日期高低价生成。</span>
      </div>
      <div v-if="loading || updatingPositions" class="state">加载中...</div>
      <div v-else-if="!positionStocks.length" class="state">当前日期没有触发买入的股票。</div>
      <div v-else class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>最高价</th>
              <th>最低价</th>
              <th>档位</th>
              <th>买入价格</th>
              <th>买入手数</th>
              <th>买入股数</th>
              <th>买入金额</th>
              <th>卖出日期</th>
              <th>卖出价格</th>
              <th>卖出金额</th>
              <th>盈亏金额</th>
              <th>盈亏比例</th>
              <th>卖出原因</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="stock in positionStocks"
              :key="`position-${stock.code}-${stock.name}`"
              :class="{ closed: stock.status === 'closed' }"
            >
              <td class="code">{{ stock.code }}</td>
              <td class="name">{{ stock.name }}</td>
              <td>{{ stock.highest_price.toFixed(2) }}</td>
              <td class="loss">{{ stock.lowest_price.toFixed(2) }}</td>
              <td>{{ stock.buy_level || 'B1' }}</td>
              <td class="buy">{{ stock.buy1_price.toFixed(2) }}</td>
              <td>{{ stock.buy_lots }}</td>
              <td>{{ stock.buy_shares }}</td>
              <td class="amount">{{ stock.buy_amount.toFixed(2) }}</td>
              <td>{{ stock.sell_date || '-' }}</td>
              <td class="sell">{{ formatOptionalNumber(stock.sell_price) }}</td>
              <td class="amount">{{ formatOptionalNumber(stock.sell_amount) }}</td>
              <td :class="stock.profit_amount >= 0 ? 'profit' : 'loss'">
                {{ formatOptionalNumber(stock.profit_amount) }}
              </td>
              <td :class="stock.profit_amount >= 0 ? 'profit' : 'loss'">
                {{ formatPercent(stock.profit_rate) }}
              </td>
              <td>{{ exitReasonText(stock.exit_reason) }}</td>
              <td>{{ statusText(stock.status) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="table-panel">
      <div class="section-heading">
        <h2>股票池明细</h2>
        <span>展示今日高低价和三档价格。</span>
      </div>
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
              <th>最高价</th>
              <th>最低价</th>
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
              <td>{{ stock.highest_price.toFixed(2) }}</td>
              <td>{{ stock.lowest_price.toFixed(2) }}</td>
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

  </main>
</template>
