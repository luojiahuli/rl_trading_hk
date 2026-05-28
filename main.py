#!/usr/bin/env python3
"""港股量化交易系统 - 主入口"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents import AgentContext, OrchestratorAgent, build_daily_pipeline
from src.storage import DatabaseManager, MessageBus
from config import REPORT_DIR, LOG_DIR, OUTPUT_DIR, DB_PATH


def run_daily_analysis(date_str: str = None) -> AgentContext:
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    print(f"🚀 启动港股 {date_str} 量化交易分析...")
    bus = MessageBus()
    db = DatabaseManager(DB_PATH).connect()
    context = AgentContext(date=date_str)
    pipeline = build_daily_pipeline()
    orchestrator = OrchestratorAgent(pipeline, message_bus=bus, database=db)
    context = orchestrator.execute(context)
    db.close()

    print(f"\n{'='*50}")
    print(f"📊 港股分析完成: {date_str}")
    print(f"  热门板块: {len(context.hot_sectors)} 个")
    print(f"  股票池: {len(context.stock_pool)} 只")
    print(f"  时间信号: {len(context.ts_signals)} 个")
    print(f"  交易信号: {len(context.rl_signals)} 个")
    print(f"  回测次数: {len(context.backtest_results)} 次")
    print(f"  市场状态: {context.regime}")
    print(f"  可视化: {context.viz_path}")
    if context.errors:
        print(f"  ❌ 错误: {len(context.errors)} 个")
        for e in context.errors:
            print(f"    - {e}")

    return context


def run_in_terminal(date_str: str = None):
    context = run_daily_analysis(date_str)
    print(f"\n{'='*50}")
    print(context.report_text)
    print(f"\n{'='*50}")
    print("💡 提示: 运行 `python main.py --qa` 启动问答模式")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="港股量化交易系统")
    parser.add_argument("--date", "-d", help="分析日期 YYYY-MM-DD")
    parser.add_argument("--qa", action="store_true", help="启动问答模式")
    args = parser.parse_args()
    run_in_terminal(args.date)
