# 港股量化交易系统 (HK)

基于 **多智能体架构** 的港股每日动态机会点挖掘系统。

---

## 今日分析 (2026-05-29)

### 📊 策略绩效

| 策略 | 收益率 | Sharpe | 最大回撤 |
|------|--------|--------|---------|
| breakout | -0.74% | 0.140 | -37.92% |
| mean_reversion | +20.74% | 0.322 | -27.92% |
| momentum | **+31.60%** | **0.446** 🏆 | -33.16% |
| trend_following | +13.29% | 0.205 | -33.96% |

### 📊 市场研判

| 维度 | 判断 |
|------|------|
| 市场阶段 | 熊市 |
| 趋势方向 | down |
| RSI | 16.4 |
| 波动率(年化) | 24.0% |

**恒生指数**: 25006 点 | **市场宽度**: 40.0% 股票站上MA50

### ⚠️ 风险控制

| 指标 | 值 |
|------|-----|
| 当前回撤 | 0.00% |
| 状态 | normal |

### 📈 可视化

![港股可视化](output/reports/hk_report_2026-05-29.png)

---

## 系统架构

```
新闻 ──→ 板块 ──→ 日线数据 ──→ 技术指标 ──→ 时间序列信号 ──→ RL决策 ──→ 报告/可视化/飞书
```

10 Agent 管线: HotSector → DataFetch → TSSignal → RL → MultiStrategy → Risk → Report → Viz → Feishu → Storage

## 快速开始

```bash
git clone https://github.com/luojiahuli/rl_trading_hk.git
cd rl_trading_hk
pip install -r requirements.txt
python main.py
```

### 每日推送

```bash
bash daily_push.sh
```

## 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FEISHU_APP_ID` | 飞书应用 ID | `cli_aa8a3a870d789cb1` |
| `FEISHU_APP_SECRET` | 飞书应用 Secret | - |
| `FEISHU_CHAT_ID` | 飞书群 ID | `oc_ed483f60e1bc9408534038ee155eaf5d` |
| `MIN_STOCK_PRICE` | 最低股价过滤 | HK$1.0 |
| `INITIAL_CASH` | 初始资金 | HK$1,000,000 |
