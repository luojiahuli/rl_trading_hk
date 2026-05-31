#!/usr/bin/env python3
"""热门板块挖掘 Agent — 港股版（ECC 架构：COLLECT → ENRICH → STORE）"""
from ..agents.base import AgentContext, BaseAgent
from ..data.sector_map import _SECTOR_STOCK_MAP_HK
from scrapling_utils import (
    fetch_all_parallel,
    classify_sectors,
    get_resolved_config,
    ContentHashCache,
)

_CACHE = ContentHashCache(ttl_minutes=30)


class HotSectorMiningAgent(BaseAgent):
    name = "hot_sector_mining"
    description = "从香港和内地财经媒体挖掘港股热门板块"

    def execute(self, context: AgentContext) -> AgentContext:
        cfg = get_resolved_config()

        # ── Phase 1: COLLECT — 并行抓取 ──────────────────
        news_items = fetch_all_parallel(
            market="hk",
            max_workers=cfg.get("global", {}).get("max_workers", 5),
            max_per_source=cfg.get("markets", {}).get("hk", {}).get("max_news_per_source", 10),
        )
        context.news_data = [n.to_dict() for n in news_items]
        context.warnings.append(f"港股并行抓取: {len(news_items)} 条新闻")

        # ── Phase 2: ENRICH — 板块分类 ────────────────────
        if news_items:
            texts = [n.title + " " + (n.content or "") for n in news_items]
            use_llm = cfg.get("ai", {}).get("enabled", False)
            api_key = cfg.get("ai", {}).get("api_key", "")
            sectors = classify_sectors(texts, market="hk", api_key=api_key, use_llm=use_llm)
        else:
            sectors = None

        if sectors:
            hot_sectors = self._enrich_with_stocks(sectors)
            context.warnings.append(f"发现 {len(hot_sectors)} 个港股热门板块")
        else:
            hot_sectors = self._preset_sectors()
            context.warnings.append("无新闻数据，使用预设板块")

        # ── Phase 3: STORE — 输出 ─────────────────────────
        context.hot_sectors = hot_sectors
        return context

    def _enrich_with_stocks(self, classified: list[dict]) -> list[dict]:
        results = []
        for item in classified[:8]:
            stocks = _SECTOR_STOCK_MAP_HK.get(item["sector"], [])
            results.append({
                "sector": item["sector"],
                "heat_score": item["heat_score"],
                "summary": f"热度{item['heat_score']}({item.get('source', 'keyword')})",
                "stocks": stocks[:5],
            })
        return results

    def _preset_sectors(self) -> list[dict]:
        results = []
        for i, (sector, stocks) in enumerate(_SECTOR_STOCK_MAP_HK.items()):
            heat = max(0, 80 - i * 5)
            results.append({
                "sector": sector,
                "heat_score": heat,
                "summary": "预设关注板块",
                "stocks": stocks[:5],
            })
        return results[:8]
