-- ============================================================
-- 电商用户订单数据仓库分析平台 - 分析查询SQL
-- ============================================================

-- ============================================================
-- 1. 用户分析
-- ============================================================

-- 1.1 用户消费分层（RFM分析）
WITH rfm AS (
    SELECT 
        customer_id,
        MAX(invoice_date) as last_purchase,
        COUNT(DISTINCT invoice_no) as frequency,
        SUM(total_amount) as monetary
    FROM dwd_order_detail
    GROUP BY customer_id
),
rfm_scored AS (
    SELECT 
        customer_id,
        last_purchase,
        frequency,
        monetary,
        NTILE(5) OVER (ORDER BY last_purchase DESC) as r_score,
        NTILE(5) OVER (ORDER BY frequency DESC) as f_score,
        NTILE(5) OVER (ORDER BY monetary DESC) as m_score
    FROM rfm
)
SELECT 
    customer_id,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score) as rfm_total,
    CASE 
        WHEN (r_score + f_score + m_score) >= 12 THEN 'High Value'
        WHEN (r_score + f_score + m_score) >= 8 THEN 'Medium Value'
        ELSE 'Low Value'
    END as customer_segment
FROM rfm_scored
ORDER BY rfm_total DESC;

-- 1.2 用户活跃度分析
SELECT 
    customer_id,
    MIN(invoice_date) as first_order,
    MAX(invoice_date) as last_order,
    COUNT(DISTINCT invoice_no) as total_orders,
    SUM(total_amount) as total_spend,
    AVG(total_amount) as avg_order_value,
    EXTRACT(DAY FROM MAX(invoice_date) - MIN(invoice_date)) as customer_lifespan_days
FROM dwd_order_detail
GROUP BY customer_id
ORDER BY total_spend DESC
LIMIT 20;

-- ============================================================
-- 2. 商品分析
-- ============================================================

-- 2.1 商品销售排行
SELECT 
    stock_code,
    MAX(description) as description,
    SUM(quantity) as total_quantity,
    SUM(total_amount) as total_revenue,
    COUNT(DISTINCT customer_id) as unique_customers,
    COUNT(DISTINCT invoice_no) as total_orders
FROM dwd_order_detail
GROUP BY stock_code
ORDER BY total_revenue DESC
LIMIT 20;

-- 2.2 商品月度销售趋势
SELECT 
    DATE_TRUNC('month', invoice_date) as sale_month,
    stock_code,
    MAX(description) as description,
    SUM(quantity) as monthly_quantity,
    SUM(total_amount) as monthly_revenue
FROM dwd_order_detail
GROUP BY sale_month, stock_code
ORDER BY sale_month, monthly_revenue DESC;

-- ============================================================
-- 3. 时间分析
-- ============================================================

-- 3.1 每日销售趋势
SELECT 
    invoice_date_only as sale_date,
    SUM(total_amount) as daily_sales,
    COUNT(DISTINCT invoice_no) as daily_orders,
    COUNT(DISTINCT customer_id) as daily_customers
FROM dwd_order_detail
GROUP BY invoice_date_only
ORDER BY sale_date;

-- 3.2 每月销售趋势
SELECT 
    year,
    month,
    SUM(total_amount) as monthly_sales,
    COUNT(DISTINCT invoice_no) as monthly_orders,
    COUNT(DISTINCT customer_id) as monthly_customers
FROM dwd_order_detail
GROUP BY year, month
ORDER BY year, month;

-- 3.3 小时销售分布
SELECT 
    hour,
    SUM(total_amount) as hourly_sales,
    COUNT(DISTINCT invoice_no) as hourly_orders
FROM dwd_order_detail
GROUP BY hour
ORDER BY hour;

-- 3.4 星期销售分布
SELECT 
    day_of_week,
    CASE day_of_week
        WHEN 0 THEN 'Monday'
        WHEN 1 THEN 'Tuesday'
        WHEN 2 THEN 'Wednesday'
        WHEN 3 THEN 'Thursday'
        WHEN 4 THEN 'Friday'
        WHEN 5 THEN 'Saturday'
        WHEN 6 THEN 'Sunday'
    END as day_name,
    SUM(total_amount) as daily_sales,
    COUNT(DISTINCT invoice_no) as daily_orders
FROM dwd_order_detail
GROUP BY day_of_week
ORDER BY day_of_week;

-- ============================================================
-- 4. 地区分析
-- ============================================================

-- 4.1 各国家销售排行
SELECT 
    country,
    SUM(total_amount) as total_sales,
    COUNT(DISTINCT customer_id) as unique_customers,
    COUNT(DISTINCT invoice_no) as total_orders
FROM dwd_order_detail
GROUP BY country
ORDER BY total_sales DESC
LIMIT 15;

-- 4.2 各国家Top3商品
WITH ranked_products AS (
    SELECT 
        country,
        stock_code,
        MAX(description) as description,
        SUM(total_amount) as revenue,
        ROW_NUMBER() OVER (PARTITION BY country ORDER BY SUM(total_amount) DESC) as rank
    FROM dwd_order_detail
    GROUP BY country, stock_code
)
SELECT 
    country,
    stock_code,
    description,
    revenue
FROM ranked_products
WHERE rank <= 3
ORDER BY country, rank;

-- ============================================================
-- 5. 数据仓库层级汇总
-- ============================================================

-- 5.1 DWS层：用户消费汇总表
SELECT * FROM dws_customer_summary
ORDER BY purchase_amount DESC
LIMIT 20;

-- 5.2 DWS层：商品销售汇总表
SELECT * FROM dws_product_summary
ORDER BY sale_amount DESC
LIMIT 20;

-- 5.3 ADS层：销售仪表盘
SELECT * FROM ads_sales_dashboard
ORDER BY sale_date DESC;

-- ============================================================
-- 6. 数据质量检查
-- ============================================================

-- 6.1 各层数据量统计
SELECT 
    'ODS层' as layer,
    COUNT(*) as row_count
FROM ods_retail
UNION ALL
SELECT 
    'DWD层' as layer,
    COUNT(*) as row_count
FROM dwd_order_detail
UNION ALL
SELECT 
    'DWS用户汇总' as layer,
    COUNT(*) as row_count
FROM dws_customer_summary
UNION ALL
SELECT 
    'DWS商品汇总' as layer,
    COUNT(*) as row_count
FROM dws_product_summary
UNION ALL
SELECT 
    'ADS销售仪表盘' as layer,
    COUNT(*) as row_count
FROM ads_sales_dashboard;

-- 6.2 数据空值检查
SELECT 
    'CustomerID空值' as check_name,
    COUNT(*) as null_count
FROM ods_retail
WHERE customer_id IS NULL
UNION ALL
SELECT 
    'Description空值' as check_name,
    COUNT(*) as null_count
FROM ods_retail
WHERE description IS NULL;