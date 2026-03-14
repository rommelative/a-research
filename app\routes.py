from flask import Blueprint, jsonify, request
from app import db
from app.models import Stock, News, StockNews, StockPool
from app.crawlers.news_crawler import SinaCrawler, EastMoneyCrawler, CNInfoCrawler, IndustryCrawler
from app.utils.analyzer import NewsAnalyzer, StockPoolManager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)


# ============ 资讯相关 API ============

@main.route('/api/news', methods=['GET'])
def get_news():
    """获取资讯列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    source = request.args.get('source')
    
    query = News.query
    
    if source:
        query = query.filter_by(source=source)
    
    news = query.order_by(News.publish_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'news': [n.to_dict() for n in news.items],
        'total': news.total,
        'pages': news.pages,
        'current_page': page
    })


@main.route('/api/news/<int:news_id>', methods=['GET'])
def get_news_detail(news_id):
    """获取资讯详情"""
    news = News.query.get_or_404(news_id)
    return jsonify(news.to_dict())


# ============ 股票相关 API ============

@main.route('/api/stocks', methods=['GET'])
def get_stocks():
    """获取股票列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    industry = request.args.get('industry')
    
    query = Stock.query
    
    if industry:
        query = query.filter_by(industry=industry)
    
    stocks = query.order_by(Stock.code).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'stocks': [s.to_dict() for s in stocks.items],
        'total': stocks.total,
        'pages': stocks.pages,
        'current_page': page
    })


@main.route('/api/stock/<code>', methods=['GET'])
def get_stock_detail(code):
    """获取股票详情和关联资讯"""
    stock = Stock.query.filter_by(code=code).first_or_404()
    
    # 获取关联资讯
    relations = StockNews.query.filter_by(stock_id=stock.id).order_by(
        StockNews.created_at.desc()
    ).limit(20).all()
    
    return jsonify({
        'stock': stock.to_dict(),
        'news': [r.to_dict() for r in relations]
    })


# ============ 股票池相关 API ============

@main.route('/api/pools', methods=['GET'])
def get_pools():
    """获取所有股票池"""
    pools = StockPoolManager.get_all_pools()
    return jsonify({'pools': pools})


@main.route('/api/pool/<pool_name>', methods=['GET'])
def get_pool_detail(pool_name):
    """获取指定股票池详情"""
    # 先URL解码
    from urllib.parse import unquote
    pool_name = unquote(pool_name)
    
    stocks = StockPoolManager.get_pool_stocks(pool_name)
    
    # 获取股票池信息
    pool = StockPool.query.filter_by(name=pool_name).first()
    
    return jsonify({
        'pool': pool.to_dict() if pool else None,
        'stocks': stocks,
        'count': len(stocks)
    })


# ============ 爬虫相关 API ============

@main.route('/api/crawl', methods=['POST'])
def trigger_crawl():
    """手动触发爬虫"""
    source = request.json.get('source', 'all')
    
    try:
        if source == 'all' or source == 'eastmoney':
            crawler = EastMoneyCrawler()
            news_list = crawler.crawl_industry_news()
            _save_news(news_list)
        
        if source == 'all' or source == 'cninfo':
            crawler = CNInfoCrawler()
            news_list = crawler.crawl_announcements()
            _save_news(news_list)
        
        if source == 'all' or source == 'industry':
            crawler = IndustryCrawler()
            news_list = crawler.crawl_all()
            _save_news(news_list)
        
        # 分析并关联股票
        _analyze_and_link()
        
        return jsonify({'status': 'success', 'message': f'爬取完成'})
    
    except Exception as e:
        logger.error(f"爬取失败: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@main.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    return jsonify({
        'news_count': News.query.count(),
        'stock_count': Stock.query.count(),
        'relation_count': StockNews.query.count(),
        'pool_count': StockPool.query.count()
    })


# ============ 内部函数 ============

def _save_news(news_list):
    """保存资讯到数据库"""
    for news_data in news_list:
        # 检查是否已存在
        existing = News.query.filter_by(url=news_data.get('url')).first()
        if existing:
            continue
        
        news = News(
            title=news_data.get('title', ''),
            content=news_data.get('content', ''),
            source=news_data.get('source', ''),
            url=news_data.get('url', ''),
            publish_time=news_data.get('publish_time', datetime.now())
        )
        db.session.add(news)
    
    db.session.commit()


