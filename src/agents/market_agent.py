"""港股市场研判 Agent — 恒生指数 + 恒生科技"""
import numpy as np
import pandas as pd
from ..agents.base import AgentContext, BaseAgent
from ..data.fetcher import fetch_index_daily
from ..data.indicators import compute_indicators, compute_trend_intensity


class MarketJudgementAgent(BaseAgent):
    name = "market_judgement"
    description = "港股市场研判（恒生指数 + 恒生科技）"

    def execute(self, context: AgentContext) -> AgentContext:
        indices = {"恒生指数": "^HSI", "恒生科技": "^HSTECH", "恒生国企": "^HSCE"}
        index_data = {}
        for name, code in indices.items():
            df = fetch_index_daily(code)
            if df is not None and len(df) > 30:
                df = compute_indicators(df)
                index_data[name] = df

        if not index_data:
            context.warnings.append("无法获取港股指数数据")
            return context

        hsi = index_data.get("恒生指数", next(iter(index_data.values())))
        last = hsi.iloc[-1]
        ma20 = hsi.get("ma20", pd.Series([np.nan] * len(hsi))).iloc[-1]
        ma60 = hsi.get("ma60", pd.Series([np.nan] * len(hsi))).iloc[-1] if "ma60" in hsi.columns else None

        # 趋势方向
        trend = "sideways"
        if last["close"] > ma20 and last["close"] > (ma60 or ma20):
            trend = "up"
        elif last["close"] < ma20 and last["close"] < (ma60 or ma20):
            trend = "down"

        # 市场阶段
        ret_60d = hsi["close"].iloc[-1] / hsi["close"].iloc[-min(60, len(hsi))] - 1 if len(hsi) >= 60 else 0
        if ret_60d > 0.1:
            phase = "牛市"
        elif ret_60d < -0.05:
            phase = "熊市"
        else:
            phase = "震荡"

        # 技术指标
        rsi = last.get("rsi_14", 50)
        price_vs_ma200 = (last["close"] / hsi["close"].iloc[-200] - 1) * 100 if len(hsi) >= 200 else 0
        volatility = float(hsi["close"].pct_change().std() * np.sqrt(252))

        # 市场宽度（基于已有股票数据）
        total_stocks = len(context.stock_pool)
        above_ma50 = 0
        for code in context.stock_pool:
            df = context.market_data.get(code)
            if df is not None and len(df) > 50:
                if df["close"].iloc[-1] > df["close"].rolling(50).mean().iloc[-1]:
                    above_ma50 += 1
        breadth = round(above_ma50 / max(total_stocks, 1) * 100, 1)

        context.market_judgement = {
            "market_phase": phase,
            "trend_direction": trend,
            "policy_outlook": "中性",
            "confidence": "medium",
            "next_trend": f"港股处于{phase}，{trend}趋势，波动率{volatility:.1%}",
            "summary": (f"恒生指数{last['close']:.0f}点，RSI={rsi:.1f}，"
                       f"价格vsMA200={price_vs_ma200:.1f}%。"
                       f"市场宽度{breadth}%股票站上MA50。"
                       f"综合判断市场处于{phase}，{trend}趋势。"),
            "details": {
                "stock_breadth": {"pct_above_ma50": breadth, "total_stocks": total_stocks},
                "sector_breadth": {"breadth": "moderate", "total_sectors": len(context.hot_sectors)},
                "index_trend": {
                    "price_vs_ma200_pct": round(price_vs_ma200, 2),
                    "ma_alignment": "bullish" if trend == "up" else ("bearish" if trend == "down" else "mixed"),
                    "rsi_14": round(rsi, 1),
                    "volatility": round(volatility, 4),
                },
            },
        }
        context.warnings.append(f"港股市场研判: {phase}/{trend}")
        return context
