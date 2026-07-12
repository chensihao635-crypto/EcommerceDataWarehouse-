# ============================================================
# 电商用户订单数据仓库分析平台 - 数据加载模块 (MySQL)
# ============================================================

import pandas as pd
from pathlib import Path
from loguru import logger
import yaml
from sqlalchemy import create_engine, text
from datetime import datetime


class DataLoader:
    """数据加载类 - 负责将数据写入MySQL数据库"""
    
    def __init__(self, config_path=None):
        """
        初始化数据加载器
        
        Args:
            config_path: 配置文件路径，默认为config/config.yaml
        """
        # 获取项目根目录
        self.project_root = Path(__file__).parent.parent
        
        # 加载配置
        if config_path is None:
            config_path = self.project_root / "config" / "config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 数据库连接
        self.engine = None
        
        logger.info("数据加载器初始化完成")
    
    def get_connection(self):
        """
        获取数据库连接
        
        Returns:
            SQLAlchemy Engine: 数据库引擎
        """
        db_config = self.config['database']
        
        # 构建MySQL连接字符串
        connection_string = (
            f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['name']}"
            f"?charset=utf8mb4"
        )
        
        try:
            self.engine = create_engine(connection_string, pool_recycle=3600)
            logger.info("数据库连接成功")
            return self.engine
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def test_connection(self):
        """
        测试数据库连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            engine = self.get_connection()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("数据库连接测试成功")
                return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def create_database(self):
        """
        创建数据库
        """
        db_config = self.config['database']
        
        # 先连接MySQL服务器（不指定数据库）
        connection_string = (
            f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}"
            f"?charset=utf8mb4"
        )
        
        try:
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_config['name']} "
                                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()
            logger.info(f"数据库 {db_config['name']} 创建成功")
        except Exception as e:
            logger.error(f"创建数据库失败: {e}")
            raise
    
    def create_tables(self):
        """
        创建数据仓库表结构（ODS, DWD, DWS层）
        """
        logger.info("=" * 60)
        logger.info("创建数据仓库表结构")
        logger.info("=" * 60)
        
        # 读取SQL文件
        sql_file = self.project_root / "warehouse" / "mysql_create_tables.sql"
        
        if not sql_file.exists():
            logger.warning(f"SQL文件不存在: {sql_file}")
            logger.info("使用默认表结构创建...")
            self._create_default_tables()
            return
        
        try:
            # 先创建数据库
            self.create_database()
            
            # 连接到目标数据库
            engine = self.get_connection()
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 移除CREATE DATABASE和USE语句（已执行）
            lines = sql_content.split('\n')
            filtered_lines = []
            skip = False
            for line in lines:
                if 'CREATE DATABASE' in line.upper():
                    skip = True
                elif 'USE ' in line.upper() and 'ecommerce_dw' in line.upper():
                    skip = False
                    continue
                elif not skip:
                    filtered_lines.append(line)
            
            sql_content = '\n'.join(filtered_lines)
            
            with engine.connect() as conn:
                # 分割并执行每个SQL语句
                statements = sql_content.split(';')
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt and not stmt.startswith('--'):
                        try:
                            conn.execute(text(stmt))
                        except Exception as e:
                            logger.warning(f"执行SQL语句时出错: {e}")
                conn.commit()
            
            logger.info("数据仓库表结构创建成功")
            
        except Exception as e:
            logger.error(f"创建表结构失败: {e}")
            logger.info("使用默认表结构创建...")
            self._create_default_tables()
    
    def _create_default_tables(self):
        """
        创建默认表结构（MySQL语法）
        """
        create_tables_sql = """
        -- ODS层：原始数据层
        CREATE TABLE IF NOT EXISTS ods_retail_raw (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            invoiceno VARCHAR(50),
            stockcode VARCHAR(50),
            description TEXT,
            quantity INT,
            invoicedate DATETIME,
            unitprice DECIMAL(10, 2),
            customerid DECIMAL(10, 0),
            country VARCHAR(100),
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        
        -- DWD层：数据明细层
        CREATE TABLE IF NOT EXISTS dwd_order_detail (
            order_detail_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            invoice_no VARCHAR(50),
            stock_code VARCHAR(50),
            description TEXT,
            quantity INT,
            invoice_date DATETIME,
            unit_price DECIMAL(10, 2),
            total_amount DECIMAL(12, 2),
            customer_id DECIMAL(10, 0),
            country VARCHAR(100),
            year INT,
            month INT,
            day INT,
            weekday VARCHAR(10),
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        
        -- 用户维度表
        CREATE TABLE IF NOT EXISTS dim_users (
            user_sk BIGINT AUTO_INCREMENT PRIMARY KEY,
            customer_id DECIMAL(10, 0),
            country VARCHAR(100),
            first_purchase_date DATETIME,
            last_purchase_date DATETIME,
            total_orders INT,
            total_amount DECIMAL(12, 2),
            is_active BOOLEAN DEFAULT TRUE,
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        
        -- 商品维度表
        CREATE TABLE IF NOT EXISTS dim_products (
            product_sk BIGINT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(50),
            description TEXT,
            first_sale_date DATETIME,
            last_sale_date DATETIME,
            total_quantity INT,
            total_revenue DECIMAL(12, 2),
            avg_unit_price DECIMAL(10, 2),
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        
        -- 日期维度表
        CREATE TABLE IF NOT EXISTS dim_date (
            date_sk INT PRIMARY KEY,
            full_date DATE,
            year INT,
            quarter INT,
            month INT,
            day INT,
            weekday VARCHAR(10),
            is_weekend BOOLEAN
        ) ENGINE=InnoDB;
        
        -- 发票维度表
        CREATE TABLE IF NOT EXISTS dim_invoice (
            invoice_sk BIGINT AUTO_INCREMENT PRIMARY KEY,
            invoice_no VARCHAR(50),
            customer_id DECIMAL(10, 0),
            invoice_date DATETIME,
            country VARCHAR(100),
            total_amount DECIMAL(12, 2),
            item_count INT,
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        
        -- 销售事实表
        CREATE TABLE IF NOT EXISTS fact_sales (
            sales_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            order_detail_id BIGINT,
            invoice_no VARCHAR(50),
            stock_code VARCHAR(50),
            description TEXT,
            quantity INT,
            unit_price DECIMAL(10, 2),
            total_amount DECIMAL(12, 2),
            customer_id DECIMAL(10, 0),
            country VARCHAR(100),
            invoice_date DATETIME,
            year INT,
            month INT,
            day INT,
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """
        
        try:
            engine = self.get_connection()
            with engine.connect() as conn:
                conn.execute(text(create_tables_sql))
                conn.commit()
            logger.info("默认表结构创建成功")
        except Exception as e:
            logger.error(f"创建默认表结构失败: {e}")
            raise
    
    def load_ods(self, df):
        """
        加载数据到ODS层
        
        Args:
            df: 原始数据DataFrame
        """
        logger.info("加载数据到ODS层...")
        
        try:
            engine = self.get_connection()
            
            # 重命名列以匹配数据库字段（小写）
            df_load = df.copy()
            df_load.columns = [col.lower().replace(' ', '_') for col in df_load.columns]
            
            # 写入数据库
            df_load.to_sql(
                'ods_retail_raw',
                engine,
                if_exists='append',
                index=False,
                chunksize=1000
            )
            
            logger.info(f"ODS层数据加载成功: {len(df_load):,} 行")
            
        except Exception as e:
            logger.error(f"ODS层数据加载失败: {e}")
            raise
    
    def load_dwd(self, df):
        """
        加载数据到DWD层
        
        Args:
            df: 清洗后的数据DataFrame
        """
        logger.info("加载数据到DWD层...")
        
        try:
            engine = self.get_connection()
            
            # 准备DWD层数据
            df_dwd = df.copy()
            
            # 确保列名匹配
            column_mapping = {
                'InvoiceNo': 'invoice_no',
                'StockCode': 'stock_code',
                'Description': 'description',
                'Quantity': 'quantity',
                'InvoiceDate': 'invoice_date',
                'UnitPrice': 'unit_price',
                'TotalAmount': 'total_amount',
                'CustomerID': 'customer_id',
                'Country': 'country',
                'Year': 'year',
                'Month': 'month',
                'Day': 'day',
                'Weekday': 'weekday'
            }
            
            # 选择存在的列
            existing_cols = [col for col in column_mapping.keys() if col in df_dwd.columns]
            df_dwd = df_dwd[existing_cols].copy()
            df_dwd.columns = [column_mapping[col] for col in existing_cols]
            
            # 写入数据库
            df_dwd.to_sql(
                'dwd_order_detail',
                engine,
                if_exists='append',
                index=False,
                chunksize=1000
            )
            
            logger.info(f"DWD层数据加载成功: {len(df_dwd):,} 行")
            
        except Exception as e:
            logger.error(f"DWD层数据加载失败: {e}")
            raise
    
    def load_dim_users(self, df):
        """
        加载用户维度表
        
        Args:
            df: DWD层数据DataFrame
        """
        logger.info("加载用户维度表...")
        
        try:
            engine = self.get_connection()
            
            # 构建用户维度表
            dim_users = df.groupby('CustomerID').agg({
                'Country': 'first',
                'InvoiceDate': ['min', 'max'],
                'InvoiceNo': 'nunique',
                'TotalAmount': 'sum'
            }).reset_index()
            
            dim_users.columns = ['customer_id', 'country', 'first_purchase_date', 
                                'last_purchase_date', 'total_orders', 'total_amount']
            dim_users['is_active'] = True
            
            # 写入数据库
            dim_users.to_sql(
                'dim_users',
                engine,
                if_exists='append',
                index=False,
                chunksize=1000
            )
            
            logger.info(f"用户维度表加载成功: {len(dim_users):,} 行")
            
        except Exception as e:
            logger.error(f"用户维度表加载失败: {e}")
            raise
    
    def load_dim_products(self, df):
        """
        加载商品维度表
        
        Args:
            df: DWD层数据DataFrame
        """
        logger.info("加载商品维度表...")
        
        try:
            engine = self.get_connection()
            
            # 构建商品维度表
            dim_products = df.groupby('StockCode').agg({
                'Description': 'first',
                'InvoiceDate': ['min', 'max'],
                'Quantity': 'sum',
                'TotalAmount': 'sum',
                'UnitPrice': 'mean'
            }).reset_index()
            
            dim_products.columns = ['stock_code', 'description', 'first_sale_date',
                                   'last_sale_date', 'total_quantity', 'total_revenue',
                                   'avg_unit_price']
            
            # 写入数据库
            dim_products.to_sql(
                'dim_products',
                engine,
                if_exists='append',
                index=False,
                chunksize=1000
            )
            
            logger.info(f"商品维度表加载成功: {len(dim_products):,} 行")
            
        except Exception as e:
            logger.error(f"商品维度表加载失败: {e}")
            raise
    
    def load_dim_date(self, df):
        """
        加载日期维度表
        
        Args:
            df: DWD层数据DataFrame
        """
        logger.info("加载日期维度表...")
        
        try:
            engine = self.get_connection()
            
            # 构建日期维度表
            dates = pd.date_range(start=df['InvoiceDate'].min(), 
                                 end=df['InvoiceDate'].max())
            
            dim_date = pd.DataFrame({
                'date_sk': dates.strftime('%Y%m%d').astype(int),
                'full_date': dates.date,
                'year': dates.year,
                'quarter': dates.quarter,
                'month': dates.month,
                'day': dates.day,
                'weekday': dates.strftime('%A'),
                'is_weekend': dates.weekday >= 5
            })
            
            # 写入数据库
            dim_date.to_sql(
                'dim_date',
                engine,
                if_exists='append',
                index=False,
                chunksize=1000
            )
            
            logger.info(f"日期维度表加载成功: {len(dim_date):,} 行")
            
        except Exception as e:
            logger.error(f"日期维度表加载失败: {e}")
            raise
    
    def load_dim_invoice(self, df):
        """
        加载发票维度表
        
        Args:
            df: DWD层数据DataFrame
        """
        logger.info("加载发票维度表...")
        
        try:
            engine = self.get_connection()
            
            # 构建发票维度表
            dim_invoice = df.groupby('InvoiceNo').agg({
                'CustomerID': 'first',
                'InvoiceDate': 'first',
                'Country': 'first',
                'TotalAmount': 'sum',
                'StockCode': 'count'
            }).reset_index()
            
            dim_invoice.columns = ['invoice_no', 'customer_id', 'invoice_date',
                                  'country', 'total_amount', 'item_count']
            
            # 写入数据库
            dim_invoice.to_sql(
                'dim_invoice',
                engine,
                if_exists='append',
                index=False,
                chunksize=1000
            )
            
            logger.info(f"发票维度表加载成功: {len(dim_invoice):,} 行")
            
        except Exception as e:
            logger.error(f"发票维度表加载失败: {e}")
            raise
    
    def load_fact_sales(self, df):
        """
        加载销售事实表
        
        Args:
            df: DWD层数据DataFrame
        """
        logger.info("加载销售事实表...")
        
        try:
            engine = self.get_connection()
            
            # 准备事实表数据
            fact_sales = df[['InvoiceNo', 'StockCode', 'Description', 'Quantity',
                            'UnitPrice', 'TotalAmount', 'CustomerID', 'Country',
                            'InvoiceDate', 'Year', 'Month', 'Day']].copy()
            
            fact_sales.columns = ['invoice_no', 'stock_code', 'description', 'quantity',
                                 'unit_price', 'total_amount', 'customer_id', 'country',
                                 'invoice_date', 'year', 'month', 'day']
            
            # 写入数据库
            fact_sales.to_sql(
                'fact_sales',
                engine,
                if_exists='append',
                index=False,
                chunksize=1000
            )
            
            logger.info(f"销售事实表加载成功: {len(fact_sales):,} 行")
            
        except Exception as e:
            logger.error(f"销售事实表加载失败: {e}")
            raise
    
    def load_all_from_csv(self):
        """
        从CSV文件加载所有数据到数据库
        """
        logger.info("从CSV文件加载所有数据...")
        
        # 加载DWD层数据
        dwd_file = self.project_root / "data" / "dwd" / "dwd_order_detail.csv"
        if dwd_file.exists():
            df_dwd = pd.read_csv(dwd_file)
            
            # 转换日期列
            if 'InvoiceDate' in df_dwd.columns:
                df_dwd['InvoiceDate'] = pd.to_datetime(df_dwd['InvoiceDate'])
            
            # 加载各层数据
            self.load_dwd(df_dwd)
            self.load_dim_users(df_dwd)
            self.load_dim_products(df_dwd)
            self.load_dim_date(df_dwd)
            self.load_dim_invoice(df_dwd)
            self.load_fact_sales(df_dwd)
            
            logger.info("所有数据加载完成")
        else:
            logger.error(f"DWD数据文件不存在: {dwd_file}")
    
    def get_table_stats(self):
        """
        获取各表数据统计
        """
        logger.info("=" * 60)
        logger.info("数据仓库统计信息")
        logger.info("=" * 60)
        
        tables = ['ods_retail_raw', 'dwd_order_detail', 'dim_users', 
                  'dim_products', 'dim_date', 'dim_invoice', 'fact_sales']
        
        try:
            engine = self.get_connection()
            with engine.connect() as conn:
                for table in tables:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        logger.info(f"{table}: {count:,} 行")
                    except Exception as e:
                        logger.warning(f"表 {table} 不存在或查询失败")
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")


if __name__ == "__main__":
    # 测试数据加载
    loader = DataLoader()
    
    # 测试连接
    if loader.test_connection():
        # 创建表结构
        loader.create_tables()
        
        # 从CSV加载数据
        loader.load_all_from_csv()
        
        # 获取统计信息
        loader.get_table_stats()
    else:
        logger.error("无法连接到数据库，请检查配置")