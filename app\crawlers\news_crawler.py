import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class BaseCrawler:
    """爬虫基类"""
    
    def __init__(self, source_name):
        self.source_name = source_name
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def fetch(self, url, encoding='utf-8'):
        """获取网页内容"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = encoding
            return response.text
        except Exception as e:
            logger.error(f"获取 {url} 失败: {e}")
            return None
    
    def parse(self, html):
        """解析网页"""
        if not html:
            return []
        return BeautifulSoup(html, 'lxml')
    
    def extract_stocks(self, text):
        """从文本中提取股票代码和名称"""
        # 匹配股票代码 (6位数字)
        stock_codes = re.findall(r'(\d{6})', text)
        # 匹配股票名称 (中文2-4字)
        stock_names = re.findall(r'([\u4e00-\u9fa5]{2,4})(?:股份|集团|有限|公司|科技|实业|控股)', text)
        return list(set(stock_codes)), list(set(stock_names))
    
    def clean_text(self, text):
        """清理文本"""
        if not text:
            return ''
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


class SinaCrawler(BaseCrawler):
    """新浪财经爬虫"""
    
    def __init__(self):
        super().__init__('新浪财经')
        self.base_url = 'https://finance.sina.com.cn'
    
    def crawl_stock_news(self, stock_code):
        """爬取个股新闻"""
        url = f'{self.base_url}/stock/quote/kline.php?symbol=sh{stock_code}&scale=240'
        # 新浪财经API
        news_url = f'{self.base_url}/stock/{"sh" if stock_code.startswith("6") else "sz"}{stock_code}/news.shtml'
        
        html = self.fetch(news_url)
        if not html:
            return []
        
        soup = self.parse(html)
        news_list = []
        
        for item in soup.select('.news_list li')[:10]:
            title = item.select_one('a')
            if title:
                news_list.append({
                    'title': self.clean_text(title.get_text()),
                    'url': self.base_url + title.get('href', ''),
                    'source': self.source_name
                })
        
        return news_list


class EastMoneyCrawler(BaseCrawler):
    """东方财富爬虫"""
    
    def __init__(self):
        super().__init__('东方财富')
        self.base_url = 'https://www.eastmoney.com'
    
    def crawl_industry_news(self):
        """爬取行业新闻"""
        # 东方财富财经新闻
        url = 'https://news.eastmoney.com/'
        html = self.fetch(url)
        if not html:
            return []
        
        soup = self.parse(html)
        news_list = []
        
        for item in soup.select('.news_list li, .title_list li')[:20]:
            title_elem = item.select_one('a')
            time_elem = item.select_one('span, .time')
            
            if title_elem:
                news_list.append({
                    'title': self.clean_text(title_elem.get_text()),
                    'url': title_elem.get('href', ''),
                    'source': self.source_name,
                    'publish_time': self.parse_time(time_elem.get_text() if time_elem else '')
                })
        
        return news_list
    
    def parse_time(self, time_str):
        """解析时间"""
        if not time_str:
            return datetime.now()
        
        # 简单处理
        try:
            # 尝试解析常见格式
            for fmt in ['%Y-%m-%d %H:%M', '%m-%d %H:%M', '%H:%M']:
                try:
                    return datetime.strptime(time_str, fmt)
                except:
                    pass
        except:
            pass
        
        return datetime.now()


class CNInfoCrawler(BaseCrawler):
    """巨潮资讯网爬虫（官方公告）"""
    
    def __init__(self):
        super().__init__('巨潮资讯')
        self.base_url = 'http://www.cninfo.com.cn'
    
    def crawl_announcements(self, keyword='', limit=50):
        """爬取上市公司公告"""
        # 使用巨潮API
        api_url = f'{self.base_url}/new/hisAnnouncement/query'
        
        data = {
            'pageNum': 1,
            'pageSize': limit,
            'tabName': 'fulltext',
            'column': 'szse',
            'seDate': '',
            'searchkey': keyword,
            'category': '',
            'isHLtitle': 'true'
        }
        
        try:
            response = requests.post(
                api_url, 
                json=data, 
                headers={'Content-Type': 'application/json', **self.headers},
                timeout=10
            )
            result = response.json()
            
            news_list = []
            for item in result.get('announcements', [])[:20]:
                news_list.append({
                    'title': item.get('announcementTitle', ''),
                    'url': f"{self.base_url}/new/disclosure/detail?plate=szse&orgId={item.get('orgId', '')}&announcementId={item.get('announcementId', '')}",
                    'source': self.source_name,
                    'content': item.get('announcementContent', '')[:500],
                    'publish_time': datetime.strptime(item.get('announcementTime', ''), '%Y%m%d%H%M%S') if item.get('announcementTime') else datetime.now()
                })
            
            return news_list
            
        except Exception as e:
            logger.error(f"爬取巨潮公告失败: {e}")
            return []


class IndustryCrawler(BaseCrawler):
    """行业新闻爬虫"""
    
    def __init__(self):
        super().__init__('行业新闻')
        self.sources = [
            {'name': 'IT之家', 'url': 'https://www.ithome.com/', 'encoding': 'utf-8'},
            {'name': '36氪', 'url': 'https://36kr.com/', 'encoding': 'utf-8'},
            {'name': '第一财经', 'url': 'https://www.yicai.com/', 'encoding': 'utf-8'},
        ]
    
    def crawl_all(self):
        """爬取所有行业新闻源"""
        all_news = []
        
        for source in self.sources:
            html = self.fetch(source['url'], source.get('encoding', 'utf-8'))
            if not html:
                continue
            
            soup = self.parse(html)
            
            # 简单提取标题链接
            for item in soup.select('a[href*="/news"], a[href*="/article"]')[:10]:
                title = item.get_text(strip=True)
                href = item.get('href', '')
                
                if title and len(title) > 5:
                    all_news.append({
                        'title': title,
                        'url': href if href.startswith('http') else source['url'] + href,
                        'source': source['name']
                    })
        
        return all_news


def crawl_all_sources():
    """爬取所有资讯源"""
    news_list = []
    
    # 东方财富
    try:
        crawler = EastMoneyCrawler()
        news_list.extend(crawler.crawl_industry_news())
    except Exception as e:
        print(f"东方财富爬取失败: {e}")
    
    # 巨潮资讯
    try:
        crawler = CNInfoCrawler()
        news_list.extend(crawler.crawl_announcements())
    except Exception as e:
        print(f"巨潮资讯爬取失败: {e}")
    
    # 行业新闻
    try:
        crawler = IndustryCrawler()
        news_list.extend(crawler.crawl_all())
    except Exception as e:
        print(f"行业新闻爬取失败: {e}")
    
    return news_list
