"""
crawler_demo.py — 北邮官网信息公告采集 Demo

功能：
  1. 爬取 https://www.bupt.edu.cn/xxgg.htm 公告列表
  2. 进入详情页提取正文、来源、附件
  3. 对内容进行简单摘要
  4. 输出结构化 JSON

策略：
  - DrissionPage（ChromiumPage）控制 Edge 浏览器
  - 能正确处理 Cloudflare JS 挑战并执行页面 JS 渲染

依赖：DrissionPage, beautifulsoup4, lxml
用法：python crawler_demo.py
"""

import json
import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from DrissionPage import ChromiumPage, ChromiumOptions


# ============================================================
# 配置
# ============================================================

BASE_URL = "https://www.bupt.edu.cn"
LIST_URL = f"{BASE_URL}/xxgg.htm"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# 分页配置
PAGES_TO_CRAWL = 3   # 爬取多少页列表（1 = 仅首页）
DETAIL_LIMIT = 10     # 采集多少条详情（0 = 全部）


# ============================================================
# 浏览器工厂
# ============================================================

def create_page() -> ChromiumPage:
    """创建 DrissionPage ChromiumPage 实例"""
    co = ChromiumOptions()
    co.set_browser_path(EDGE_PATH)
    # 不设 headless —— Cloudflare 检测无头浏览器
    co.set_argument("--window-size=1920,1080")
    co.set_argument("--disable-blink-features=AutomationControlled")
    return ChromiumPage(co)


def fetch(page: ChromiumPage, url: str, wait_selector: str = "body") -> str:
    """
    获取页面渲染后的 HTML。

    参数：
        page: ChromiumPage 实例（复用同一个浏览器进程）
        url: 目标 URL
        wait_selector: 等待此 CSS 选择器出现后才返回
    """
    print(f"  [fetch] {url}")
    page.get(url)

    # 等待关键元素出现（最多 15 秒）
    deadline = time.time() + 15
    while time.time() < deadline:
        if page.ele(wait_selector, timeout=1):
            break
        time.sleep(0.5)

    html = page.html
    print(f"  [fetch] OK ({len(html)} bytes)")
    return html


# ============================================================
# 列表页解析
# ============================================================

def parse_list(html: str) -> list[dict]:
    """
    解析公告列表页。

    JS 渲染后的 DOM 结构（DrissionPage 实测）：
        ul.list > li
          ├── div.date-block
          |     |-- p.date-year  > "2026-07"
          |     |-- p.date-day   > "07"
          |-- a[href]  >  标题 + info/1083/90755.htm
    """
    soup = BeautifulSoup(html, "lxml")
    articles = []

    for li in soup.select("ul.list > li"):
        a_tag = li.select_one("a[href]")
        year_tag = li.select_one(".date-year")
        day_tag = li.select_one(".date-day")

        if not a_tag:
            continue

        title = a_tag.get_text(strip=True)
        href = a_tag.get("href", "").strip()
        if not title or not href:
            continue

        # 拼接日期：2026-07 + 07 = 2026-07-07
        date = ""
        if year_tag:
            year = year_tag.get_text(strip=True)
            day = day_tag.get_text(strip=True) if day_tag else ""
            if year:
                date = f"{year}-{day}" if day else year

        articles.append({
            "title": title,
            "date": date,
            "url": urljoin(BASE_URL, href),
        })

    return articles


# ============================================================
# 详情页解析
# ============================================================

def parse_detail(html: str, base_url: str) -> dict:
    """
    解析公告详情页 > 标题、正文、来源、附件。

    北邮 CMS (Visual SiteBuilder) 特征：
      - 正文容器: #vsb_content 或 #vsb_content_2
      - 来源: 正则 "来源：xxx"
      - 附件: 扩展名匹配 + "附件"关键词
    """
    soup = BeautifulSoup(html, "lxml")

    # 1) 标题
    title = ""
    for sel in [".content h1", ".article h1", "h1", ".title", ".con-title"]:
        node = soup.select_one(sel)
        if node:
            title = node.get_text(strip=True)
            if title:
                break
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
        if "-" in title:
            title = title.rsplit("-", 1)[0].strip()

    # 2) 正文
    content = ""
    for sel in [
        "#vsb_content", "#vsb_content_2",
        ".v_news_content", ".article-content",
        ".content", ".article",
    ]:
        node = soup.select_one(sel)
        if node:
            for tag in node.select("script, style"):
                tag.decompose()
            content = node.get_text("\n", strip=True)
            if len(content) > 50:
                break

    # 3) 来源
    source = ""
    text = soup.get_text(" ", strip=True)
    for pat in [r"来源[:：]\s*([^\s|｜]+)", r"信息来源[:：]\s*([^\s|｜]+)"]:
        m = re.search(pat, text)
        if m:
            source = m.group(1).strip()
            break

    # 4) 附件
    attachments = []
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href:
            continue
        link_text = a.get_text(strip=True)
        lower = href.lower()
        if lower.endswith((
            ".pdf", ".doc", ".docx", ".xls", ".xlsx",
            ".ppt", ".pptx", ".zip", ".rar", ".7z",
        )) or "附件" in link_text:
            attachments.append(urljoin(base_url, href))
    attachments = list(dict.fromkeys(attachments))  # 去重保序

    return {
        "title": title,
        "content": content,
        "source": source,
        "attachments": attachments,
    }


