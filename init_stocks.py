"""
初始化A股股票数据库
"""
import requests
from app import create_app, db
from app.models import Stock

def init_stocks():
    """从东方财富获取A股股票列表"""
    app = create_app()
    
    with app.app_context():
        # 创建数据库表
        db.create_all()
        
        # 检查是否已有数据
        if Stock.query.first():
            print("股票数据已存在，跳过初始化")
            return
        
        print("正在获取A股股票列表...")
        
        # 东方财富股票列表API
        url = "https://24.push2.eastmoney.com/api/qygl/getlist"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            # 沪市A股
            params = {'pn': 1, 'pz': 5000, 'po': 1, 'np': 1, 'ut': 'bd1d9ddb04089700cf9c27f6f7426281', 
                     'fltt': 2, 'invt': 2, 'fid': 'f3', 'fs': 'm:1+t:23', 'fields': 'f1,f2,f3,f4,f12,f13,f14'}
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            data = response.json()
            
            stocks_added = 0
            
            # 解析沪市
            if 'data' in data and 'diff' in data['data']:
                for item in data['data']['diff']:
                    code = str(item.get('f12', ''))
                    name = item.get('f14', '')
                    
                    if code and name:
                        stock = Stock(
                            code=code,
                            name=name,
                            market='SH',
                            industry=''
                        )
                        db.session.add(stock)
                        stocks_added += 1
            
            # 深市A股
            params['fs'] = 'm:0+t:80'
            response = requests.get(url, params=params, headers=headers, timeout=30)
            data = response.json()
            
            if 'data' in data and 'diff' in data['data']:
                for item in data['data']['diff']:
                    code = str(item.get('f12', ''))
                    name = item.get('f14', '')
                    
                    if code and name:
                        stock = Stock(
                            code=code,
                            name=name,
                            market='SZ',
                            industry=''
                        )
                        db.session.add(stock)
                        stocks_added += 1
            
            db.session.commit()
            print(f"成功添加 {stocks_added} 只股票")
            
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            # 添加一些测试数据
            _add_sample_stocks()


def _add_sample_stocks():
    """添加示例股票数据"""
    sample_stocks = [
        {'code': '600519', 'name': '贵州茅台', 'market': 'SH', 'industry': '白酒'},
        {'code': '000858', 'name': '五粮液', 'market': 'SZ', 'industry': '白酒'},
        {'code': '601318', 'name': '中国平安', 'market': 'SH', 'industry': '保险'},
        {'code': '600036', 'name': '招商银行', 'market': 'SH', 'industry': '银行'},
        {'code': '000333', 'name': '美的集团', 'market': 'SZ', 'industry': '家电'},
        {'code': '002594', 'name': '比亚迪', 'market': 'SZ', 'industry': '汽车'},
        {'code': '600900', 'name': '长江电力', 'market': 'SH', 'industry': '电力'},
        {'code': '300750', 'name': '宁德时代', 'market': 'SZ', 'industry': '锂电池'},
        {'code': '002475', 'name': '立讯精密', 'market': 'SZ', 'industry': '电子'},
        {'code': '688981', 'name': '中芯国际', 'market': 'SH', 'industry': '半导体'},
    ]
    
    for s in sample_stocks:
        stock = Stock(**s)
        db.session.add(stock)
    
    db.session.commit()
    print(f"添加了 {len(sample_stocks)} 只示例股票")


if __name__ == '__main__':
    init_stocks()
