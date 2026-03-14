from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import logging

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stocks.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'stock-research-secret-key'

    db.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    # 初始化定时任务
    init_scheduler()

    return app

def init_scheduler():
    """初始化定时爬虫任务"""
    scheduler = BackgroundScheduler()
    from app.crawlers.news_crawler import crawl_all_sources
    # 每天9:00-15:00之间每30分钟爬取一次
    scheduler.add_job(func=crawl_all_sources, trigger='cron', hour='9-14', minute='*/30')
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
