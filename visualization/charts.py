# -*- coding: utf-8 -*-
# ============================================================
# 电商用户订单数据仓库 - 数据可视化模块
# ============================================================

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from pathlib import Path
import yaml
from sqlalchemy import create_engine, text
from loguru import logger

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


class DataVisualizer:
    """数据可视化类 - 从MySQL读取数据并生成图表"""

    def __init__(self, config_path=None):
        self.project_root = Path(__file__).parent.parent

        if config_path is None:
            config_path = self.project_root / "config" / "config.yaml"

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.engine = None
        self.output_dir = self.project_root / "output" / "charts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("数据可视化器初始化完成")

    def get_connection(self):
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
        engine = self.get_connection()
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn)

    def chart_monthly_revenue(self):
        """月度销售额趋势图"""
        logger.info("生成月度销售额趋势图...")

        sql = """
        SELECT DATE_FORMAT(invoice_date, '%Y-%m') as month,
               ROUND(SUM(total_amount), 2) as total_revenue,
               COUNT(DISTINCT invoice_no) as order_count
        FROM fact_sales
        GROUP BY DATE_FORMAT(invoice_date, '%Y-%m')
        ORDER BY month
        """
        df = self.query(sql)

        fig, ax1 = plt.subplots(figsize=(12, 6))

        color = '#2196F3'
        ax1.bar(df['month'], df['total_revenue'], color=color, alpha=0.7, label='销售额')
        ax1.set_xlabel('月份', fontsize=12)
        ax1.set_ylabel('销售额 ($)', color=color, fontsize=12)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.set_xticklabels(df['month'], rotation=45, ha='right')

        ax2 = ax1.twinx()
        color2 = '#FF5722'
        ax2.plot(df['month'], df['order_count'], color=color2, marker='o', linewidth=2, label='订单数')
        ax2.set_ylabel('订单数', color=color2, fontsize=12)
        ax2.tick_params(axis='y', labelcolor=color2)

        plt.title('月度销售额与订单数趋势', fontsize=16, fontweight='bold')
        fig.tight_layout()

        filepath = self.output_dir / '01_monthly_revenue_trend.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"月度趋势图已保存: {filepath}")
        return filepath

    def chart_top_countries(self):
        """Top 10国家销售额饼图"""
        logger.info("生成国家销售额饼图...")

        sql = """
        SELECT country, ROUND(SUM(total_amount), 2) as total_revenue
        FROM fact_sales
        GROUP BY country
        ORDER BY total_revenue DESC
        LIMIT 10
        """
        df = self.query(sql)

        fig, ax = plt.subplots(figsize=(10, 8))

        colors = plt.cm.Set3(range(len(df)))
        wedges, texts, autotexts = ax.pie(
            df['total_revenue'],
            labels=df['country'],
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            pctdistance=0.85
        )

        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontsize(9)

        plt.title('Top 10 国家销售额占比', fontsize=16, fontweight='bold')
        fig.tight_layout()

        filepath = self.output_dir / '02_top_countries_pie.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"国家饼图已保存: {filepath}")
        return filepath

    def chart_top_products(self):
        """Top 20热销商品柱状图"""
        logger.info("生成热销商品柱状图...")

        sql = """
        SELECT description, ROUND(SUM(total_amount), 2) as total_revenue
        FROM fact_sales
        WHERE stock_code IS NOT NULL AND description IS NOT NULL
        GROUP BY stock_code, description
        ORDER BY total_revenue DESC
        LIMIT 20
        """
        df = self.query(sql)

        fig, ax = plt.subplots(figsize=(14, 8))

        # 截断过长的名称
        df['short_desc'] = df['description'].apply(lambda x: x[:25] + '...' if len(str(x)) > 25 else x)

        colors = plt.cm.RdYlGn(range(0, 256, 256 // len(df)))
        bars = ax.barh(df['short_desc'], df['total_revenue'], color=colors)

        ax.set_xlabel('销售额 ($)', fontsize=12)
        ax.set_ylabel('商品', fontsize=12)
        ax.set_title('Top 20 热销商品', fontsize=16, fontweight='bold')
        ax.invert_yaxis()

        # 添加数值标签
        for bar, val in zip(bars, df['total_revenue']):
            ax.text(bar.get_width() + 500, bar.get_y() + bar.get_height()/2,
                    f'${val:,.0f}', va='center', fontsize=9)

        fig.tight_layout()

        filepath = self.output_dir / '03_top_products_bar.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"热销商品图已保存: {filepath}")
        return filepath

    def chart_customer_segments(self):
        """客户分层饼图"""
        logger.info("生成客户分层饼图...")

        sql = """
        SELECT segment, COUNT(*) as cnt
        FROM (
            SELECT customer_id,
                CASE 
                    WHEN DATEDIFF('2011-12-31', MAX(invoice_date)) <= 90 AND COUNT(DISTINCT invoice_no) >= 5 THEN '1-High Value'
                    WHEN DATEDIFF('2011-12-31', MAX(invoice_date)) <= 180 THEN '2-Active'
                    WHEN DATEDIFF('2011-12-31', MAX(invoice_date)) <= 365 THEN '3-Regular'
                    ELSE '4-Churned'
                END as segment
            FROM fact_sales
            WHERE customer_id IS NOT NULL
            GROUP BY customer_id
        ) t
        GROUP BY segment
        ORDER BY segment
        """
        df = self.query(sql)

        fig, ax = plt.subplots(figsize=(8, 8))

        colors = ['#4CAF50', '#2196F3', '#FFC107', '#F44336']
        explode = tuple([0.05] * len(df))
        wedges, texts, autotexts = ax.pie(
            df['cnt'],
            labels=df['segment'],
            autopct='%1.1f%%',
            colors=colors[:len(df)],
            startangle=90,
            explode=explode
        )

        for text in texts:
            text.set_fontsize(12)
        for autotext in autotexts:
            autotext.set_fontsize(11)
            autotext.set_fontweight('bold')

        plt.title('Customer Segments (RFM)', fontsize=16, fontweight='bold')
        fig.tight_layout()

        filepath = self.output_dir / '04_customer_segments_pie.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"客户分层图已保存: {filepath}")
        return filepath

    def chart_daily_orders(self):
        """每日订单量时序图"""
        logger.info("生成每日订单量时序图...")

        sql = """
        SELECT DATE(invoice_date) as dt,
               COUNT(DISTINCT invoice_no) as order_count,
               ROUND(SUM(total_amount), 2) as daily_revenue
        FROM fact_sales
        GROUP BY DATE(invoice_date)
        ORDER BY dt
        """
        df = self.query(sql)
        df['dt'] = pd.to_datetime(df['dt'])

        fig, ax1 = plt.subplots(figsize=(14, 6))

        ax1.fill_between(df['dt'], df['daily_revenue'], alpha=0.3, color='#2196F3')
        ax1.plot(df['dt'], df['daily_revenue'], color='#2196F3', linewidth=1.5, label='Daily Revenue')
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Daily Revenue ($)', color='#2196F3', fontsize=12)
        ax1.tick_params(axis='y', labelcolor='#2196F3')

        ax2 = ax1.twinx()
        ax2.plot(df['dt'], df['order_count'], color='#FF5722', linewidth=1, alpha=0.7, label='Order Count')
        ax2.set_ylabel('Order Count', color='#FF5722', fontsize=12)
        ax2.tick_params(axis='y', labelcolor='#FF5722')

        plt.title('Daily Revenue & Order Count', fontsize=16, fontweight='bold')
        fig.tight_layout()

        filepath = self.output_dir / '05_daily_orders_timeseries.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"每日订单图已保存: {filepath}")
        return filepath

    def chart_country_heatmap_data(self):
        """国家月度销售额热力图"""
        logger.info("生成国家月度热力图...")

        sql = """
        SELECT country,
               DATE_FORMAT(invoice_date, '%Y-%m') as month,
               ROUND(SUM(total_amount), 2) as total_revenue
        FROM fact_sales
        GROUP BY country, DATE_FORMAT(invoice_date, '%Y-%m')
        HAVING total_revenue > 10000
        ORDER BY country, month
        """
        df = self.query(sql)

        pivot = df.pivot_table(index='country', columns='month', values='total_revenue', fill_value=0)

        fig, ax = plt.subplots(figsize=(16, 10))
        im = ax.imshow(pivot.values, cmap='YlOrRd', aspect='auto')

        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=45, ha='right', fontsize=9)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index, fontsize=10)

        plt.colorbar(im, ax=ax, label='Revenue ($)')
        plt.title('Country x Month Revenue Heatmap', fontsize=16, fontweight='bold')
        fig.tight_layout()

        filepath = self.output_dir / '06_country_month_heatmap.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"热力图已保存: {filepath}")
        return filepath

    def generate_all_charts(self):
        """生成所有图表"""
        logger.info("=" * 60)
        logger.info("开始生成可视化图表")
        logger.info("=" * 60)

        charts = [
            self.chart_monthly_revenue,
            self.chart_top_countries,
            self.chart_top_products,
            self.chart_customer_segments,
            self.chart_daily_orders,
            self.chart_country_heatmap_data,
        ]

        for chart_func in charts:
            try:
                chart_func()
            except Exception as e:
                logger.error(f"图表生成失败 {chart_func.__name__}: {e}")

        logger.info("=" * 60)
        logger.info(f"所有图表已保存到: {self.output_dir}")
        logger.info("=" * 60)

        return self.output_dir


if __name__ == "__main__":
    viz = DataVisualizer()
    output = viz.generate_all_charts()
    print(f"\n图表已保存到: {output}")