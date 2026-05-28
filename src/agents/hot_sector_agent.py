"""热门板块挖掘 Agent — 港股版（Yahoo Finance HK + AASTOCKS + 新浪港股）"""
import os
import re
import requests
from ..agents.base import AgentContext, BaseAgent
from ..data.sector_map import extract_hot_sectors_from_news
from ..data.fetcher import fetch_hk_news

_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("ALL_PROXY")
_SESSION = requests.Session()
if _PROXY:
    _SESSION.proxies.update({"http": _PROXY, "https": _PROXY})
_SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})


def _fetch_yahoo_finance_hk() -> list:
    """从 Yahoo Finance 获取港股新闻"""
    try:
        r = _SESSION.get(
            "https://finance.yahoo.com/news/",
            params={"format": "feed", "lang": "zh-Hans-HK"},
            timeout=10,
        )
        r.raise_for_status()
        items = []
        # 尝试从 RSS/HTML 中提取新闻标题
        text = r.text
        titles = re.findall(r'<h3[^>]*>(.*?)</h3>', text, re.DOTALL)[:10]
        for t in titles:
            clean = re.sub(r'<.*?>', '', t).strip()
            if clean:
                items.append({"source": "yahoo_finance_hk", "title": clean, "content": clean})
        return items
    except Exception:
        return []


def _fetch_aastocks_news() -> list:
    """从 AASTOCKS 获取港股新闻"""
    try:
        r = _SESSION.get(
            "https://www.aastocks.com/en/stocks/market/news.aspx",
            params={"type": "1", "source": "all"},
            timeout=10,
            headers={"Referer": "https://www.aastocks.com/"},
        )
        r.raise_for_status()
        items = []
        titles = re.findall(r'<a[^>]*class="news"[^>]*>(.*?)</a>', r.text, re.DOTALL)[:10]
        for t in titles:
            clean = re.sub(r'<.*?>', '', t).strip()
            if clean:
                items.append({"source": "aastocks", "title": clean, "content": clean})
        return items
    except Exception:
        return []


def _fetch_sina_hk_news() -> list:
    """从新浪财经港股频道获取新闻"""
    try:
        r = _SESSION.get(
            "https://feed.mix.sina.com.cn/api/roll/get",
            params={"pageid": 153, "lid": 2515, "k": "", "num": 10, "page": 1},
            timeout=10,
        )
        data = r.json()
        items = []
        for item in data.get("result", {}).get("data", []):
            items.append({
                "source": "sina_hk",
                "title": item.get("title", ""),
                "content": item.get("intro", "") or item.get("title", ""),
            })
        return items
    except Exception:
        return []


def _fetch_cls_news() -> list:
    """从财联社获取热点新闻"""
    try:
        r = _SESSION.get(
            "https://www.cls.cn/api/telegraph",
            params={"category": "1", "limit": 10},
            timeout=10,
            headers={"Referer": "https://www.cls.cn/"},
        )
        data = r.json()
        items = []
        for item in data.get("data", {}).get("roll_data", []):
            items.append({
                "source": "cls",
                "title": item.get("title", ""),
                "content": item.get("content", "")[:200],
            })
        return items
    except Exception:
        return []


class HotSectorMiningAgent(BaseAgent):
    name = "hot_sector_mining"
    description = "从香港和内地财经媒体挖掘港股热门板块"

    def execute(self, context: AgentContext) -> AgentContext:
        news_items = []

        # 1. Yahoo Finance HK
        news_items = _fetch_yahoo_finance_hk()
        if news_items:
            self._process_news(context, news_items, "yahoo_finance_hk")
            return context

        # 2. AASTOCKS
        news_items = _fetch_aastocks_news()
        if news_items:
            self._process_news(context, news_items, "aastocks")
            return context

        # 3. Yahoo Finance API (via yfinance)
        news_items = fetch_hk_news()
        if news_items:
            self._process_news(context, news_items, "yahoo_finance_api")
            return context

        # 4. Sina HK
        news_items = _fetch_sina_hk_news()
        if news_items:
            self._process_news(context, news_items, "sina_hk")
            return context

        # 5. 财联社（后备）
        news_items = _fetch_cls_news()
        if news_items:
            self._process_news(context, news_items, "cls")
            return context

        # 6. fallback: 使用预设板块
        from ..data.sector_map import _SECTOR_STOCK_MAP_HK
        fallback_sectors = []
        for i, (sector, stocks) in enumerate(_SECTOR_STOCK_MAP_HK.items()):
            heat = max(0, 80 - i * 5)
            fallback_sectors.append({
                "sector": sector,
                "heat_score": heat,
                "summary": "预设关注板块",
                "stocks": stocks[:5],
            })
        context.hot_sectors = fallback_sectors[:8]
        context.news_data = []
        context.warnings.append(f"所有新闻源不可用，使用 {len(fallback_sectors)} 个预设板块")
        return context

    def _process_news(self, context: AgentContext, news_items: list, source: str):
        context.news_data = news_items
        # 从新闻中提取板块
        hot_sectors_raw = extract_hot_sectors_from_news(news_items)
        hot_sectors = []
        if hot_sectors_raw:
            for sector, score in hot_sectors_raw[:8]:
                from ..data.sector_map import _SECTOR_STOCK_MAP_HK
                stocks = _SECTOR_STOCK_MAP_HK.get(sector, [])
                hot_sectors.append({
                    "sector": sector,
                    "heat_score": score * 10,
                    "summary": f"新闻热点({source})",
                    "stocks": stocks[:5],
                })
        else:
            # 无匹配板块时使用预设
            from ..data.sector_map import _SECTOR_STOCK_MAP_HK
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
