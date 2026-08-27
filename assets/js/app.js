"use strict";

const DATA_URL = "./data/latest.json";
const WEEKLY_HISTORY_URL = "./data/history/weekly.json";
const INTRADAY_HISTORY_URL = "./data/history/intraday.json";
const LOCALE = "ja-JP";
const SVG_NAMESPACE = "http://www.w3.org/2000/svg";

const metricOrder = ["skew", "vix", "nasdaq100_drawdown", "brent", "us10y"];
const fallbackLabels = {
  skew: "Cboe SKEW Index",
  vix: "Cboe Volatility Index",
  nasdaq100_drawdown: "NASDAQ 100 Drawdown",
  brent: "Brent Crude Oil",
  us10y: "US 10-Year Treasury Yield",
};

const dashboardState = {
  weeklyHistory: [], intradayHistory: [], weeklyYears: 1, intradayDays: 90, historyMetric: "skew",
};
let chartSequence = 0;

function formatValue(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: decimals, maximumFractionDigits: decimals,
  }).format(Number(value));
}

function formatDate(value) {
  if (!value) return "データ未取得";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "日時不明";
  return new Intl.DateTimeFormat(LOCALE, {
    dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Tokyo",
  }).format(date);
}

function formatShortDate(date) {
  return new Intl.DateTimeFormat(LOCALE, {
    year: "2-digit", month: "2-digit", day: "2-digit", timeZone: "Asia/Tokyo",
  }).format(date);
}

function deltaPresentation(delta, decimals = 2) {
  if (delta === null || delta === undefined || Number.isNaN(Number(delta))) {
    return { text: "前回差 —", className: "delta-neutral" };
  }
  const numericDelta = Number(delta);
  const prefix = numericDelta > 0 ? "+" : "";
  const className = numericDelta > 0 ? "delta-positive" : numericDelta < 0 ? "delta-negative" : "delta-neutral";
  return { text: `前回差 ${prefix}${formatValue(numericDelta, decimals)}`, className };
}

function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
  } catch {
    return "#";
  }
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function buildMetricCard(key, metric = {}) {
  const article = element("article", "metric-card");
  const top = element("div", "metric-top");
  top.append(
    element("p", "metric-label", metric.label || fallbackLabels[key] || key),
    element("span", "metric-unit", metric.unit || ""),
  );
  const delta = deltaPresentation(metric.delta, metric.decimals);
  const bottom = element("div", "metric-bottom");
  bottom.append(element("p", `metric-delta ${delta.className}`, delta.text));
  const source = element("a", "metric-source", "Source ↗");
  source.href = safeExternalUrl(metric.source_url);
  source.target = "_blank";
  source.rel = "noreferrer";
  bottom.append(source);
  article.append(
    top,
    element("p", "metric-value", formatValue(metric.value, metric.decimals)),
    bottom,
    element("p", "metric-time", formatDate(metric.observed_at)),
  );
  return article;
}

function renderMetrics(metrics = {}) {
  document.querySelector("#metrics-grid").replaceChildren(
    ...metricOrder.map((key) => buildMetricCard(key, metrics[key])),
  );
}

function renderSources(metrics = {}) {
  const items = metricOrder.map((key) => {
    const metric = metrics[key] || {};
    const item = document.createElement("li");
    const link = document.createElement("a");
    item.append(document.createTextNode(metric.label || fallbackLabels[key] || key));
    link.href = safeExternalUrl(metric.source_url);
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "Yahoo Finance ↗";
    item.append(link);
    return item;
  });
  document.querySelector("#source-list").replaceChildren(...items);
}

function renderWeekly(weekly = {}) {
  document.querySelector("#weekly-cci").textContent = formatValue(weekly.cci, 2);
  document.querySelector("#weekly-rsi").textContent = formatValue(weekly.rsi, 2);
  document.querySelector("#weekly-as-of").textContent = weekly.as_of ? `基準日 ${formatDate(weekly.as_of)}` : "算出前";
}

