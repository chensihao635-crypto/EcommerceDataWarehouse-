# 电商用户订单数据仓库分析平台 (EcommerceDataWarehouse)

基于 UCI Online Retail 真实电商交易数据，设计并实现端到端数据仓库分析平台。使用 Python 完成 ETL 流程，构建星型模型维度建模，数据存储于 MySQL，并通过 SQL 和 Python 完成多维度业务分析与可视化。

## 技术栈

- **编程语言**: Python 3.9+
- **数据处理**: Pandas, SQLAlchemy, PyMySQL
- **数据库**: MySQL 8.0
- **数据可视化**: Matplotlib, Seaborn
- **AI 查数**: Qwen2.5-0.5B-Instruct、Transformers、PyTorch
- **构建工具**: setuptools

## 项目结构

```
EcommerceDataWarehouse/
├── config/
│   ├── config.example.yaml       # 配置示例
│   └── config.yaml               # 本地配置，不提交 Git
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
├── ai_assistant.py               # 计划校验、参数化 SQL 与查询执行
├── local_model.py                # 本地千问推理与问题约束
├── evaluate_ai.py                # 模型计划及真实数据库结果评测
├── setup_ai_database.py          # 创建专用只读账号
├── run_ai.ps1                    # 本地查询入口
├── test_ai_assistant.py          # 独立 SQLite 测试
├── requirements-ai.txt           # AI 查数依赖
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
git clone https://github.com/chensihao635-crypto/EcommerceDataWarehouse-.git
cd EcommerceDataWarehouse-

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # Linux/Mac

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置数据库
# 将 config/config.example.yaml 复制为 config/config.yaml，填写 MySQL 连接信息

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


## AI 自然语言查数助手

使用本地 Qwen2.5-0.5B-Instruct 理解中文问题，输出结构化查询计划，再由程序生成参数化 SQL 查询数仓。模型不直接生成并执行任意 SQL。输出包括查询计划、SQL、绑定参数、指标口径和结果，便于复核。

```text
中文问题 → 模型生成查询计划 → 字段与指标一致性校验 → 参数化 SQL
        → MySQL 只读查询 → 返回计划、SQL、指标口径和结果
