# ============================================================
# 电商用户订单数据仓库分析平台 - 主程序入口
# ============================================================

import sys
from pathlib import Path
from loguru import logger

# 设置项目根目录
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_etl_pipeline():
    """
    运行完整的ETL流程
    """
    from etl.extract import DataExtractor
    from etl.transform import DataTransformer
    from etl.load import DataLoader
    
    logger.info("=" * 60)
    logger.info("开始运行ETL流程")
    logger.info("=" * 60)
    
    try:
        # 1. Extract - 数据抽取
        logger.info("步骤1: 数据抽取")
        extractor = DataExtractor()
        df_raw = extractor.extract_ods()
        
        # 2. Transform - 数据转换
        logger.info("步骤2: 数据转换")
        transformer = DataTransformer()
        result = transformer.transform(df_raw)
        
        # result是一个dict，包含fact_sales, dim_users, dim_products, dim_date, dim_invoice, dwd_data
        df_clean = result['dwd_data']
        
        # 3. Load - 数据加载
        logger.info("步骤3: 数据加载")
        loader = DataLoader()
        
        # 尝试连接数据库，如果失败则跳过
        if loader.test_connection():
            loader.create_tables()
            loader.load_ods(df_raw)
            loader.load_dwd(df_clean)
            loader.build_all_dws_ads()
            loader.get_table_stats()
        else:
            logger.warning("数据库连接失败，数据已保存到CSV文件")
        
        # 打印构建结果摘要
        logger.info("=" * 60)
        logger.info("数据仓库表构建摘要:")
        logger.info(f"  用户维度表 (dim_users): {len(result['dim_users']):,} 行")
        logger.info(f"  商品维度表 (dim_products): {len(result['dim_products']):,} 行")
        logger.info(f"  日期维度表 (dim_date): {len(result['dim_date']):,} 行")
        logger.info(f"  订单维度表 (dim_invoice): {len(result['dim_invoice']):,} 行")
        logger.info(f"  销售事实表 (fact_sales): {len(result['fact_sales']):,} 行")
        logger.info(f"  DWD明细数据: {len(df_clean):,} 行")
        logger.info("=" * 60)
        
        logger.info("=" * 60)
        logger.info("ETL流程完成!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"ETL流程失败: {e}")
        return False


def run_visualization():
    """运行数据可视化"""
    from visualization.charts import DataVisualizer
    viz = DataVisualizer()
    viz.generate_all_charts()


def main():
    logger.info("=" * 60)
    logger.info("电商用户订单数据仓库分析平台")
    logger.info("=" * 60)
    
    # 运行ETL流程
    etl_success = run_etl_pipeline()
    
    # 运行数据可视化
    if etl_success:
        run_visualization()
    
    logger.info("程序执行完成!")


if __name__ == "__main__":
    main()