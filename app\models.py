from app import db
from datetime import datetime

class Stock(db.Model):
    """股票基本信息"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)  # 股票代码
    name = db.Column(db.String(50), nullable=False, index=True)  # 股票名称
    industry = db.Column(db.String(50))  # 所属行业
    market = db.Column(db.String(20))  # 上市市场 (SH/SZ)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    news_relations = db.relationship('StockNews', back_populates='stock', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'industry': self.industry,
            'market': self.market
        }

class News(db.Model):
    """资讯基本信息"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)  # 标题
    content = db.Column(db.Text)  # 内容摘要
    source = db.Column(db.String(50), nullable=False)  # 来源
    url = db.Column(db.String(1000), unique=True)  # 原文链接
    publish_time = db.Column(db.DateTime, index=True)  # 发布时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    stock_relations = db.relationship('StockNews', back_populates='news', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content[:200] + '...' if self.content and len(self.content) > 200 else self.content,
            'source': self.source,
            'url': self.url,
            'publish_time': self.publish_time.strftime('%Y-%m-%d %H:%M') if self.publish_time else None
        }

class StockNews(db.Model):
    """股票-资讯关联表"""
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False, index=True)
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=False, index=True)
    
    # 利好级别: 1-重大利好, 2-利好, 3-中性, 4-利空, 5-重大利空
    benefit_level = db.Column(db.Integer, default=3)
    
    # 匹配方式: keyword/ai
    match_method = db.Column(db.String(20))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    stock = db.relationship('Stock', back_populates='news_relations')
    news = db.relationship('News', back_populates='stock_relations')

    def to_dict(self):
        return {
            'id': self.id,
            'stock': self.stock.to_dict() if self.stock else None,
            'news': self.news.to_dict() if self.news else None,
            'benefit_level': self.benefit_level,
            'benefit_label': ['重大利好', '利好', '中性', '利空', '重大利空'][self.benefit_level - 1],
            'match_method': self.match_method
        }

class StockPool(db.Model):
    """股票池"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # 股票池名称
    description = db.Column(db.String(200))  # 说明
    
    # 股票池类型: aggressive(激进), stable(稳健), avoid(规避)
    pool_type = db.Column(db.String(20), nullable=False)
    
    # 包含的利好级别
    benefit_levels = db.Column(db.String(50))  # 如 "1,2" 表示包含重大利好和利好
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'pool_type': self.pool_type,
            'benefit_levels': self.benefit_levels
        }