function svgElement(tag, attributes = {}) {
  const node = document.createElementNS(SVG_NAMESPACE, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
  return node;
}

function normalizePoints(points) {
  return points
    .map((point) => ({ date: new Date(point.date), value: Number(point.value) }))
    .filter((point) => !Number.isNaN(point.date.getTime()) && Number.isFinite(point.value))
    .sort((left, right) => left.date - right.date);
}

function showEmptyChart(container) {
  const empty = element("div", "chart-empty");
  empty.append(
    element("strong", "", "履歴データがありません"),
    element("p", "", "定期取得後にグラフが表示されます。"),
  );
  container.replaceChildren(empty);
}

function drawLineChart(container, rawPoints, options = {}) {
  const points = normalizePoints(rawPoints);
  if (!points.length) {
    showEmptyChart(container);
    return;
  }
  const width = 760;
  const height = options.large ? 310 : 260;
  const margin = { top: 12, right: 18, bottom: 32, left: 54 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const domainValues = points.map((point) => point.value).concat(options.guides || []);
  if (options.includeZero) domainValues.push(0);
  let minimum = options.domain?.[0] ?? Math.min(...domainValues);
  let maximum = options.domain?.[1] ?? Math.max(...domainValues);
  if (minimum === maximum) {
    const padding = Math.max(Math.abs(minimum) * 0.05, 1);
    minimum -= padding;
    maximum += padding;
  } else if (!options.domain) {
    const padding = (maximum - minimum) * 0.1;
    minimum -= padding;
    maximum += padding;
  }
  const xPosition = (index) => points.length === 1
    ? margin.left + plotWidth / 2
    : margin.left + (index / (points.length - 1)) * plotWidth;
  const yPosition = (value) => margin.top + ((maximum - value) / (maximum - minimum)) * plotHeight;
  const svg = svgElement("svg", {
    viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: "xMidYMid meet", "aria-hidden": "true",
  });

  const gradientId = `chart-area-gradient-${chartSequence += 1}`;
  const defs = svgElement("defs");
  const gradient = svgElement("linearGradient", { id: gradientId, x1: 0, y1: 0, x2: 0, y2: 1 });
  gradient.append(
    svgElement("stop", { offset: "0%", "stop-color": "#52e0b4", "stop-opacity": 0.2 }),
    svgElement("stop", { offset: "100%", "stop-color": "#52e0b4", "stop-opacity": 0 }),
  );
  defs.append(gradient);
  svg.append(defs);

  for (let index = 0; index <= 4; index += 1) {
    const value = maximum - ((maximum - minimum) * index) / 4;
    const y = yPosition(value);
    svg.append(svgElement("line", {
      x1: margin.left, y1: y, x2: width - margin.right, y2: y, class: "chart-grid-line",
    }));
    const label = svgElement("text", {
      x: margin.left - 8, y: y + 4, "text-anchor": "end", class: "chart-axis-label",
    });
    label.textContent = formatValue(value, options.axisDecimals ?? 0);
    svg.append(label);
  }

  for (const guide of options.guides || []) {
    if (guide < minimum || guide > maximum) continue;
    const y = yPosition(guide);
    svg.append(svgElement("line", {
      x1: margin.left, y1: y, x2: width - margin.right, y2: y, class: "chart-guide-line",
    }));
  }
  if (options.includeZero && minimum <= 0 && maximum >= 0) {
    const y = yPosition(0);
    svg.append(svgElement("line", {
      x1: margin.left, y1: y, x2: width - margin.right, y2: y, class: "chart-zero-line",
    }));
  }

  const coordinates = points.map((point, index) => `${xPosition(index)},${yPosition(point.value)}`);
  const areaPath = [
    `M ${xPosition(0)} ${margin.top + plotHeight}`,
    `L ${coordinates.join(" L ")}`,
    `L ${xPosition(points.length - 1)} ${margin.top + plotHeight}`,
    "Z",
  ].join(" ");
  svg.append(svgElement("path", { d: areaPath, fill: `url(#${gradientId})`, class: "chart-area" }));
  svg.append(svgElement("polyline", { points: coordinates.join(" "), class: "chart-line" }));

  const latest = points[points.length - 1];
  const latestDot = svgElement("circle", {
    cx: xPosition(points.length - 1), cy: yPosition(latest.value), r: 5, class: "chart-latest-dot",
  });
  const tooltip = svgElement("title");
  tooltip.textContent = `${formatShortDate(latest.date)}: ${formatValue(latest.value, options.axisDecimals ?? 2)}`;
  latestDot.append(tooltip);
  svg.append(latestDot);

  const labelIndexes = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
  for (const index of labelIndexes) {
    const label = svgElement("text", {
      x: xPosition(index), y: height - 8,
      "text-anchor": index === 0 ? "start" : index === points.length - 1 ? "end" : "middle",
      class: "chart-axis-label",
    });
    label.textContent = formatShortDate(points[index].date);
    svg.append(label);
  }
  container.replaceChildren(svg);
  container.setAttribute(
    "aria-label",
    `${options.label || "指標"}、${formatShortDate(points[0].date)}から${formatShortDate(latest.date)}、最新値${formatValue(latest.value, options.axisDecimals ?? 2)}`,
  );
}

function filterByYears(points, years) {
  if (!points.length) return [];
  const latest = new Date(points[points.length - 1].date);
  const cutoff = new Date(latest);
  cutoff.setUTCFullYear(cutoff.getUTCFullYear() - years);
  return points.filter((point) => new Date(point.date) >= cutoff);
}

function filterByDays(points, days) {
  if (!points.length) return [];
  const latest = new Date(points[points.length - 1].date);
  const cutoff = new Date(latest.getTime() - days * 86400000);
  return points.filter((point) => new Date(point.date) >= cutoff);
}

function renderWeeklyCharts() {
  const filtered = filterByYears(dashboardState.weeklyHistory, dashboardState.weeklyYears);
  document.querySelector("#weekly-chart-summary").textContent = filtered.length
    ? `${filtered.length}週分 · ${formatShortDate(new Date(filtered[0].date))}〜${formatShortDate(new Date(filtered.at(-1).date))}`
    : "週足履歴は初回取得後に表示されます";
  drawLineChart(
    document.querySelector("#cci-chart"),
    filtered.map((point) => ({ date: point.date, value: point.cci })),
    { label: "週足CCI", guides: [-100, 100], includeZero: true, axisDecimals: 0 },
  );
  drawLineChart(
    document.querySelector("#rsi-chart"),
    filtered.map((point) => ({ date: point.date, value: point.rsi })),
    { label: "週足RSI", guides: [30, 70], domain: [0, 100], axisDecimals: 0 },
  );
}

function metricHistoryPoints(key) {
  return dashboardState.intradayHistory.flatMap((observation) => {
    const metric = observation.metrics?.[key];
    if (!metric || metric.value === null || metric.value === undefined) return [];
    return [{ date: metric.observed_at || observation.captured_at, value: metric.value }];
  });
}

function renderIntradayChart() {
  const key = dashboardState.historyMetric;
  const points = filterByDays(metricHistoryPoints(key), dashboardState.intradayDays);
  const title = fallbackLabels[key] || key;
  document.querySelector("#history-chart-title").textContent = title;
  document.querySelector("#history-chart-summary").textContent = points.length
    ? `${points.length}回分 · 最新 ${formatValue(points.at(-1).value, key === "us10y" ? 3 : 2)}`
    : "履歴は次回の定期取得から蓄積されます";
  drawLineChart(document.querySelector("#history-chart"), points, {
    label: title, includeZero: key === "nasdaq100_drawdown",
    axisDecimals: key === "us10y" ? 3 : 2, large: true,
  });
}

function bindChartControls() {
  document.querySelector("[data-chart-controls='weekly']").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-years]");
    if (!button) return;
    dashboardState.weeklyYears = Number(button.dataset.years);
    button.parentElement.querySelectorAll("button").forEach((item) => {
      item.setAttribute("aria-pressed", String(item === button));
    });
    renderWeeklyCharts();
  });
  document.querySelector("[data-chart-controls='intraday']").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-days]");
    if (!button) return;
    dashboardState.intradayDays = Number(button.dataset.days);
    button.parentElement.querySelectorAll("button").forEach((item) => {
      item.setAttribute("aria-pressed", String(item === button));
    });
    renderIntradayChart();
  });
  document.querySelector("#history-metric").addEventListener("change", (event) => {
    dashboardState.historyMetric = event.target.value;
    renderIntradayChart();
  });
}