# ============================================================
# 优先级判断
# ============================================================

PRIORITY_RULES = [
    ("high", ["紧急", "截止", "立即", "重要通知", "关于", "停水", "停电", "断网"]),
    ("medium", ["报名", "申请", "会议", "征集", "申报", "公示"]),
    ("low", ["宣传", "新闻", "活动预告", "讲座", "报告会"]),
]


def get_priority(title: str) -> str:
    """
    根据标题关键词判断优先级。

    匹配规则：
      - 命中 high 关键词 → "high"
      - 命中 medium 关键词 → "medium"
      - 命中 low 关键词 → "low"
      - 无匹配 → "medium"（默认）
    """
    for level, keywords in PRIORITY_RULES:
        for kw in keywords:
            if kw in title:
                return level
    return "medium"


# ============================================================
# 分类识别
# ============================================================

# 分类规则：按顺序匹配标题和正文关键词，标题命中权重 2，正文权重 1
CATEGORY_RULES = [
    ("科研", ["科研", "项目", "论文", "基金", "实验"]),
    ("教学", ["课程", "考试", "教学", "学生"]),
    ("行政", ["通知", "会议", "办公", "管理"]),
    ("招聘", ["招聘", "岗位", "人才"]),
    ("活动", ["讲座", "比赛", "活动"]),
]


def classify(title: str, content: str = "") -> str:
    """
    根据标题和正文关键词进行自动分类。

    策略：
      - 标题关键词每个命中 +2 分
      - 正文关键词每个命中 +1 分
      - 取最高分的类别
      - 无匹配时返回 "其他"
    """
    scores: list[int] = [0] * len(CATEGORY_RULES)

    title_lower = title.lower()
    content_lower = content.lower() if content else ""

    for idx, (_, keywords) in enumerate(CATEGORY_RULES):
        for kw in keywords:
            if kw.lower() in title_lower:
                scores[idx] += 2
            if kw.lower() in content_lower:
                scores[idx] += 1

    best_idx = max(range(len(scores)), key=lambda i: scores[i])

    if scores[best_idx] == 0:
        return "其他"

    return CATEGORY_RULES[best_idx][0]


# ============================================================
# 分页
# ============================================================

def get_page_urls(page: ChromiumPage, max_pages: int) -> list[str]:
    """
    从首页获取所有分页 URL。

    北邮分页规律（JS 渲染后）：
      - 第1页: xxgg.htm
      - 第2页: xxgg/215.htm
      - 第3页: xxgg/214.htm
      - ...
      - 最后一页: xxgg/1.htm

    通过解析首页上的分页块获取总页数，然后生成 URL 列表。
    """
    from bs4 import BeautifulSoup as Soup

    soup = Soup(page.html, "lxml")
    pager = soup.select_one(".pb_sys_common")

    if not pager:
        print("  [分页] 未找到分页块，仅采集首页")
        return [LIST_URL]

    # 找最后一页的页码
    last_page_num = 1
    page_links = {}
    for a in pager.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"].strip()
        if text.isdigit():
            n = int(text)
            page_links[n] = href
            if n > last_page_num:
                last_page_num = n

    if last_page_num <= 1:
        print("  [分页] 仅1页")
        return [LIST_URL]

    # 从首页提取当前页对应的 ID（第2页的链接中提取基准）
    total_pages = last_page_num
    if 2 in page_links:
        # page_links[2] = "xxgg/215.htm" → 当前第1页 ID = 216
        m = __import__('re').search(r"/(\d+)\.htm", page_links[2])
        if m:
            current_max_id = int(m.group(1)) + 1
        else:
            current_max_id = total_pages
    else:
        current_max_id = total_pages

    pages = min(max_pages, total_pages)
    urls = [LIST_URL]  # 第1页

    # 第2页起: xxgg/{current_max_id-1}.htm, xxgg/{current_max_id-2}.htm ...
    for i in range(1, pages):
        page_id = current_max_id - i
        urls.append(urljoin(BASE_URL, f"xxgg/{page_id}.htm"))

    print(f"  [分页] 总{total_pages}页, 本次采集{len(urls)}页")
    return urls


