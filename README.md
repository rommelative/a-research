# A股资讯智能分析系统

基于财经资讯的股票分析与筛选工具

## 功能特性

- 实时爬取财经资讯（新浪财经、东方财富、巨潮资讯、行业新闻）
- 智能分析资讯与A股股票的关联关系
- 根据利好/利空级别分类股票
- 分为激进型、稳健型、规避型股票池

## 利好级别

| 级别 | 说明 |
|------|------|
| ★★★★★ 重大利好 | 重大资产重组、业绩暴增、政策利好 |
| ★★★★ 利好 | 业绩增长、订单增加 |
| ★★★ 中性 | 一般性公告 |
| ★★ 利空 | 业绩下滑、减持 |
| ★ 重大利空 | 退市风险、重大亏损 |

## 技术栈

- 后端：Python + Flask + SQLAlchemy
- 数据库：SQLite
- 爬虫：Requests + BeautifulSoup
- 部署：Render

## 快速部署到 Render

1. 创建 GitHub 仓库并推送代码
2. 在 Render 上创建新的 Web Service
3. 连接到 GitHub 仓库
4. 设置：
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn wsgi:app`
5. 部署完成！

## 本地运行

```bash
pip install -r requirements.txt
python init_stocks.py
python wsgi.py
```

访问 http://127.0.0.1:5000

## API 接口

- `/api/news` - 获取资讯列表
- `/api/pools` - 获取股票池列表
- `/api/pool/<name>` - 获取指定股票池
- `/api/stats` - 获取统计信息
- `/api/crawl` - 触发爬虫（POST）
