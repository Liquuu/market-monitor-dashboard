"use strict";

const DATA_URL = "./data/latest.json";
const LOCALE = "ja-JP";

const metricOrder = ["skew", "vix", "nasdaq100_drawdown", "brent", "us10y"];

const fallbackLabels = {
  skew: "Cboe SKEW Index",
  vix: "Cboe Volatility Index",
  nasdaq100_drawdown: "NASDAQ 100 Drawdown",
  brent: "Brent Crude Oil",
  us10y: "US 10-Year Treasury Yield",
};

function formatValue(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  return new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Number(value));
}

function formatDate(value) {
  if (!value) return "データ未取得";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "日時不明";

  return new Intl.DateTimeFormat(LOCALE, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Tokyo",
  }).format(date);
}

function deltaPresentation(delta, decimals = 2) {
  if (delta === null || delta === undefined || Number.isNaN(Number(delta))) {
    return { text: "前回差 —", className: "delta-neutral" };
  }

  const numericDelta = Number(delta);
  const prefix = numericDelta > 0 ? "+" : "";
  const className = numericDelta > 0
    ? "delta-positive"
    : numericDelta < 0
      ? "delta-negative"
      : "delta-neutral";

  return {
    text: `前回差 ${prefix}${formatValue(numericDelta, decimals)}`,
    className,
  };
}

function buildMetricCard(key, metric = {}) {
  const article = document.createElement("article");
  article.className = "metric-card";

  const delta = deltaPresentation(metric.delta, metric.decimals);
  const safeSourceUrl = typeof metric.source_url === "string" ? metric.source_url : "#";

  article.innerHTML = `
    <div class="metric-top">
      <p class="metric-label">${metric.label || fallbackLabels[key] || key}</p>
      <span class="metric-unit">${metric.unit || ""}</span>
    </div>
    <p class="metric-value">${formatValue(metric.value, metric.decimals)}</p>
    <div class="metric-bottom">
      <p class="metric-delta ${delta.className}">${delta.text}</p>
      <a class="metric-source" href="${safeSourceUrl}" target="_blank" rel="noreferrer">Source ↗</a>
    </div>
    <p class="metric-time">${formatDate(metric.observed_at)}</p>
  `;

  return article;
}

function renderMetrics(metrics = {}) {
  const grid = document.querySelector("#metrics-grid");
  grid.replaceChildren(...metricOrder.map((key) => buildMetricCard(key, metrics[key])));
}

function renderSources(metrics = {}) {
  const list = document.querySelector("#source-list");
  const items = metricOrder.map((key) => {
    const metric = metrics[key] || {};
    const item = document.createElement("li");
    const link = document.createElement("a");

    item.append(document.createTextNode(metric.label || fallbackLabels[key] || key));
    link.href = typeof metric.source_url === "string" ? metric.source_url : "#";
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "Yahoo Finance ↗";
    item.append(link);

    return item;
  });

  list.replaceChildren(...items);
}

function renderWeekly(weekly = {}) {
  document.querySelector("#weekly-cci").textContent = formatValue(weekly.cci, 2);
  document.querySelector("#weekly-rsi").textContent = formatValue(weekly.rsi, 2);
  document.querySelector("#weekly-as-of").textContent = weekly.as_of
    ? `基準日 ${formatDate(weekly.as_of)}`
    : "算出前";
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

async function initialize() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const payload = await response.json();
    renderMetrics(payload.metrics);
    renderSources(payload.metrics);
    renderWeekly(payload.weekly);
    renderStatus(payload);
  } catch (error) {
    renderMetrics();
    renderSources();
    renderWeekly();
    showLoadError(error);
  }
}

document.addEventListener("DOMContentLoaded", initialize);