# ============================================================
# 简单摘要
# ============================================================

def summarize(text: str, max_length: int = 150) -> str:
    """取正文前 max_length 字符，在标点处截断"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text

    snippet = text[:max_length + 50]
    for sep in ["。", "；", "\n", "，"]:
        pos = snippet.rfind(sep, 0, max_length)
        if pos > max_length // 2:
            return snippet[:pos + 1].strip()

    return text[:max_length].strip() + "..."


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("  北邮官网信息公告采集 Demo")
    print("=" * 60)

    page = create_page()

    try:
        # ---- [1/5] 首页 + 分页分析 ----
        print("\n[1/5] 获取首页并分析分页...")
        list_html = fetch(page, LIST_URL, wait_selector="ul.list")
        articles = parse_list(list_html)
        page_urls = get_page_urls(page, PAGES_TO_CRAWL)
        print(f"  -> 首页解析到 {len(articles)} 条公告")

        # ---- [2/5] 采集剩余分页 ----
        if len(page_urls) > 1:
            print(f"\n[2/5] 采集第2~{len(page_urls)}页...")
            for url in page_urls[1:]:
                try:
                    html = fetch(page, url, wait_selector="ul.list")
                    page_articles = parse_list(html)
                    articles.extend(page_articles)
                    print(f"  {url.split('/')[-1]}: +{len(page_articles)} 条, 累计 {len(articles)}")
                except Exception as e:
                    print(f"  {url}: X {type(e).__name__}: {e}")
                    continue
        else:
            print("\n[2/5] 跳过 (仅采集首页)")

        if not articles:
            print("  X 未找到公告，退出。")
            return

        # ---- [3/5] 列表展示 ----
        print(f"\n[3/5] 公告列表 (共 {len(articles)} 条)：")
        print("-" * 60)
        for i, art in enumerate(articles[:30], 1):  # 最多显示30条
            print(f"  {i:3d}. [{art['date']}] {art['title'][:55]}")
        if len(articles) > 30:
            print(f"  ... 还有 {len(articles) - 30} 条")
        print("-" * 60)

        # ---- [4/5] 详情采集 ----
        detail_limit = DETAIL_LIMIT if DETAIL_LIMIT > 0 else len(articles)
        detail_limit = min(detail_limit, len(articles))
        print(f"\n[4/5] 采集详情页（前 {detail_limit} 条）...")
        results = []

        for i, art in enumerate(articles[:detail_limit], 1):
            print(f"\n  --- 第 {i}/{detail_limit} 条 ---")
            try:
                detail_html = fetch(page, art["url"], wait_selector="#vsb_content")
                detail = parse_detail(detail_html, art["url"])
                summary = summarize(detail["content"])
                category = classify(
                    detail["title"] or art["title"],
                    detail["content"],
                )
                priority = get_priority(detail["title"] or art["title"])

                result = {
                    "title": detail["title"] or art["title"],
                    "date": art["date"],
                    "url": art["url"],
                    "category": category,
                    "priority": priority,
                    "content": detail["content"][:500],
                    "content_full_length": len(detail["content"]),
                    "source": detail["source"],
                    "attachments": detail["attachments"],
                    "summary": summary,
                }
                results.append(result)

                print(f"    标题: {result['title'][:60]}")
                print(f"    分类: {result['category']} | 优先级: {result['priority']}")
                print(f"    来源: {result['source'] or '未提取到'}")
                print(f"    正文长度: {result['content_full_length']} 字")
                print(f"    附件: {len(result['attachments'])} 个")
                print(f"    摘要: {summary[:80]}...")

            except Exception as e:
                print(f"    X 采集失败: {type(e).__name__}: {e}")
                category = classify(art["title"])
                priority = get_priority(art["title"])
                results.append({
                    "title": art["title"], "date": art["date"],
                    "url": art["url"],
                    "category": category,
                    "priority": priority,
                    "error": str(e),
                })

        # ---- [5/5] 输出 JSON ----
        output_file = "crawler_output.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n[5/5] 结构化输出：")
        print("=" * 60)
        for r in results:
            print(f"  [{r.get('category','')}] [{r.get('priority','')}] {r.get('title','')[:55]}")
            print(f"  {r.get('date','')} | {r.get('category','')} | {r.get('url','')}")
            print()
        print("=" * 60)
        print(f"\n完整 JSON 已保存到: {output_file}")
        print(f"完成! 共 {len(page_urls)} 页, {len(articles)} 条列表, 采集 {len(results)} 条详情。")

        return results

    finally:
        page.quit()


if __name__ == "__main__":
    main()
