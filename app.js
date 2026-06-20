let latest = null;
let selected = null;

const $ = (id) => document.getElementById(id);

function money(value) {
  const n = Number(value || 0);
  if (Math.abs(n) >= 1e7) return `₹${(n / 1e7).toFixed(2)} cr`;
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function pct(value) {
  return `${Number(value || 0).toFixed(2)}%`;
}

async function loadLatest() {
  const profile = $("profile").value;
  const res = await fetch(`/api/latest?profile=${profile}`);
  latest = await res.json();
  renderLatest();
}

function renderLatest() {
  const top = latest?.top10 || [];
  $("scanTime").textContent = latest?.scan ? `Last scan ${new Date(latest.scan.created_at).toLocaleString()}` : "No scan loaded";
  $("topRows").innerHTML = top.map((item) => `
    <tr>
      <td><strong>${item.symbol}</strong><br><span class="muted">${item.name}</span></td>
      <td>${item.score}</td>
      <td class="${item.action.includes("BUY") ? "buy" : item.action.includes("SELL") ? "sell" : ""}">${item.action}</td>
      <td><span class="badge">${item.risk_category}</span></td>
      <td>${item.entry}</td>
      <td>${item.stoploss}</td>
      <td>${item.target}</td>
      <td>${pct(item.risk_pct)}</td>
      <td>${pct(item.reward_pct)}</td>
      <td><button onclick="selectStock('${item.symbol}')">Open</button></td>
    </tr>
  `).join("");

  $("candidateCards").innerHTML = (latest?.candidates || []).map((item) => `
    <div class="card" onclick="selectStock('${item.symbol}')">
      <strong>#${(latest.candidates.indexOf(item) + 1)} ${item.symbol}</strong>
      <div class="muted">${item.name}</div>
      <div>Score ${item.score} · ${item.action}</div>
      <div>Risk ${pct(item.risk_pct)} · Profit ${pct(item.reward_pct)}</div>
    </div>
  `).join("");

  if (!selected && top.length) selectStock(top[0].symbol);
}

async function runScan() {
  $("scanBtn").disabled = true;
  $("scanBtn").textContent = "Scanning...";
  const data = new FormData();
  data.append("profile", $("profile").value);
  const res = await fetch("/api/scan", { method: "POST", body: data });
  const payload = await res.json();
  latest = payload.latest;
  selected = null;
  renderLatest();
  $("scanBtn").disabled = false;
  $("scanBtn").textContent = "Run scan now";
}

async function selectStock(symbol) {
  const all = latest?.candidates || [];
  selected = all.find((item) => item.symbol === symbol);
  if (!selected) return;
  $("chartTitle").textContent = `${selected.symbol} · ${selected.name}`;
  $("detailBox").innerHTML = `
    <div><strong>Current situation</strong><br>${selected.current_situation}</div>
    <div><strong>Company aim/business</strong><br>${selected.company_aim}</div>
    <div><strong>Fundamentals</strong><br>PE ${selected.pe_ratio || "NA"} · Market cap ${money(selected.market_cap)} · Avg turnover ${money(selected.turnover)}</div>
    <div><strong>Risk</strong><br>${selected.risks}</div>
    <div><strong>Profit case</strong><br>${selected.profit_case}</div>
    <div><strong>Stats</strong><br>Std dev ${selected.std_dev}% · Alpha ${selected.alpha}% · Beta ${selected.beta} · Volatility ${selected.volatility}%</div>
    <div><strong>Patterns</strong><br>${selected.patterns?.map((p) => `${p.name} (${p.date})`).join(", ") || "None detected"}</div>
    <div><a target="_blank" href="https://www.screener.in/company/${selected.symbol}/">Screener</a> · <a target="_blank" href="https://www.nseindia.com/get-quotes/equity?symbol=${selected.symbol}">NSE</a> · <a target="_blank" href="https://www.moneycontrol.com/stocks/company_info/stock_search.php?search_str=${selected.symbol}">Moneycontrol</a></div>
  `;
  $("chartBox").innerHTML = `<iframe title="${selected.symbol} chart" src="/api/chart/${selected.symbol}?entry=${selected.entry}&stoploss=${selected.stoploss}&target=${selected.target}"></iframe>`;
}

async function loadZerodha() {
  $("zerodhaBox").innerHTML = "Loading...";
  const res = await fetch("/api/zerodha");
  const data = await res.json();
  $("loginLink").href = data.login_url || "#";
  const equity = data.margins?.data?.equity;
  const holdings = data.holdings?.holdings || [];
  $("zerodhaBox").innerHTML = `
    <div><strong>Mode:</strong> ${data.live_trading ? "Live orders enabled" : "Paper order logging"}</div>
    <div><strong>Available balance:</strong> ${equity ? money(equity.available?.cash || 0) : "Login/config needed"}</div>
    <div><strong>Holdings:</strong> ${holdings.length}</div>
    <div>${holdings.slice(0, 8).map((h) => `${h.tradingsymbol}: qty ${h.quantity}, P&L ${money(h.pnl || 0)}`).join("<br>") || "No holdings loaded"}</div>
    <div><strong>Recent orders</strong><br>${(data.orders || []).slice(0, 8).map((o) => `${o.side} ${o.quantity} ${o.symbol} · ${o.status} · ${o.mode}`).join("<br>") || "None"}</div>
  `;
}

async function sendOrder(side) {
  if (!selected) return alert("Select a stock first.");
  const quantity = Number($("qty").value || 0);
  if (quantity < 1) return alert("Quantity must be at least 1.");
  const ok = confirm(`${side} ${quantity} share(s) of ${selected.symbol}?`);
  if (!ok) return;
  const data = new FormData();
  data.append("symbol", selected.symbol);
  data.append("side", side);
  data.append("quantity", quantity);
  const res = await fetch("/api/order", { method: "POST", body: data });
  const payload = await res.json();
  if (!res.ok) alert(payload.detail || "Order failed");
  else alert(payload.message || `${payload.status}: ${payload.order_id || ""}`);
  loadZerodha();
}

$("scanBtn").addEventListener("click", runScan);
$("zerodhaBtn").addEventListener("click", loadZerodha);
$("profile").addEventListener("change", loadLatest);
$("buyBtn").addEventListener("click", () => sendOrder("BUY"));
$("sellBtn").addEventListener("click", () => sendOrder("SELL"));

loadLatest();
loadZerodha();
