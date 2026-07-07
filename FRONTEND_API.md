# 前端接口文档

**Base URL**: `http://localhost:8000`

---

## 接口总览

| # | 接口 | 方式 | 用途 | 页面 |
|---|------|------|------|------|
| 1 | `/news` | GET | 新闻列表（支持筛选+搜索） | 首页、分类列表、搜索 |
| 2 | `/news/{id}` | GET | 新闻详情 | 详情页 |
| 3 | `/stats` | GET | 数据统计 | 统计页、首页看板 |

---

## 1. 首页 — 新闻列表

```http
GET /news
```

### 参数

无。直接调用返回全部新闻。

### 返回 JSON 示例

```json
[
  {
    "id": 1,
    "title": "北京邮电大学中国移动联合研究院装修工程竞争性磋商公告",
    "date": "2026-07-07",
    "category": "行政",
    "priority": "medium",
    "summary": "项目概况\n北京邮电大学中国移动联合研究院装修工程 采购项目的潜在供应商应在..."
  },
  {
    "id": 2,
    "title": "北京邮电大学工程师技术中心配套设施采购项目成交公告",
    "date": "2026-07-07",
    "category": "科研",
    "priority": "medium",
    "summary": "一、项目编号：BUPT-HWKYKC-26001..."
  }
]
```

### 前端用法

```js
const res = await fetch('http://localhost:8000/news');
const list = await res.json();

// 渲染列表
list.forEach(item => {
  item.id        // 新闻序号，点击跳转详情 /detail?id=1
  item.title     // 标题
  item.date      // 发布时间
  item.category  // 分类标签
  item.priority  // 优先级标签
  item.summary   // 摘要，列表展示用
});
```

---

## 2. 二级页面 — 分类新闻列表

```http
GET /news?category={分类名}
```

### 参数

| 参数 | 类型 | 必填 | 可选值 | 示例 |
|------|------|------|--------|------|
| `category` | string | 是 | `科研` `教学` `行政` `招聘` `活动` `其他` | `?category=科研` |

### 请求示例

```http
GET /news?category=科研
```

### 返回 JSON 示例

```json
[
  {
    "id": 2,
    "title": "北京邮电大学工程师技术中心配套设施采购项目成交公告",
    "date": "2026-07-07",
    "category": "科研",
    "priority": "medium",
    "summary": "一、项目编号：BUPT-HWKYKC-26001..."
  },
  {
    "id": 3,
    "title": "北京邮电大学建设工程质量检测服务项目公开招标公告",
    "date": "2026-07-06",
    "category": "科研",
    "priority": "medium",
    "summary": "项目概况\n北京邮电大学建设工程质量检测服务项目..."
  }
]
```

### 前端用法

```js
// 点击"科研"分类标签
const category = '科研';
const res = await fetch(`http://localhost:8000/news?category=${category}`);
const list = await res.json();
```

---

## 3. 三级页面 — 新闻详情

```http
GET /news/{id}
```

### 参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `id` | int | 是 | 新闻序号，来自列表的 `id` 字段 | `/news/1` |

### 请求示例

```http
GET /news/1
```

### 返回 JSON 示例

```json
{
  "id": 1,
  "title": "北京邮电大学中国移动联合研究院装修工程竞争性磋商公告",
  "date": "2026-07-07",
  "url": "https://www.bupt.edu.cn/info/1083/90755.htm",
  "category": "行政",
  "priority": "medium",
  "content": "项目概况\n北京邮电大学中国移动联合研究院装修工程 采购项目的潜在供应商应在北京市朝阳区南磨房路37号华腾北搪商务大厦11层1105室获取采购文件，并于2026年07月20日 09点30分（北京时间）前提交响应文件。\n一、项目基本情况\n项目编号：BUPT-GCXCZB-26024...",
  "content_full_length": 1995,
  "source": "",
  "attachments": [],
  "summary": "项目概况\n北京邮电大学中国移动联合研究院装修工程 采购项目的潜在供应商应在..."
}
```

### 字段说明

| 字段 | 说明 | 页面使用 |
|------|------|----------|
| `title` | 标题 | 详情页标题 |
| `date` | 发布时间 | 发布日期 |
| `url` | 北邮官网原文链接 | "查看原文"外链 |
| `category` | 分类 | 分类标签 |
| `priority` | 优先级 | 优先级标签（红/黄/灰） |
| `content` | 正文（前 500 字） | 正文展示区 |
| `content_full_length` | 正文字数 | 辅助信息 |
| `source` | 来源部门 | "来源：xxx" |
| `attachments` | 附件链接数组 | 附件下载列表 |
| `summary` | 摘要 | 分享/预览 |

### 错误响应

```json
// 404 Not Found
{ "detail": "News #999 not found" }
```

### 前端用法

```js
// 从列表页点击进入详情
const id = 1;
const res = await fetch(`http://localhost:8000/news/${id}`);
const detail = await res.json();

