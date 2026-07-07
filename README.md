# 北邮官网数据采集与派单系统

北京邮电大学官网公开信息自动采集、分类与派单系统。面向校内行政办公场景，将官网公告按类别和优先级自动分发到对应部门。

---

## 1. 项目介绍

本项目采集[北京邮电大学官网](https://www.bupt.edu.cn)「信息公告」栏目的公开数据，实现：

- **自动采集**：定时爬取公告列表及详情正文
- **智能分类**：根据标题和正文关键词，自动归类到科研/教学/行政/招聘/活动
- **优先级判断**：识别紧急通知、会议报名、一般新闻等不同优先级
- **内容摘要**：自动生成正文摘要，供快速浏览
- **API 接口**：提供 RESTful API，供前端或派单系统消费

### 项目成员

| 角色 | 职责 |
|------|------|
| D 成员 | 后端开发（爬虫 + 数据库 + API） |
| 其他成员 | 前端开发（待定） |

---

## 2. 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 爬虫引擎 | DrissionPage | 控制 Edge 浏览器，绕过 Cloudflare，执行 JS 渲染 |
| HTML 解析 | BeautifulSoup4 + lxml | CSS 选择器提取 DOM 数据 |
| 后端框架 | FastAPI | RESTful API 接口 |
| 数据格式 | JSON | 爬虫输出与接口数据源 |
| 运行环境 | Python 3.10+ | Windows / Linux / macOS |

> 后续计划接入 MySQL（SQLAlchemy ORM）替代 JSON 文件存储。

---

## 3. 系统流程图

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  北邮官网    │────▶│  crawler_demo │────▶│  crawler_     │
│  xxgg.htm   │     │  .py          │     │  output.json  │
│  (信息公告)  │     │  采集/解析/分类 │     │  (结构化数据)  │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                 │
                                                 │ 读取
                                                 ▼
                  ┌──────────────┐     ┌───────────────┐
                  │   前端页面    │◀────│  api_server   │
                  │   (待开发)    │     │  .py          │
                  │              │     │  FastAPI      │
                  └──────────────┘     └───────────────┘
```

---

## 4. 爬虫流程

```
[1/5] 首页采集
  │
  ├── DrissionPage 启动 Edge 浏览器
  ├── 访问 https://www.bupt.edu.cn/xxgg.htm
  ├── 绕过 Cloudflare WAF（JS 挑战 + 浏览器指纹）
  ├── 等待 ul.list 渲染完成
  └── 解析分页块，获取总页数(216页)

[2/5] 分页遍历
  │
  ├── 生成 URL: xxgg.htm → xxgg/215.htm → xxgg/214.htm → ...
  └── 每页 10 条，累计采集

[3/5] 列表解析
  │
  ├── CSS 选择器: ul.list > li
  ├── 标题: a 标签文本
  ├── 日期: .date-year + .date-day
  └── 链接: a[href] → urljoin 补全

[4/5] 详情采集
  │
  ├── 逐条访问 info/1083/{id}.htm
  ├── 标题: h1 / .title / .con-title
  ├── 正文: #vsb_content（Visual SiteBuilder CMS）
  ├── 来源: 正则 "来源：xxx"
  ├── 附件: 扩展名(.pdf/.doc/.zip) + "附件"关键词
  ├── 分类: 标题(+2) + 正文(+1) 关键词权重
  ├── 优先级: 标题关键词匹配
  └── 摘要: 前 150 字，标点处截断

[5/5] JSON 输出 → crawler_output.json
```

### 反爬策略

| 问题 | 方案 |
|------|------|
| Cloudflare 412 | DrissionPage 控制真实 Edge 浏览器，非 headless |
| JS 动态渲染 | 等待 `ul.list` 元素出现后再抓取 |
| 请求频率控制 | 详情页间间隔 1s |

---

## 5. JSON 数据示例

```json
{
  "title": "北京邮电大学中国移动联合研究院装修工程竞争性磋商公告",
  "date": "2026-07-07",
  "url": "https://www.bupt.edu.cn/info/1083/90755.htm",
  "category": "行政",
  "priority": "medium",
  "content": "项目概况\n北京邮电大学中国移动联合研究院装修工程...",
  "content_full_length": 1995,
  "source": "",
  "attachments": [],
  "summary": "项目概况\n北京邮电大学中国移动联合研究院装修工程 采购项目的潜在供应商应在..."
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 公告标题 |
| `date` | string | 发布时间 (YYYY-MM-DD) |
| `url` | string | 原文链接 |
| `category` | string | 分类: 科研/教学/行政/招聘/活动/其他 |
| `priority` | string | 优先级: high/medium/low |
| `content` | string | 正文前 500 字 |
| `content_full_length` | int | 正文字数 |
| `source` | string | 来源部门 |
| `attachments` | array | 附件链接列表 |
| `summary` | string | 智能摘要 (~150字) |

---

## 6. API 接口说明

**Base URL**: `http://localhost:8000`

### GET /news

返回全部新闻数据。

**响应**: `200 OK`

```json
[
  { "id": 1, "title": "...", "category": "行政", ... },
  { "id": 2, "title": "...", "category": "行政", ... }
]
```

---

### GET /news/{id}

返回单条新闻。

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | int | 新闻序号，从 1 开始 |

**响应**: `200 OK`

```json
{
  "id": 1,
  "title": "北京邮电大学中国移动联合研究院装修工程竞争性磋商公告",
  "date": "2026-07-07",
  "url": "https://www.bupt.edu.cn/info/1083/90755.htm",
  "category": "行政",
  "priority": "medium",
  "content": "项目概况\n...",
  "summary": "项目概况\n..."
}
```

**错误**: `404 Not Found`

```json
{ "detail": "News #999 not found" }
```

---

### 分类规则

| 类别 | 关键词 | 派单方向 |
|------|--------|----------|
| 科研 | 科研、项目、论文、基金、实验 | 科研院 |
| 教学 | 课程、考试、教学、学生 | 教务处 |
| 行政 | 通知、会议、办公、管理 | 党政办 |
| 招聘 | 招聘、岗位、人才 | 人事处 |
| 活动 | 讲座、比赛、活动 | 团委/学工 |
| 其他 | 无匹配 | 管理员 |

### 优先级规则

| 级别 | 触发词 | 含义 |
|------|--------|------|
| `high` | 紧急、截止、立即、重要通知 | 需立即处理 |
| `medium` | 报名、申请、会议、公示 | 有时效性 |
| `low` | 宣传、新闻、讲座、报告会 | 告知类 |

---

## 7. 运行方法

### 安装依赖

```bash
cd bupt_dispatch_system
pip install -r requirements.txt
```

### 运行爬虫

```bash
python crawler_demo.py
```

可修改 `crawler_demo.py` 顶部的配置：

```python
PAGES_TO_CRAWL = 3    # 爬取页数（3页=30条）
DETAIL_LIMIT = 10      # 采集详情条数
```

输出文件：`crawler_output.json`

### 启动 API 服务

```bash
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 访问接口

| 地址 | 说明 |
|------|------|
| http://localhost:8000/docs | Swagger 接口文档 |
| http://localhost:8000/news | 全部新闻 |
| http://localhost:8000/news/1 | 第1条新闻 |

### 项目结构

```
bupt_dispatch_system/
├── crawler_demo.py        # 爬虫主程序
├── crawler_output.json    # 爬虫产出数据
├── api_server.py          # FastAPI 后端接口
├── requirements.txt       # 依赖列表
└── README.md              # 本文档
```
