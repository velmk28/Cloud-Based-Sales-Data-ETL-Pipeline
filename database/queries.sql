-- -----------------------------------------------------------------------------
-- SQL Analytics Queries for BI and Dashboard reports
-- Database: sales_data
-- -----------------------------------------------------------------------------

USE sales_data;

-- 1. High-Level Executive KPI Summary
-- Calculates total revenue, cost, profit, and overall profit margin.
SELECT 
    SUM(revenue) AS total_revenue,
    SUM(cost) AS total_cost,
    SUM(profit) AS total_profit,
    (SUM(profit) / SUM(revenue)) * 100 AS profit_margin_percentage,
    COUNT(sales_key) AS total_transactions,
    SUM(quantity) AS total_units_sold
FROM 
    fact_sales;


-- 2. Top 5 Best-Selling Products by Revenue
-- Shows which products drive the most income.
SELECT 
    p.product_id,
    p.product_name,
    p.category,
    SUM(s.quantity) AS total_units_sold,
    SUM(s.revenue) AS total_revenue,
    SUM(s.profit) AS total_profit
FROM 
    fact_sales s
JOIN 
    dim_products p ON s.product_key = p.product_key
GROUP BY 
    p.product_key, p.product_id, p.product_name, p.category
ORDER BY 
    total_revenue DESC
LIMIT 5;


-- 3. Category Performance Analysis
-- Evaluates performance aggregates across product divisions.
SELECT 
    p.category,
    COUNT(DISTINCT s.product_key) AS unique_products_sold,
    SUM(s.quantity) AS total_units_sold,
    SUM(s.revenue) AS total_revenue,
    SUM(s.profit) AS total_profit,
    (SUM(s.profit) / SUM(s.revenue)) * 100 AS net_profit_margin_pct
FROM 
    fact_sales s
JOIN 
    dim_products p ON s.product_key = p.product_key
GROUP BY 
    p.category
ORDER BY 
    total_revenue DESC;


-- 4. Month-over-Month (MoM) Growth Analysis
-- Computes monthly revenue along with the growth percentage compared to the previous month.
WITH MonthlySales AS (
    SELECT 
        YEAR(date) AS sales_year,
        MONTH(date) AS sales_month,
        SUM(revenue) AS monthly_revenue
    FROM 
        fact_sales
    GROUP BY 
        YEAR(date), MONTH(date)
)
SELECT 
    sales_year,
    sales_month,
    monthly_revenue,
    LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month) AS prev_month_revenue,
    monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month) AS revenue_change,
    ((monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month)) / 
     LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month)) * 100 AS mom_growth_pct
FROM 
    MonthlySales
ORDER BY 
    sales_year, sales_month;


-- 5. Sales Performance by Country (Geographic Breakdown)
-- Analyzes sales distribution by customer regions.
SELECT 
    c.country,
    COUNT(s.sales_key) AS transaction_count,
    SUM(s.quantity) AS total_units_sold,
    SUM(s.revenue) AS total_revenue,
    SUM(s.profit) AS total_profit
FROM 
    fact_sales s
JOIN 
    dim_customers c ON s.customer_key = c.customer_key
GROUP BY 
    c.country
ORDER BY 
    total_revenue DESC;


-- 6. Average Transaction Value (ATV) Trend
-- Tracking buyer ticket size trends over time.
SELECT 
    YEAR(date) AS sales_year,
    MONTH(date) AS sales_month,
    AVG(revenue) AS avg_transaction_value,
    SUM(revenue) / COUNT(DISTINCT customer_key) AS revenue_per_customer
FROM 
    fact_sales
GROUP BY 
    YEAR(date), MONTH(date)
ORDER BY 
    sales_year, sales_month;