function renderStatus(payload) {
  const badge = document.querySelector("#status-badge");
  const notice = document.querySelector("#data-notice");
  const state = payload.status?.state || "setup";
  badge.className = `status-badge status-${state}`;
  badge.textContent = state === "ready" ? "更新済み" : state === "stale" ? "更新遅延" : "準備中";
  notice.textContent = payload.status?.message || "データ状態を取得できませんでした。";
  document.querySelector("#last-updated").textContent = formatDate(payload.generated_at);
}

function showLoadError(error) {
  const badge = document.querySelector("#status-badge");
  const notice = document.querySelector("#data-notice");
  badge.className = "status-badge status-error";
  badge.textContent = "読込失敗";
  notice.className = "notice notice-error";
  notice.textContent = "最新データを読み込めませんでした。しばらくしてから再読み込みしてください。";
  console.error("Failed to load dashboard data", error);
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response.json();
}

async function initialize() {
  bindChartControls();
  try {
    const [payload, weeklyHistory, intradayHistory] = await Promise.all([
      fetchJson(DATA_URL),
      fetchJson(WEEKLY_HISTORY_URL).catch(() => ({ observations: [] })),
      fetchJson(INTRADAY_HISTORY_URL).catch(() => ({ observations: [] })),
    ]);
    dashboardState.weeklyHistory = (weeklyHistory.observations || []).map((item) => ({
      date: item.as_of, cci: item.cci, rsi: item.rsi,
    }));
    dashboardState.intradayHistory = intradayHistory.observations || [];
    renderMetrics(payload.metrics);
    renderSources(payload.metrics);
    renderWeekly(payload.weekly);
    renderWeeklyCharts();
    renderIntradayChart();
    renderStatus(payload);
  } catch (error) {
    renderMetrics(); renderSources(); renderWeekly(); renderWeeklyCharts(); renderIntradayChart();
    showLoadError(error);
  }
}

document.addEventListener("DOMContentLoaded", initialize);
