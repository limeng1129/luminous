#!/usr/bin/env python3
"""命令行版存储自检。用法：python check_storage.py"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("LUMINOUS_DB", os.path.join(BASE, "luminous.db"))
UP = os.environ.get("LUMINOUS_UPLOAD_DIR", os.path.join(BASE, "static", "uploads"))

from checks import run_checks

MARK = {"ok": "✅", "warn": "⚠️ ", "fail": "❌"}

print("\n  流光 · 存储自检\n" + "  " + "─" * 52)
results = run_checks(DB, UP)
for name, status, detail, fix in results:
    print(f"\n  {MARK[status]} {name}\n     {detail}")
    if fix:
        print(f"     → {fix}")
print("\n  " + "─" * 52)
bad = [r for r in results if r[1] == "fail"]
print(f"  {'有 %d 项没通过，按上面的提示修一下。' % len(bad) if bad else '全部通过，存储配置没问题。'}\n")
sys.exit(1 if bad else 0)
