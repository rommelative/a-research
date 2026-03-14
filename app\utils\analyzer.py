import re
import logging
from app.models import db, Stock, News, StockNews, StockPool

logger = logging.getLogger(__name__)

# 利好关键词（按强度排序）
BENEFIT_KEYWORDS = {
    1: [  # 重大利好
        '重大资产重组', '业绩暴增', '净利润增长', '签订重大合同', '中标',
        '政策利好', '行业扶持', '退市风险解除', '摘帽', '业绩预增',
        '净利润同比增长', '扭亏为盈', '定增获批', '并购重组'
    ],
    2: [  # 利好
        '业绩增长', '订单增加', '合作签约', '产品发布', '技术突破',
        '市场拓展', '产能扩张', '获批', '中标', '签约',
        '净利润增加', '营收增长', '同比增长', '提升', '增长'
    ],
    4: [  # 利空
        '业绩下滑', '业绩预减', '减持', '监管问询', '警示',
        '处罚', '亏损', '订单减少', '市场萎缩', '风险提示',
        '同比下降', '净利润减少', '营收下降', '预警'
    ],
    5: [  # 重大利空
        '退市风险', '重大亏损', '违法处罚', '涉嫌违法', '立案调查',
        '暂停上市', '终止上市', '资不抵债', '破产重整', '重大违约'
    ]
}

# 中性词（不改变利好级别）
NEUTRAL_KEYWORDS = [
    '召开', '公告', '会议', '年报', '季报', '披露',
    '变更', '转让', '质押', '冻结', '澄清', '说明'
]


class NewsAnalyzer:
    """资讯分析器：关联股票 + 判断利好级别"""
    
    def __init__(self):
        # 加载A股股票列表
        self.stock_codes = self._load_stock_codes()
        logger.info(f"加载了 {len(self.stock_codes)} 个股票代码")
    
    def _load_stock_codes(self):
        """加载股票代码库"""
        stocks = Stock.query.all()
        return {s.code: s for s in stocks}
    
    def analyze_news(self, news):
        """分析单条资讯"""
        text = f"{news.get('title', '')} {news.get('content', '')}"
        
        # 1. 提取关联股票
        stocks = self.extract_stocks(text)
        
        # 2. 判断利好级别
        benefit_level = self.calculate_benefit_level(text)
        
        # 3. 确定匹配方式
        match_method = 'keyword'
        
        return {
            'stocks': stocks,
            'benefit_level': benefit_level,
            'match_method': match_method
        }
    
    def extract_stocks(self, text):
        """从文本中提取关联股票"""
        found_stocks = []
        
        # 匹配6位股票代码
        codes = re.findall(r'(\d{6})', text)
        
        for code in codes:
            # 过滤：A股代码通常是 6(沪市) 或 0/3(深市)
            if code[:1] in ['0', '3', '6'] and code in self.stock_codes:
                found_stocks.append(self.stock_codes[code])
        
        # 匹配股票名称（简单版）
        for stock in self.stock_codes.values():
            if stock.name in text:
                if stock not in found_stocks:
                    found_stocks.append(stock)
        
        return found_stocks
    
    def calculate_benefit_level(self, text):
        """计算利好级别"""
        # 先检查重大利空/利好
        for level in [5, 1]:  # 重大利空先检查
            keywords = BENEFIT_KEYWORDS.get(level, [])
            for kw in keywords:
                if kw in text:
                    # 排除双重否定等情况
                    if level in [4, 5]:  # 利空
                        if '无' in text and ('利空' in text or '风险' in text):
                            continue
                    return level
        
        # 再检查一般利好/利空
        for level in [2, 4]:
            keywords = BENEFIT_KEYWORDS.get(level, [])
            for kw in keywords:
                if kw in text:
                    return level
        
        # 默认中性
        return 3
    
    def batch_analyze(self, news_list):
        """批量分析资讯"""
        results = []
        
        for news in news_list:
            analysis = self.analyze_news(news)
            
            # 只保留有关联股票的资讯
            if analysis['stocks']:
                results.append({
                    'news': news,
                    'stocks': analysis['stocks'],
                    'benefit_level': analysis['benefit_level'],
                    'match_method': analysis['match_method']
                })
        
        return results


class StockPoolManager:
    """股票池管理器"""
    
    # 默认股票池配置
    DEFAULT_POOLS = [
        {
            'name': '激进型股票池',
            'description': '重大利好+利好，适合追求高收益投资者',
            'pool_type': 'aggressive',
            'benefit_levels': '1,2'
        },
        {
            'name': '稳健型股票池',
            'description': '中性资讯，关注基本面稳健的股票',
            'pool_type': 'stable',
            'benefit_levels': '3'
        },
        {
            'name': '规避型股票池',
            'description': '利空+重大利空，需要注意风险',
            'pool_type': 'avoid',
            'benefit_levels': '4,5'
        }
    ]
    
    @staticmethod
    def init_default_pools():
        """初始化默认股票池"""
        for pool_config in StockPoolManager.DEFAULT_POOLS:
            existing = StockPool.query.filter_by(name=pool_config['name']).first()
            if not existing:
                pool = StockPool(**pool_config)
                db.session.add(pool)
        
        db.session.commit()
    
    @staticmethod
    def get_pool_stocks(pool_name):
        """获取指定股票池的股票"""
        pool = StockPool.query.filter_by(name=pool_name).first()
        if not pool:
            return []
        
        # 解析包含的利好级别
        levels = [int(l) for l in pool.benefit_levels.split(',')]
        
        # 查询关联的股票
        relations = StockNews.query.filter(
            StockNews.benefit_level.in_(levels)
        ).order_by(StockNews.created_at.desc()).limit(100).all()
        
        # 去重
        stocks_map = {}
        for rel in relations:
            if rel.stock.code not in stocks_map:
                stocks_map[rel.stock.code] = {
                    'stock': rel.stock.to_dict(),
                    'benefit_level': rel.benefit_level,
                    'benefit_label': ['重大利好', '利好', '中性', '利空', '重大利空'][rel.benefit_level - 1],
                    'latest_news': rel.news.title[:50] + '...' if len(rel.news.title) > 50 else rel.news.title
                }
        
        return list(stocks_map.values())
    
    @staticmethod
    def get_all_pools():
        """获取所有股票池"""
        return [p.to_dict() for p in StockPool.query.all()]