```

### 支持的指标与口径

| 指标 | 计算口径 |
| --- | --- |
| 销售额 | 有效订单明细金额之和 |
| 订单数 | 订单号去重计数 |
| 客单价 | 有效销售额 / 去重订单数，而非明细行平均金额 |
| 期间复购率 | 所选期间下单超过一次的客户数 / 期间下单客户数 |

支持整体、国家和月份分组，复购率暂不支持月份分组。国家分组的复购率按各国家分别计算。日期范围包含结束日。

DWD 已排除取消订单、缺失客户和非正数量/单价记录，销售额不代表扣除退货后的净收入。结果解释采用确定性的指标口径，不额外调用模型生成业务结论。

### 安装与准备

本机验证环境为 Python 3.12、MySQL 8.0.17。只运行查数助手无需安装原项目的 Spark 或 Airflow：

```powershell
python -m pip install -r requirements-ai.txt
```

下载指令模型到本地目录（模型权重不包含在 Git 仓库中）：

```powershell
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-0.5B-Instruct', local_dir='../qa/Qwen2.5-0.5B-Instruct')"
```

默认模型位于项目上一级的 `qa/Qwen2.5-0.5B-Instruct`。可使用 `--local-model` 指定其他目录。推理阶段仅加载本地文件，不自动下载模型、不执行模型仓库自定义代码。基础版 Qwen2-0.5B 在此前试跑中未生成有效计划，不作为默认模型。

### 配置 MySQL 只读连接

数据库需有 `dwd_order_detail`，字段包括 `invoice_no`、`customer_id`、`invoice_date`、`country`、`quantity`、`unit_price`、`total_amount`。本机已验证明细数据为 397,884 行，时间范围为 2010-12-01 至 2011-12-09。

已有数据后，可先复制 `config/config.example.yaml` 为 `config/config.yaml`，填写具备创建账号和授权权限的本地管理员凭据，再执行一次：

```powershell
python setup_ai_database.py
```

该脚本创建仅对 `dwd_order_detail` 拥有 SELECT 权限的 `ecommerce_ai_reader@localhost`，随机生成密码，并写入被 Git 忽略的 `.local_ai.json`。已有本地配置时不会覆盖；已有同名账号但无配置时应由管理员确认账号状态。它不建库、不导入数据。查询阶段不使用 ETL 管理员账号，密钥与数据库凭据不会传入模型。

也可由管理员预先创建只读账号，使用环境变量指定连接地址：

```powershell
$env:AI_READONLY_DB_URL = 'mysql+pymysql://只读账号:URL编码后的密码@localhost:3306/ecommerce_dw?charset=utf8mb4'
```

环境变量优先于 `.local_ai.json`。不要提交真实密码、模型密钥、`.local_ai.json` 或 `config/config.yaml`。

### 运行本地查数

在项目目录运行：

```powershell
python ai_assistant.py '2011年11月销售额最高的五个国家是哪些？' --local-model ../qa/Qwen2.5-0.5B-Instruct
```

默认模型目录就绪且未设置模型 API 密钥时，可以省略 `--local-model`，也可以使用 PowerShell 入口：

```powershell
./run_ai.ps1 '2011年11月销售额最高的五个国家是哪些？'
```

没有模型时，可跳过问题理解，直接验证计划到 MySQL 的查询链路：

```powershell
python ai_assistant.py --plan demo_plan.json
```

可用 `--sqlite 数据库路径` 只读访问同字段结构的 SQLite 演示数据库。查询计划与日期等筛选参数分别展示，便于复现。

### 可选模型 API

可使用支持 Chat Completions 和 JSON 对象输出的 HTTPS API，替代本地推理：

```powershell
$env:AI_API_KEY = '你的密钥'
$env:AI_BASE_URL = '服务商的 HTTPS 接口根地址，通常以 /v1 结尾'
$env:AI_MODEL = '服务商支持的模型名'
python ai_assistant.py '2011年11月销售额最高的五个国家是哪些？'
```

本地与 API 路径共享计划校验和查询执行；问题关键词检查及指标、国家分组一致性检查位于本地适配器，API 路径不应视为具备完全相同的问题级检查。API 接口尚未完成真实服务联调。

### 查询控制

- 模型输出必须符合固定字段与枚举，日期、排序、行数和分组均进行校验。
- SQL 只使用固定表名和指标表达式；国家、日期等输入通过参数绑定。
- MySQL 使用专用只读账号与只读事务，查询限时 5 秒，最多返回 100 行。
- 本地模型结合规则拒绝写操作、密码请求、预测等不支持问题，缺少年份时要求明确日期。
- 生成内容无法解析或校验不通过时，不执行查询。

### 测试与评测

```powershell
# 临时 SQLite 数据库测试，不调用模型、不连接真实 MySQL
python -m unittest test_ai_assistant.py -v

# 本地模型评测，查询题连接真实 MySQL，只读执行
python evaluate_ai.py --model ../qa/Qwen2.5-0.5B-Instruct
```

本机验证结果：

- 4 组单元测试通过，覆盖计算口径、日期边界、分组、无效计划与参数注入。
- 16 道查询的计划及真实数据库结果一致，8 道不支持请求被拒绝；逐题报告见 [最终评测报告](output/ai_evaluation.json)。
- 整体聚合只有一行，评测忽略不影响答案的排序方向及行数差异；其余计划字段仍须匹配。

这是小范围、模板化题集，提示示例与题集存在相近表达，不代表开放域准确率或独立盲测成绩。拒答测试只衡量不执行，不衡量解释质量。[首轮记录](output/ai_evaluation_baseline.json) 使用早期提示和评估规则，不宜直接比较百分比。

### 已知边界

尚未全面评测英文、跨年区间、复杂国家筛选、多指标和多轮对话；暂不支持预测、因果归因及自定义 SQL。模型仍可能误解问题，需核对展示的计划和指标口径。

后续可扩展独立人工标注题集、国家过滤与空结果测试，并加入查询上下文和多轮追问。当前实现不应描述为已经支持这些能力。
