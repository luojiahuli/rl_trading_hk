#!/usr/bin/env python3
"""热门板块挖掘 Agent — 港股版（基于 scrapling_utils）"""
from ..agents.base import AgentContext, BaseAgent
from ..data.sector_map import extract_hot_sectors_from_news, _SECTOR_STOCK_MAP_HK
from ..data.fetcher import fetch_hk_news
from scrapling_utils import SmartFetcher
from scrapling_utils.news_sources import (
    YahooFinanceNews, AASTOCKSNews, SinaFinanceNews, CailiansheNews
)

_fetcher = SmartFetcher()
_yahoo = YahooFinanceNews()
_yahoo.fetcher = _fetcher
_aastocks = AASTOCKSNews()
_aastocks.fetcher = _fetcher
_sina = SinaFinanceNews()
_sina.fetcher = _fetcher
_cls = CailiansheNews()
_cls.fetcher = _fetcher


class HotSectorMiningAgent(BaseAgent):
    name = "hot_sector_mining"
    description = "从香港和内地财经媒体挖掘港股热门板块"

    def execute(self, context: AgentContext) -> AgentContext:
        news_items = []
        source_name = ""

        # 1. Yahoo Finance
        items = _yahoo.fetch()
        if items:
            news_items = [n.to_dict() for n in items]
            source_name = "yahoo_finance"

        # 2. AASTOCKS
        if not news_items:
            items = _aastocks.fetch()
            if items:
                news_items = [n.to_dict() for n in items]
                source_name = "aastocks"

        # 3. yfinance API
        if not news_items:
            news_items = fetch_hk_news()
            source_name = "yahoo_finance_api"

        # 4. 新浪港股
        if not news_items:
            items = _sina.fetch(lid="2515")
            if items:
                news_items = [n.to_dict() for n in items]
                source_name = "sina_hk"

        # 5. 财联社
        if not news_items:
            items = _cls.fetch()
            if items:
                news_items = [n.to_dict() for n in items]
                source_name = "cls"

        if news_items:
            self._process_news(context, news_items, source_name)
            return context

        # 6. Fallback: 预设板块
        fallback = []
        for i, (sector, stocks) in enumerate(_SECTOR_STOCK_MAP_HK.items()):
            heat = max(0, 80 - i * 5)
            fallback.append({
                "sector": sector,
                "heat_score": heat,
                "summary": "预设关注板块",
                "stocks": stocks[:5],
            })
        context.hot_sectors = fallback[:8]
        context.news_data = []
        context.warnings.append(f"所有新闻源不可用，使用 {len(fallback)} 个预设板块")
        return context

    def _process_news(self, context: AgentContext, news_items: list, source: str):
        context.news_data = news_items
        hot_sectors_raw = extract_hot_sectors_from_news(news_items)
        hot_sectors = []
        if hot_sectors_raw:
            for sector, score in hot_sectors_raw[:8]:
                stocks = _SECTOR_STOCK_MAP_HK.get(sector, [])
                hot_sectors.append({
                    "sector": sector,
                    "heat_score": score * 10,
                    "summary": f"新闻热点({source})",
                    "stocks": stocks[:5],
                })
        else:
            for i, (sector, stocks) in enumerate(_SECTOR_STOCK_MAP_HK.items()):
                if i >= 6:
                    break
                hot_sectors.append({
                    "sector": sector,
                    "heat_score": max(0, 70 - i * 5),
                    "summary": f"关注板块({source})",
                    "stocks": stocks[:5],
                })
        context.hot_sectors = hot_sectors
        context.warnings.append(f"发现 {len(hot_sectors)} 个港股热门板块({source})")
