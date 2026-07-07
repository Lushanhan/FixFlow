"""
api_server.py — 北邮派单系统后端接口

端点:
  GET /news              新闻列表（支持筛选 + 搜索）
  GET /news/{id}         新闻详情
  GET /stats             看板统计

数据源: crawler_output.json
启动:   uvicorn api_server:app --reload
"""

import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BUPT Dispatch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = Path(__file__).parent / "crawler_output.json"


def load_news() -> list[dict]:
    """从 JSON 加载数据，逐条分配 id"""
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    for i, item in enumerate(data, 1):
        item["id"] = i
    return data


# ── /news ──────────────────────────────────────────────

@app.get("/news")
def list_news(
    category: str | None = Query(None, description="分类: 科研/教学/行政/招聘/活动/其他"),
    priority: str | None = Query(None, description="优先级: high/medium/low"),
    search:   str | None = Query(None, description="标题搜索关键词"),
):
    """新闻列表，支持按分类、优先级筛选和标题搜索"""
    items = load_news()

    if category:
        items = [it for it in items if it.get("category") == category]
    if priority:
        items = [it for it in items if it.get("priority") == priority]
    if search:
        kw = search.lower()
        items = [it for it in items if kw in it.get("title", "").lower()]

    return items


# ── /news/{id} ─────────────────────────────────────────

@app.get("/news/{news_id}")
def get_news(news_id: int):
    """单条新闻详情"""
    for item in load_news():
        if item.get("id") == news_id:
            return item
    raise HTTPException(status_code=404, detail=f"News #{news_id} not found")


# ── /stats ─────────────────────────────────────────────

@app.get("/stats")
def get_stats():
    """看板统计数据"""
    items = load_news()

    # 分类计数
    category_counts: dict[str, int] = {}
    for it in items:
        cat = it.get("category", "其他")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # 优先级计数
    priority_counts: dict[str, int] = {}
    for it in items:
        pri = it.get("priority", "medium")
        priority_counts[pri] = priority_counts.get(pri, 0) + 1

    return {
        "total": len(items),
        "by_category": category_counts,
        "by_priority": priority_counts,
    }
