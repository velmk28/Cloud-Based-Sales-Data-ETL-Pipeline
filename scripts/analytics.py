import os
import logging
import pandas as pd
from load import get_db_engine

logger = logging.getLogger(__name__)

def generate_analytics_report(output_dir="logs"):
    """
    Connects to the database, executes analytics queries,
    logs results, and saves report files locally.
    """
    logger.info("Executing pipeline database analytics and business queries...")
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        engine = get_db_engine()
        reports = {}
        
        with engine.connect() as conn:
            # 1. Executive Summary Report
            logger.info(" -> Querying Executive Summary KPI Report...")
            summary_sql = """
                SELECT 
                    SUM(revenue) AS total_revenue,
                    SUM(cost) AS total_cost,
                    SUM(profit) AS total_profit,
                    ROUND((SUM(profit) / SUM(revenue)) * 100, 2) AS net_profit_margin_pct,
                    COUNT(sales_key) AS transaction_count,
                    SUM(quantity) AS units_sold
                FROM fact_sales;
            """
            summary_df = pd.read_sql(summary_sql, conn)
            reports["executive_summary"] = summary_df
            
            # Print executive summary to log
            if not summary_df.empty:
                logger.info("--- EXECUTIVE SUMMARY KPI REPORT ---")
                logger.info(f"Total Revenue       : ${summary_df.loc[0, 'total_revenue']:,.2f}")
                logger.info(f"Total Profit        : ${summary_df.loc[0, 'total_profit']:,.2f}")
                logger.info(f"Net Profit Margin   : {summary_df.loc[0, 'net_profit_margin_pct']}%")
                logger.info(f"Transactions Count  : {summary_df.loc[0, 'transaction_count']:,}")
                logger.info(f"Total Units Sold    : {summary_df.loc[0, 'units_sold']:,}")
                logger.info("------------------------------------")
            
            # 2. Top Products Report
            logger.info(" -> Querying Top Selling Products...")
            top_products_sql = """
                SELECT 
                    p.product_id,
                    p.product_name,
                    p.category,
                    SUM(s.quantity) AS total_units_sold,
                    SUM(s.revenue) AS total_revenue,
                    SUM(s.profit) AS total_profit
                FROM fact_sales s
                JOIN dim_products p ON s.product_key = p.product_key
                GROUP BY p.product_key, p.product_id, p.product_name, p.category
                ORDER BY total_revenue DESC
                LIMIT 5;
            """
            top_products_df = pd.read_sql(top_products_sql, conn)
            reports["top_products"] = top_products_df
            
            # 3. Category Performance Report
            logger.info(" -> Querying Category Performance Breakdown...")
            category_sql = """
                SELECT 
                    p.category,
                    COUNT(DISTINCT s.product_key) AS unique_products_sold,
                    SUM(s.quantity) AS total_units_sold,
                    SUM(s.revenue) AS total_revenue,
                    SUM(s.profit) AS total_profit,
                    ROUND((SUM(s.profit) / SUM(s.revenue)) * 100, 2) AS net_margin_pct
                FROM fact_sales s
                JOIN dim_products p ON s.product_key = p.product_key
                GROUP BY p.category
                ORDER BY total_revenue DESC;
            """
            category_df = pd.read_sql(category_sql, conn)
            reports["category_performance"] = category_df
            
            if "sqlite" in engine.name:
                mom_sql = """
                    WITH MonthlySales AS (
                        SELECT 
                            CAST(strftime('%Y', date) AS INTEGER) AS sales_year,
                            CAST(strftime('%m', date) AS INTEGER) AS sales_month,
                            SUM(revenue) AS monthly_revenue
                        FROM fact_sales
                        GROUP BY strftime('%Y', date), strftime('%m', date)
                    )
                    SELECT 
                        sales_year,
                        sales_month,
                        monthly_revenue,
                        LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month) AS prev_month_revenue,
                        ROUND(monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month), 2) AS revenue_change,
                        ROUND(((monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month)) / 
                               LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month)) * 100, 2) AS mom_growth_pct
                    FROM MonthlySales
                    ORDER BY sales_year, sales_month;
                """
            else:
                mom_sql = """
                    WITH MonthlySales AS (
                        SELECT 
                            YEAR(date) AS sales_year,
                            MONTH(date) AS sales_month,
                            SUM(revenue) AS monthly_revenue
                        FROM fact_sales
                        GROUP BY YEAR(date), MONTH(date)
                    )
                    SELECT 
                        sales_year,
                        sales_month,
                        monthly_revenue,
                        LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month) AS prev_month_revenue,
                        ROUND(monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month), 2) AS revenue_change,
                        ROUND(((monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month)) / 
                               LAG(monthly_revenue, 1) OVER (ORDER BY sales_year, sales_month)) * 100, 2) AS mom_growth_pct
                    FROM MonthlySales
                    ORDER BY sales_year, sales_month;
                """
            mom_df = pd.read_sql(mom_sql, conn)
            reports["mom_growth"] = mom_df
            
            # 5. Geographical Sales Report
            logger.info(" -> Querying Country-Wise Revenue Breakdown...")
            country_sql = """
                SELECT 
                    c.country,
                    COUNT(s.sales_key) AS transaction_count,
                    SUM(s.revenue) AS total_revenue,
                    SUM(s.profit) AS total_profit
                FROM fact_sales s
                JOIN dim_customers c ON s.customer_key = c.customer_key
                GROUP BY c.country
                ORDER BY total_revenue DESC;
            """
            country_df = pd.read_sql(country_sql, conn)
            reports["country_sales"] = country_df
            
        # Write reports to CSV files inside logs/ folder
        for report_name, df in reports.items():
            report_path = os.path.join(output_dir, f"report_{report_name}.csv")
            df.to_csv(report_path, index=False)
            
        logger.info(f"Analytics Reports generated successfully. Saved CSV files to '{output_dir}/'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate analytics report: {e}")
        return False

if __name__ == "__main__":
    # Setup basic logging to run script independently
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    generate_analytics_report()
