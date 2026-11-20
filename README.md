# 电商用户订单数据仓库分析平台 (EcommerceDataWarehouse)

## AI 自然语言查数

已接入本机 MySQL 的独立只读账号，支持查询计划校验、参数化 SQL、指标口径与结果追溯。运行 `powershell -File ./run_ai.ps1 "2011年11月销售额最高的五个国家是哪些？"`。本地模型与评测说明见 [AI_README.md](AI_README.md)。模型未就绪时仍可运行 `python ai_assistant.py --plan demo_plan.json` 验证数据库查询。

基于 UCI Online Retail 真实电商交易数据，设计并实现端到端数据仓库分析平台。使用 Python 完成 ETL 流程，构建星型模型维度建模，数据存储于 MySQL，并通过 SQL 和 Python 完成多维度业务分析与可视化。

## 技术栈

- **编程语言**: Python 3.9+
- **数据处理**: Pandas, SQLAlchemy, PyMySQL
- **数据库**: MySQL 8.0
- **数据可视化**: Matplotlib, Seaborn
- **构建工具**: setuptools

## 项目结构

```
EcommerceDataWarehouse/
├── config/
│   └── config.yaml               # 数据库连接 & ETL 配置
├── etl/
│   ├── __init__.py
│   ├── extract.py                # 数据抽取（从 Excel）
│   ├── transform.py              # 数据转换（清洗+维度建模）
│   └── load.py                   # 数据加载（写入 MySQL）
├── warehouse/
│   └── mysql_create_tables.sql   # MySQL 建表 SQL
├── sql/
│   └── analysis.sql              # SQL 分析查询（13 题）
├── analysis/
│   └── analysis.py               # Python 数据分析
├── visualization/
│   └── charts.py                 # 可视化图表生成（6 张图）
├── output/
│   ├── analysis/                 # 分析结果 JSON
│   └── charts/                   # 可视化图表 PNG
├── data/                         # 数据目录（ODS/DWD/DWS CSV）
├── main.py                       # 主程序入口
├── test_mysql.py                 # MySQL 连接 & 加载测试
├── requirements.txt
└── README.md
```

## 数据仓库架构

### 分层模型

```
ODS（原始层）→ DWD（明细层）→ DWS（汇总层）→ ADS（应用层）
```

| 层级   | 说明               | 表名                                                           |
| ------ | ------------------ | -------------------------------------------------------------- |
| ODS 层 | 原始数据存储       | ods_retail                                                     |
| DWD 层 | 清洗后订单明细     | dwd_order_detail                                               |
| DWS 层 | 用户/商品/地区汇总 | dws_customer_summary, dws_product_summary, dws_country_summary |
| ADS 层 | 业务指标聚合       | ads_sales_dashboard                                            |

### 维度建模（星型模型）

- **dim_users** - 用户维度（RFM 分层、用户等级）
- **dim_products** - 商品维度（商品等级、销售统计）
- **dim_date** - 日期维度（年/月/日/周/季度）
- **dim_invoice** - 订单维度（订单金额等级）
- **fact_sales** - 销售事实表（关联维度外键）

### 数据量

| 表名             | 数据量      |
| ---------------- | ----------- |
| dwd_order_detail | ~397,884 行 |
| fact_sales       | ~397,884 行 |
| dim_users        | ~4,338 行   |
| dim_products     | ~3,665 行   |
| dim_date         | ~374 行     |
| dim_invoice      | ~18,532 行  |

## 快速开始

### 前置条件

- Python 3.9+
- MySQL 8.0+

### 安装与运行

```bash
# 1. 克隆项目
git clone https://github.com/your-username/EcommerceDataWarehouse.git
cd EcommerceDataWarehouse

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # Linux/Mac

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置数据库
# 编辑 config/config.yaml，填写 MySQL 连接信息

# 5. 测试连接并加载数据
python test_mysql.py

# 6. 运行 ETL + 可视化
python main.py
```

### 运行分析

```bash
# SQL 分析
python -m analysis.analysis

# 可视化图表
python -m visualization.charts
```

## ETL 流程

1. **Extract（抽取）**: 从 `data/online+retail/Online Retail.xlsx` 读取 541,909 行原始数据
2. **Transform（转换）**: 数据清洗（去空值、去异常、退货过滤）+ 维度表生成 + 事实表构建
3. **Load（加载）**: 批量写入 MySQL 6 张表（维度表 + 事实表）

## 分析内容

### SQL 分析（13 题）

1. 基础统计 / 2. 月度趋势 / 3. 商品排名 / 4. RFM 用户分层 / 5. 复购率 / 6. 国家分布 / 7. 价格区间 / 8. 工作日/周末 / 9. 时段分布 / 10. 商品共现 / 11. 退货分析 / 12. ABC 分析 / 13. 留存率

### 可视化图表（6 张）

1. 月度销售额与订单数趋势
2. Top 10 国家销售额占比饼图
3. Top 20 热销商品柱状图
4. 客户 RFM 分层饼图
5. 每日收入与订单量时序图
6. 国家×月份销售额热力图

## 配置说明

编辑 `config/config.yaml`:

```yaml
database:
  host: localhost
  port: 3306
  user: root
  password: "your_password"
  name: ecommerce_dw
```

## 项目亮点

1. **完整数仓分层**: ODS→DWD→DWS→ADS 四层架构
2. **星型模型维度建模**: 4 张维度表 + 1 张事实表
3. **数据清洗**: 删除空值、异常值、退货记录、负单价
4. **ETL 自动化**: 一键完成抽取→转换→加载全流程
5. **多维度分析**: 用户/商品/时间/地区/时段/ABC/RFM/留存
6. **可视化输出**: 6 张分析图表，支持复现
