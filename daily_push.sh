#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

REPORT_LOG="output/logs/daily_hk_$(date +%Y%m%d).log"
mkdir -p output/logs

echo "=== 🚀 港股量化日报 $(date +%Y-%m-%d) ===" > "$REPORT_LOG"

python3 main.py >> "$REPORT_LOG" 2>&1

echo "=== ✅ 完成 $(date) ===" >> "$REPORT_LOG"
cat "$REPORT_LOG" | tail -5