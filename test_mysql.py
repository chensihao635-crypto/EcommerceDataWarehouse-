# -*- coding: utf-8 -*-
# ============================================================
# MySQL连接测试脚本
# ============================================================
import sys
import io
from pathlib import Path

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from etl.load import DataLoader

print("=" * 60)
print("MySQL连接测试")
print("=" * 60)

# 初始化加载器
loader = DataLoader()

# 第一步：创建数据库（不指定数据库名连接）
print("\n[1/4] 正在创建数据库...")
loader.create_database()
print("[OK] 数据库创建完成")

# 第二步：创建表结构
print("\n[2/4] 正在创建数据仓库表结构...")
loader.create_tables()
print("[OK] 表结构创建完成")

# 第三步：测试连接
print("\n[3/4] 测试数据库连接...")
if loader.test_connection():
    print("[OK] 数据库连接成功")
else:
    print("[ERROR] MySQL连接失败，请检查配置")
    sys.exit(1)

# 第四步：加载数据
print("\n[4/4] 正在加载数据...")
loader.load_all_from_csv()
print("[OK] 数据加载完成")

# 获取统计信息
loader.get_table_stats()

print("\n" + "=" * 60)
print("所有任务完成!")
print("=" * 60)
