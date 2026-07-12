# ============================================================
# 电商用户订单数据仓库分析平台 - 数据转换模块
# ============================================================

import pandas as pd
from datetime import datetime
from pathlib import Path
from loguru import logger
import yaml


class DataTransformer:
    """数据转换类 - 负责清洗和转换原始数据"""
    
    def __init__(self, config_path=None):
        """
        初始化数据转换器
        
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
        
        # 设置日志
        log_file = self.project_root / self.config['etl']['log_file']
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(str(log_file), rotation="10 MB", level=self.config['etl']['log_level'])
        
        logger.info("数据转换器初始化完成")
    
    def transform(self, df):
        """
        执行数据转换和清洗
        
        Args:
            df: 原始数据DataFrame
            
        Returns:
            pandas.DataFrame: 清洗后的数据
        """
        logger.info("=" * 60)
        logger.info("开始数据转换任务")
        logger.info("=" * 60)
        
        # 记录原始数据量
        original_count = len(df)
        logger.info(f"原始数据行数: {original_count:,}")
        
        # 复制数据避免修改原始数据
        df_clean = df.copy()
        
        # 1. 删除缺失用户
        df_clean, count1 = self._remove_missing_customer(df_clean)
        
        # 2. 删除取消订单
        df_clean, count2 = self._remove_cancelled_orders(df_clean)
        
        # 3. 删除异常商品
        df_clean, count3 = self._remove_abnormal_products(df_clean)
        
        # 4. 时间转换
        df_clean = self._convert_datetime(df_clean)
        
        # 5. 新增字段
        df_clean = self._add_total_amount(df_clean)
        
        # 6. 数据质量检查
        self._data_quality_check(original_count, df_clean, count1, count2, count3)
        
        # 保存转换后的数据到DWD层
        self._save_dwd_data(df_clean)
        
        # 7. 构建维度表和事实表
        logger.info("构建维度表和事实表...")
        dim_users = self._build_dim_users(df_clean)
        dim_products = self._build_dim_products(df_clean)
        dim_date = self._build_dim_date(df_clean)
        dim_invoice = self._build_dim_invoice(df_clean)
        fact_sales = self._build_fact_sales(df_clean)
        
        # 保存维度表和事实表到CSV
        dws_dir = self.project_root / "data" / "dws"
        dws_dir.mkdir(parents=True, exist_ok=True)
        
        dim_users.to_csv(dws_dir / "dim_users.csv", index=False, encoding='utf-8')
        dim_products.to_csv(dws_dir / "dim_products.csv", index=False, encoding='utf-8')
        dim_date.to_csv(dws_dir / "dim_date.csv", index=False, encoding='utf-8')
        dim_invoice.to_csv(dws_dir / "dim_invoice.csv", index=False, encoding='utf-8')
        fact_sales.to_csv(dws_dir / "fact_sales.csv", index=False, encoding='utf-8')
        
        logger.info(f"维度表和事实表已保存到: {dws_dir}")
        
        return {
            'fact_sales': fact_sales,
            'dim_users': dim_users,
            'dim_products': dim_products,
            'dim_date': dim_date,
            'dim_invoice': dim_invoice,
            'dwd_data': df_clean
        }
    
    def _remove_missing_customer(self, df):
        """
        删除缺失用户的数据
        
        Args:
            df: 数据DataFrame
            
        Returns:
            tuple: (清洗后的DataFrame, 删除的行数)
        """
        logger.info("步骤1: 删除缺失用户的数据...")
        
        before_count = len(df)
        
        # 检查CustomerID列是否存在
        if 'CustomerID' in df.columns:
            # 删除CustomerID为空的行
            df_clean = df.dropna(subset=['CustomerID']).copy()
            # 将CustomerID转换为整数
            df_clean.loc[:, 'CustomerID'] = df_clean['CustomerID'].astype(int)
        else:
            logger.warning("数据中不存在CustomerID列")
            df_clean = df
        
        after_count = len(df_clean)
        removed_count = before_count - after_count
        
        logger.info(f"  删除缺失用户数据: {removed_count:,} 行")
        logger.info(f"  剩余数据: {after_count:,} 行")
        
        return df_clean, removed_count
    
    def _remove_cancelled_orders(self, df):
        """
        删除取消订单（InvoiceNo以C开头的数据）
        
        Args:
            df: 数据DataFrame
            
        Returns:
            tuple: (清洗后的DataFrame, 删除的行数)
        """
        logger.info("步骤2: 删除取消订单...")
        
        before_count = len(df)
        
        # 检查InvoiceNo列是否存在
        if 'InvoiceNo' in df.columns:
            # 将InvoiceNo转换为字符串
            df['InvoiceNo'] = df['InvoiceNo'].astype(str)
            
            # 删除InvoiceNo以'C'开头的行（取消订单）
            df_clean = df[~df['InvoiceNo'].str.startswith('C')]
        else:
            logger.warning("数据中不存在InvoiceNo列")
            df_clean = df
        
        after_count = len(df_clean)
        removed_count = before_count - after_count
        
        logger.info(f"  删除取消订单: {removed_count:,} 行")
        logger.info(f"  剩余数据: {after_count:,} 行")
        
        return df_clean, removed_count
    
    def _remove_abnormal_products(self, df):
        """
        删除异常商品（Quantity <= 0, UnitPrice <= 0）
        
        Args:
            df: 数据DataFrame
            
        Returns:
            tuple: (清洗后的DataFrame, 删除的行数)
        """
        logger.info("步骤3: 删除异常商品...")
        
        before_count = len(df)
        
        # 检查必要列是否存在
        if 'Quantity' in df.columns and 'UnitPrice' in df.columns:
            # 删除Quantity <= 0的行
            df_clean = df[df['Quantity'] > 0]
            
            # 删除UnitPrice <= 0的行
            df_clean = df_clean[df_clean['UnitPrice'] > 0]
        else:
            logger.warning("数据中不存在Quantity或UnitPrice列")
            df_clean = df
        
        after_count = len(df_clean)
        removed_count = before_count - after_count
        
        logger.info(f"  删除异常商品: {removed_count:,} 行")
        logger.info(f"  剩余数据: {after_count:,} 行")
        
        return df_clean, removed_count
    
    def _convert_datetime(self, df):
        """
        转换时间字段
        
        Args:
            df: 数据DataFrame
            
        Returns:
            pandas.DataFrame: 转换后的数据
        """
        logger.info("步骤4: 转换时间字段...")
        
        if 'InvoiceDate' in df.columns:
            # 转换为datetime类型
            df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], errors='coerce')
            
            # 提取日期部分
            df['InvoiceDateOnly'] = df['InvoiceDate'].dt.date
            
            # 提取年月日小时等信息
            df['Year'] = df['InvoiceDate'].dt.year
            df['Month'] = df['InvoiceDate'].dt.month
            df['Day'] = df['InvoiceDate'].dt.day
            df['Hour'] = df['InvoiceDate'].dt.hour
            df['DayOfWeek'] = df['InvoiceDate'].dt.dayofweek  # 0=Monday, 6=Sunday
            
            logger.info("  时间字段转换完成")
            logger.info(f"  时间范围: {df['InvoiceDate'].min()} 至 {df['InvoiceDate'].max()}")
        else:
            logger.warning("数据中不存在InvoiceDate列")
        
        return df
    
    def _add_total_amount(self, df):
        """
        新增总金额字段
        
        Args:
            df: 数据DataFrame
            
        Returns:
            pandas.DataFrame: 添加字段后的数据
        """
        logger.info("步骤5: 新增总金额字段...")
        
        if 'Quantity' in df.columns and 'UnitPrice' in df.columns:
            # 计算总金额 = 数量 * 单价
            df['TotalAmount'] = df['Quantity'] * df['UnitPrice']
            
            # 保留两位小数
            df['TotalAmount'] = df['TotalAmount'].round(2)
            
            logger.info("  总金额字段计算完成")
            logger.info(f"  总金额范围: {df['TotalAmount'].min():.2f} 至 {df['TotalAmount'].max():.2f}")
            logger.info(f"  总销售额: {df['TotalAmount'].sum():,.2f}")
        else:
            logger.warning("数据中不存在Quantity或UnitPrice列")
        
        return df
    
    def _data_quality_check(self, original_count, df_clean, count1, count2, count3):
        """
        数据质量检查
        
        Args:
            original_count: 原始数据行数
            df_clean: 清洗后的数据
            count1: 删除的缺失用户数据行数
            count2: 删除的取消订单行数
            count3: 删除的异常商品行数
        """
        logger.info("=" * 60)
        logger.info("数据质量检查报告:")
        logger.info("=" * 60)
        
        final_count = len(df_clean)
        total_removed = original_count - final_count
        
        logger.info(f"原始数据行数: {original_count:,}")
        logger.info(f"删除缺失用户数据: {count1:,} 行 ({count1/original_count*100:.2f}%)")
        logger.info(f"删除取消订单: {count2:,} 行 ({count2/original_count*100:.2f}%)")
        logger.info(f"删除异常商品: {count3:,} 行 ({count3/original_count*100:.2f}%)")
        logger.info(f"总删除行数: {total_removed:,} 行 ({total_removed/original_count*100:.2f}%)")
        logger.info(f"最终数据行数: {final_count:,} 行 ({final_count/original_count*100:.2f}%)")
        logger.info("=" * 60)
        
        # 检查数据完整性
        if final_count == 0:
            logger.error("警告: 清洗后数据为空！请检查数据源。")
        elif final_count < original_count * 0.5:
            logger.warning(f"警告: 清洗后数据量不足原始数据的50%！")
    
    def _save_dwd_data(self, df):
        """
        保存DWD层数据
        
        Args:
            df: 清洗后的数据
        """
        logger.info("保存DWD层数据...")
        
        # 创建DWD目录
        output_dir = self.project_root / "data" / "dwd"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 选择需要的列（DWD层标准字段）
        dwd_columns = [
            'InvoiceNo', 'StockCode', 'Description', 'Quantity',
            'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country',
            'TotalAmount', 'InvoiceDateOnly', 'Year', 'Month', 'Day',
            'Hour', 'DayOfWeek'
        ]
        
        # 只选择存在的列
        available_columns = [col for col in dwd_columns if col in df.columns]
        df_dwd = df[available_columns]
        
        # 保存为CSV
        output_file = output_dir / "dwd_order_detail.csv"
        df_dwd.to_csv(output_file, index=False, encoding='utf-8')
        
        logger.info(f"DWD层数据已保存: {output_file}")
        logger.info(f"DWD层数据行数: {len(df_dwd):,}")
        logger.info(f"DWD层数据列数: {len(df_dwd.columns)}")

    def _build_dim_users(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        构建用户维度表 dim_users
        
        Args:
            df: 清洗后的数据
            
        Returns:
            pandas.DataFrame: 用户维度表
        """
        logger.info("构建用户维度表 dim_users...")
        dim_users = df.groupby('CustomerID').agg(
            country=('Country', 'first'),
            first_order_date=('InvoiceDate', 'min'),
            last_order_date=('InvoiceDate', 'max'),
            total_orders=('InvoiceNo', 'nunique'),
            total_items=('Quantity', 'sum'),
            total_amount=('TotalAmount', 'sum')
        ).reset_index()
        
        dim_users['first_order_date'] = pd.to_datetime(dim_users['first_order_date']).dt.date
        dim_users['last_order_date'] = pd.to_datetime(dim_users['last_order_date']).dt.date
        dim_users['total_amount'] = dim_users['total_amount'].round(2)
        
        # 计算用户生命周期天数
        dim_users['customer_lifetime_days'] = (
            pd.to_datetime(dim_users['last_order_date']) - pd.to_datetime(dim_users['first_order_date'])
        ).dt.days
        
        # 用户等级划分
        def assign_tier(amount):
            if amount >= 5000:
                return 'Gold'
            elif amount >= 1000:
                return 'Silver'
            else:
                return 'Bronze'
        
        dim_users['customer_tier'] = dim_users['total_amount'].apply(assign_tier)
        
        logger.info(f"  用户维度表行数: {len(dim_users):,}")
        return dim_users

    def _build_dim_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        构建商品维度表 dim_products
        
        Args:
            df: 清洗后的数据
            
        Returns:
            pandas.DataFrame: 商品维度表
        """
        logger.info("构建商品维度表 dim_products...")
        dim_products = df.groupby('StockCode').agg(
            description=('Description', 'first'),
            unit_price=('UnitPrice', 'mean'),
            total_quantity_sold=('Quantity', 'sum'),
            total_revenue=('TotalAmount', 'sum'),
            total_orders=('InvoiceNo', 'nunique'),
            total_customers=('CustomerID', 'nunique')
        ).reset_index()
        
        dim_products['unit_price'] = dim_products['unit_price'].round(2)
        dim_products['total_revenue'] = dim_products['total_revenue'].round(2)
        
        # 商品等级划分
        def assign_product_tier(revenue):
            if revenue >= 10000:
                return 'A'
            elif revenue >= 1000:
                return 'B'
            else:
                return 'C'
        
        dim_products['product_tier'] = dim_products['total_revenue'].apply(assign_product_tier)
        
        logger.info(f"  商品维度表行数: {len(dim_products):,}")
        return dim_products

    def _build_dim_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        构建日期维度表 dim_date
        
        Args:
            df: 清洗后的数据
            
        Returns:
            pandas.DataFrame: 日期维度表
        """
        logger.info("构建日期维度表 dim_date...")
        
        # 从数据中提取唯一日期
        dates = df['InvoiceDate'].dt.date.unique()
        
        dim_date_records = []
        for d in sorted(dates):
            dt = pd.Timestamp(d)
            dim_date_records.append({
                'date_key': int(dt.strftime('%Y%m%d')),
                'full_date': d,
                'year': dt.year,
                'month': dt.month,
                'day': dt.day,
                'day_of_week': dt.dayofweek,
                'day_name': dt.day_name(),
                'month_name': dt.month_name(),
                'quarter': dt.quarter,
                'is_weekend': 1 if dt.dayofweek >= 5 else 0,
                'week_of_year': dt.isocalendar()[1]
            })
        
        dim_date = pd.DataFrame(dim_date_records)
        
        logger.info(f"  日期维度表行数: {len(dim_date):,}")
        return dim_date

    def _build_dim_invoice(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        构建订单维度表 dim_invoice
        
        Args:
            df: 清洗后的数据
            
        Returns:
            pandas.DataFrame: 订单维度表
        """
        logger.info("构建订单维度表 dim_invoice...")
        dim_invoice = df.groupby('InvoiceNo').agg(
            customer_id=('CustomerID', 'first'),
            invoice_date=('InvoiceDate', 'first'),
            country=('Country', 'first'),
            item_count=('StockCode', 'nunique'),
            total_quantity=('Quantity', 'sum'),
            total_amount=('TotalAmount', 'sum')
        ).reset_index()
        
        dim_invoice['invoice_date_only'] = pd.to_datetime(dim_invoice['invoice_date']).dt.date
        dim_invoice['total_amount'] = dim_invoice['total_amount'].round(2)
        
        # 订单金额等级
        def assign_order_tier(amount):
            if amount >= 500:
                return 'Large'
            elif amount >= 100:
                return 'Medium'
            else:
                return 'Small'
        
        dim_invoice['order_tier'] = dim_invoice['total_amount'].apply(assign_order_tier)
        
        logger.info(f"  订单维度表行数: {len(dim_invoice):,}")
        return dim_invoice

    def _build_fact_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        构建销售事实表 fact_sales
        
        Args:
            df: 清洗后的数据
            
        Returns:
            pandas.DataFrame: 销售事实表
        """
        logger.info("构建销售事实表 fact_sales...")
        
        # 创建date_key
        df_fact = df.copy()
        df_fact['date_key'] = pd.to_datetime(df_fact['InvoiceDate']).dt.strftime('%Y%m%d').astype(int)
        
        fact_sales = df_fact[[
            'InvoiceNo', 'CustomerID', 'StockCode', 'date_key',
            'Quantity', 'UnitPrice', 'TotalAmount', 'Country'
        ]].copy()
        
        fact_sales.rename(columns={
            'InvoiceNo': 'invoice_no',
            'CustomerID': 'customer_id',
            'StockCode': 'stock_code',
            'Quantity': 'quantity',
            'UnitPrice': 'unit_price',
            'TotalAmount': 'total_amount',
            'Country': 'country'
        }, inplace=True)
        
        logger.info(f"  销售事实表行数: {len(fact_sales):,}")
        return fact_sales


if __name__ == "__main__":
    # 测试数据转换
    import sys
    sys.path.append(str(Path(__file__).parent))
    from extract import DataExtractor
    
    # 先执行抽取
    extractor = DataExtractor()
    df_raw = extractor.extract()
    
    # 然后执行转换
    transformer = DataTransformer()
    df_clean = transformer.transform(df_raw)
    
    print(f"\n转换完成! 清洗后数据形状: {df_clean.shape}")