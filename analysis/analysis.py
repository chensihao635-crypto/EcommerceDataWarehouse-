# -*- coding: utf-8 -*-
# ============================================================
# 电商用户订单数据仓库分析平台 - 分析模块
# ============================================================

import pandas as pd
from pathlib import Path
from loguru import logger
import yaml
from sqlalchemy import create_engine, text
import json
from datetime import datetime


class DataAnalyzer:
    """数据分析类 - 从MySQL读取数据并进行业务分析"""
    
    def __init__(self, config_path=None):
        """
        初始化分析器
        
        Args:
            config_path: 配置文件路径
        """
        self.project_root = Path(__file__).parent.parent
        
        if config_path is None:
            config_path = self.project_root / "config" / "config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.engine = None
        self.results = {}
        
        logger.info("数据分析器初始化完成")
    
    def get_connection(self):
        """获取数据库连接"""
        db_config = self.config['database']
        connection_string = (
            f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['name']}"
            f"?charset=utf8mb4"
        )
        
        if self.engine is None:
            self.engine = create_engine(connection_string, pool_recycle=3600)
        
        return self.engine
    
    def query(self, sql):
        """执行SQL查询"""
        engine = self.get_connection()
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn)
    
    def analyze_user_overview(self):
        """
        分析1：用户概览分析
        包括：活跃用户数、复购率、平均消费金额等
        """
        logger.info("执行用户概览分析...")
        
        sql = """
        SELECT 
            COUNT(DISTINCT customer_id) as total_users,
            COUNT(DISTINCT CASE WHEN total_orders > 1 THEN customer_id END) as repeat_users,
            ROUND(AVG(total_amount), 2) as avg_amount,
            ROUND(MAX(total_amount), 2) as max_amount,
            ROUND(MIN(total_amount), 2) as min_amount,
            ROUND(SUM(total_amount), 2) as total_revenue,
            country
        FROM dim_users
        GROUP BY country
        ORDER BY total_revenue DESC
        LIMIT 10
        """
        
        df = self.query(sql)
        
        self.results['user_overview'] = {
            'data': df.to_dict('records'),
            'summary': {
                'top_country': df.iloc[0]['country'] if len(df) > 0 else 'N/A',
                'top_revenue': float(df.iloc[0]['total_revenue']) if len(df) > 0 else 0
            }
        }
        
        logger.info(f"用户概览分析完成，共{len(df)}个国家")
        return df
    
    def analyze_monthly_trend(self):
        """
        分析2：月度销售趋势
        包括：每月销售额、订单数、平均客单价等
        """
        logger.info("执行月度销售趋势分析...")
        
        sql = """
        SELECT 
            DATE_FORMAT(invoice_date, '%Y-%m') as month,
            COUNT(DISTINCT invoice_no) as order_count,
            COUNT(DISTINCT customer_id) as customer_count,
            SUM(quantity) as total_quantity,
            ROUND(SUM(total_amount), 2) as total_revenue,
            ROUND(AVG(total_amount), 2) as avg_order_amount
        FROM fact_sales
        GROUP BY DATE_FORMAT(invoice_date, '%Y-%m')
        ORDER BY month
        """
        
        df = self.query(sql)
        
        self.results['monthly_trend'] = {
            'data': df.to_dict('records'),
            'summary': {
                'best_month': df.loc[df['total_revenue'].idxmax(), 'month'] if len(df) > 0 else 'N/A',
                'worst_month': df.loc[df['total_revenue'].idxmin(), 'month'] if len(df) > 0 else 'N/A'
            }
        }
        
        logger.info(f"月度趋势分析完成，共{len(df)}个月")
        return df
    
    def analyze_product_performance(self):
        """
        分析3：商品销售表现
        包括：热销商品、滞销商品、ABC分类等
        """
        logger.info("执行商品销售表现分析...")
        
        sql = """
        SELECT 
            stock_code,
            description,
            SUM(quantity) as total_quantity,
            ROUND(SUM(total_amount), 2) as total_revenue,
            COUNT(DISTINCT invoice_no) as order_count,
            ROUND(AVG(unit_price), 2) as avg_price
        FROM fact_sales
        WHERE stock_code IS NOT NULL
        GROUP BY stock_code, description
        ORDER BY total_revenue DESC
        LIMIT 20
        """
        
        df = self.query(sql)
        
        self.results['product_performance'] = {
            'data': df.to_dict('records'),
            'summary': {
                'top_product': df.iloc[0]['description'] if len(df) > 0 else 'N/A',
                'top_revenue': float(df.iloc[0]['total_revenue']) if len(df) > 0 else 0
            }
        }
        
        logger.info(f"商品表现分析完成，共{len(df)}个商品")
        return df
    
    def analyze_customer_segments(self):
        """
        分析4：客户分层分析（RFM模型简化版）
        """
        logger.info("执行客户分层分析...")
        
        sql = """
        SELECT 
            customer_id,
            DATEDIFF('2011-12-31', MAX(invoice_date)) as recency_days,
            COUNT(DISTINCT invoice_no) as frequency,
            ROUND(SUM(total_amount), 2) as monetary,
            CASE 
                WHEN DATEDIFF('2011-12-31', MAX(invoice_date)) <= 90 AND COUNT(DISTINCT invoice_no) >= 5 THEN '高价值客户'
                WHEN DATEDIFF('2011-12-31', MAX(invoice_date)) <= 180 THEN '活跃客户'
                WHEN DATEDIFF('2011-12-31', MAX(invoice_date)) <= 365 THEN '普通客户'
                ELSE '流失客户'
            END as customer_segment
        FROM fact_sales
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
        """
        
        df = self.query(sql)
        
        # 统计各分层人数
        segment_stats = df['customer_segment'].value_counts().to_dict()
        
        self.results['customer_segments'] = {
            'data': segment_stats,
            'summary': segment_stats
        }
        
        logger.info(f"客户分层分析完成，分层统计: {segment_stats}")
        return df
    
    def analyze_regional_distribution(self):
        """
        分析5：地区销售分布
        """
        logger.info("执行地区销售分布分析...")
        
        sql = """
        SELECT 
            country,
            COUNT(DISTINCT invoice_no) as order_count,
            COUNT(DISTINCT customer_id) as customer_count,
            ROUND(SUM(total_amount), 2) as total_revenue,
            ROUND(AVG(total_amount), 2) as avg_order_amount
        FROM fact_sales
        GROUP BY country
        ORDER BY total_revenue DESC
        LIMIT 15
        """
        
        df = self.query(sql)
        
        self.results['regional_distribution'] = {
            'data': df.to_dict('records'),
            'summary': {
                'top_country': df.iloc[0]['country'] if len(df) > 0 else 'N/A',
                'country_count': len(df)
            }
        }
        
        logger.info(f"地区分布分析完成，共{len(df)}个国家")
        return df
    
    def run_all_analysis(self):
        """
        执行所有分析任务
        """
        logger.info("=" * 60)
        logger.info("开始执行数据分析")
        logger.info("=" * 60)
        
        try:
            # 执行各分析
            self.analyze_user_overview()
            self.analyze_monthly_trend()
            self.analyze_product_performance()
            self.analyze_customer_segments()
            self.analyze_regional_distribution()
            
            # 保存结果
            self.save_results()
            
            logger.info("=" * 60)
            logger.info("所有分析任务完成!")
            logger.info("=" * 60)
            
            return self.results
            
        except Exception as e:
            logger.error(f"分析执行失败: {e}")
            raise
    
    def save_results(self):
        """
        保存分析结果到JSON文件
        """
        output_dir = self.project_root / "output" / "analysis"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "analysis_results.json"
        
        # 转换数据为可序列化格式
        serializable_results = {}
        for key, value in self.results.items():
            if isinstance(value, dict):
                serializable_results[key] = value
            else:
                serializable_results[key] = str(value)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"分析结果已保存: {output_file}")
    
    def get_executive_summary(self):
        """
        生成执行摘要
        """
        summary = {
            'project': '电商用户订单数据仓库分析平台',
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'key_findings': []
        }
        
        if 'user_overview' in self.results:
            data = self.results['user_overview'].get('data', [])
            if data:
                summary['key_findings'].append(
                    f"最高收入国家: {data[0].get('country', 'N/A')}, "
                    f"收入: ${data[0].get('total_revenue', 0):,.2f}"
                )
        
        if 'monthly_trend' in self.results:
            data = self.results['monthly_trend'].get('data', [])
            if data:
                summary['key_findings'].append(
                    f"最佳销售月份: {data[-1].get('month', 'N/A')}, "
                    f"收入: ${data[-1].get('total_revenue', 0):,.2f}"
                )
        
        if 'customer_segments' in self.results:
            segments = self.results['customer_segments'].get('data', {})
            if segments:
                summary['key_findings'].append(
                    f"客户分层: {segments}"
                )
        
        return summary


if __name__ == "__main__":
    analyzer = DataAnalyzer()
    results = analyzer.run_all_analysis()
    
    # 打印执行摘要
    summary = analyzer.get_executive_summary()
    print("\n" + "=" * 60)
    print("执行摘要")
    print("=" * 60)
    print(f"项目: {summary['project']}")
    print(f"分析时间: {summary['analysis_date']}")
    print("\n关键发现:")
    for finding in summary['key_findings']:
        print(f"  - {finding}")