// 渲染详情页
detail.title              // 页面标题
detail.date               // 发布日期
detail.category           // 分类标签
detail.priority           // 优先级标签
detail.content            // 正文
detail.source             // "来源：xxx"
detail.attachments        // 附件列表
detail.url                // "查看原文"
detail.content_full_length // 字数统计
```

---

## 4. 搜索 — 标题搜索

```http
GET /news?search={关键词}
```

### 参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `search` | string | 是 | 标题搜索关键词 | `?search=装修` |

### 请求示例

```http
GET /news?search=装修
```

### 返回 JSON 示例

```json
[
  {
    "id": 1,
    "title": "北京邮电大学中国移动联合研究院装修工程竞争性磋商公告",
    "date": "2026-07-07",
    "category": "行政",
    "priority": "medium",
    "summary": "项目概况\n北京邮电大学中国移动联合研究院装修工程 采购项目的潜在供应商应在..."
  }
]
```

### 前端用法

```js
// 搜索框输入后触发
const keyword = '装修';
const res = await fetch(`http://localhost:8000/news?search=${encodeURIComponent(keyword)}`);
const list = await res.json();
```

---

## 5. 统计页面 — 数据统计

```http
GET /stats
```

### 参数

无。

### 请求示例

```http
GET /stats
```

### 返回 JSON 示例

```json
{
  "total": 10,
  "by_category": {
    "行政": 1,
    "科研": 9,
    "教学": 0,
    "招聘": 0,
    "活动": 0
  },
  "by_priority": {
    "high": 0,
    "medium": 10,
    "low": 0
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 新闻总数 |
| `by_category` | object | 各分类数量 |
| `by_priority` | object | 各优先级数量 |

### 前端用法

```js
const res = await fetch('http://localhost:8000/stats');
const stats = await res.json();

stats.total                     // 总数 → 页头数字
stats.by_category['行政']       // 分类数量 → 分类标签上的角标
stats.by_priority['high']       // 紧急数量 → 紧急处理区
```

---

## 组合筛选

`category`、`priority`、`search` 可任意组合。

### 示例

```http
GET /news?category=行政&priority=medium        # 行政类 + 中优先级
GET /news?category=科研&search=芯片            # 科研类 + 标题含"芯片"
GET /news?priority=high                       # 全部高优先级
```

---

## 枚举值

### 分类

| 值 | 含义 |
|----|------|
| `科研` | 科研项目、论文、基金、实验 |
| `教学` | 课程、考试、教学、学生 |
| `行政` | 通知、会议、办公、管理 |
| `招聘` | 招聘、岗位、人才 |
| `活动` | 讲座、比赛、活动 |
| `其他` | 无法匹配 |

### 优先级

| 值 | 含义 |
|----|------|
| `high` | 紧急、截止、立即 |
| `medium` | 报名、申请、会议、公示 |
| `low` | 宣传、新闻、讲座 |

---

## 页面路由建议

```
/                       首页（统计看板 + 新闻列表）
/list?category=科研      二级分类列表
/detail?id=1            三级新闻详情
/search?q=装修           搜索结果页
```

---

## 调试

Swagger 接口文档: [http://localhost:8000/docs](http://localhost:8000/docs)