def _analyze_and_link():
    """分析资讯并关联股票"""
    analyzer = NewsAnalyzer()
    
    # 获取最近未分析的资讯
    recent_news = News.query.order_by(News.created_at.desc()).limit(100).all()
    
    for news in recent_news:
        # 检查是否已有关联
        existing = StockNews.query.filter_by(news_id=news.id).first()
        if existing:
            continue
        
        # 分析
        result = analyzer.analyze_news(news.to_dict())
        
        # 保存关联
        for stock in result['stocks']:
            relation = StockNews(
                stock_id=stock.id,
                news_id=news.id,
                benefit_level=result['benefit_level'],
                match_method=result['match_method']
            )
            db.session.add(relation)
    
    db.session.commit()


# ============ 页面路由 ============

@main.route('/')
def index():
    """首页"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>A股资讯智能分析系统</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            .card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; }
            .pool-aggressive { background: #fff5f5; border-color: #ff6b6b; }
            .pool-stable { background: #f0f9ff; border-color: #4dabf7; }
            .pool-avoid { background: #fff9db; border-color: #ffd43b; }
            a { color: #0066cc; }
            .btn { display: inline-block; padding: 8px 16px; background: #0066cc; color: white; 
                   text-decoration: none; border-radius: 4px; margin: 5px; }
            .btn:hover { background: #0052a3; }
        </style>
    </head>
    <body>
        <h1>A股资讯智能分析系统</h1>
        <p>基于财经资讯的股票分析与筛选工具</p>
        
        <div class="card">
            <h2>功能说明</h2>
            <ul>
                <li>实时爬取财经资讯（新浪、东方财富、巨潮、行业新闻）</li>
                <li>智能分析资讯与A股股票的关联关系</li>
                <li>根据利好/利空级别分类股票</li>
                <li>分为激进型、稳健型、规避型股票池</li>
            </ul>
        </div>
        
        <h2>股票池</h2>
        <div class="card pool-aggressive">
            <h3><a href="/pool/%E6%BF%80%E8%BF%9A%E5%9E%8B">激进型股票池</a></h3>
            <p>重大利好 + 利好资讯</p>
        </div>
        
        <div class="card pool-stable">
            <h3><a href="/pool/%E7%A8%B3%E5%81%A5%E5%9E%8B">稳健型股票池</a></h3>
            <p>中性资讯</p>
        </div>
        
        <div class="card pool-avoid">
            <h3><a href="/pool/%E8%A6%81%E9%81%BF%E5%9E%8B">规避型股票池</a></h3>
            <p>利空 + 重大利空资讯</p>
        </div>
        
        <h2>API 接口</h2>
        <ul>
            <li><a href="/api/news">/api/news</a> - 获取资讯列表</li>
            <li><a href="/api/pools">/api/pools</a> - 获取股票池列表</li>
            <li><a href="/api/stats">/api/stats</a> - 获取统计信息</li>
        </ul>
        
        <h2>管理</h2>
        <a class="btn" href="/api/crawl" onclick="fetch(this.href); return false;">触发爬虫</a>
    </body>
    </html>
    '''


@main.route('/pool/<pool_name>')
def pool_page(pool_name):
    """股票池详情页"""
    from urllib.parse import unquote
    pool_name = unquote(pool_name)
    
    stocks = StockPoolManager.get_pool_stocks(pool_name)
    
    pool = StockPool.query.filter_by(name=pool_name).first()
    
    pool_type_colors = {
        'aggressive': '#ff6b6b',
        'stable': '#4dabf7',
        'avoid': '#ffd43b'
    }
    
    color = pool_type_colors.get(pool.pool_type, '#666') if pool else '#666'
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>{pool_name} - A股资讯分析</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: {color}; }}
            .stock {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; }}
            .level-1 {{ background: #fff5f5; border-left: 4px solid #ff6b6b; }}
            .level-2 {{ background: #fff0f0; border-left: 4px solid #ffa8a8; }}
            .level-3 {{ background: #f8f9fa; border-left: 4px solid #adb5bd; }}
            .level-4 {{ background: #fff9db; border-left: 4px solid #ffd43b; }}
            .level-5 {{ background: #fff5c0; border-left: 4px solid #fab005; }}
            a {{ color: #0066cc; }}
            .back {{ display: inline-block; padding: 8px 16px; background: #666; color: white; 
                    text-decoration: none; border-radius: 4px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <a class="back" href="/">← 返回首页</a>
        <h1>{pool_name}</h1>
        <p>{pool.description if pool else ''}</p>
        <p>共 {len(stocks)} 只股票</p>
    '''
    
    for s in stocks:
        level_class = f"level-{s['benefit_level']}"
        html += f'''
        <div class="stock {level_class}">
            <h3>{s['stock']['code']} - {s['stock']['name']}</h3>
            <p>利好级别: {s['benefit_label']}</p>
            <p>最新资讯: {s['latest_news']}</p>
        </div>
        '''
    
    html += '</body></html>'
    
    return html
