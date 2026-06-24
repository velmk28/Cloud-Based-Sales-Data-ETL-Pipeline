# Power BI Dashboard Design Guide

This guide provides step-by-step instructions for connecting Power BI to the ETL database (either local MySQL or AWS RDS) and building a professional retail analytics dashboard.

---

## 1. Database Connection

To load your ETL pipeline data into Power BI:

1. Open Power BI Desktop.
2. Click **Get Data** on the Home ribbon and select **MySQL database** (click **Connect**).
3. In the dialog box:
   * **Server**: `localhost:3306` (or your AWS RDS endpoint, e.g., `sales-rds.c123456789.us-east-1.rds.amazonaws.com:3306`)
   * **Database**: `sales_data`
   * **Connection Mode**: Import
4. Click **OK**.
5. When prompted for credentials, select the **Database** tab (do not choose Windows/Anonymous):
   * **Username**: `sales_user`
   * **Password**: `sales_secure_password`
6. Click **Connect**. If a warning about encryption pops up, select **OK/Run** to bypass if running locally without SSL.
7. In the Navigator window, select the following tables:
   * `dim_customers`
   * `dim_products`
   * `fact_sales`
8. Click **Load**.

---

## 2. Data Modeling (Star Schema)

Once the tables are loaded, switch to the **Model View** (left-hand sidebar) to configure relationships. Power BI should automatically detect them, but verify they match the following structure:

| From Table (Dimension) | Key | To Table (Fact) | Key | Cardinality | Cross Filter |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `dim_products` | `product_key` | `fact_sales` | `product_key` | 1 to Many (1:\*) | Single (Dim filters Fact) |
| `dim_customers` | `customer_key` | `fact_sales` | `customer_key` | 1 to Many (1:\*) | Single (Dim filters Fact) |

Ensure the `date` field in `fact_sales` is marked or configured as a Date datatype.

---

## 3. DAX Measures (Business Intelligence Metrics)

Create a dedicated measures table or add these measures to the `fact_sales` table:

### Total Revenue
```dax
Total Revenue = SUM(fact_sales[revenue])
```

### Total Cost
```dax
Total Cost = SUM(fact_sales[cost])
```

### Total Profit
```dax
Total Profit = SUM(fact_sales[profit])
```

### Net Profit Margin %
```dax
Profit Margin % = DIVIDE([Total Profit], [Total Revenue], 0)
```
*(Format as a Percentage: `0.0%`)*

### Total Units Sold
```dax
Total Units Sold = SUM(fact_sales[quantity])
```

### Total Transactions
```dax
Transaction Count = COUNTROWS(fact_sales)
```

### Month-over-Month (MoM) Revenue Growth %
```dax
MoM Revenue Growth % = 
VAR CurrentMonthRevenue = [Total Revenue]
VAR PrevMonthRevenue = 
    CALCULATE(
        [Total Revenue], 
        DATEADD('fact_sales'[date], -1, MONTH)
    )
RETURN
    DIVIDE(CurrentMonthRevenue - PrevMonthRevenue, PrevMonthRevenue, 0)
```
*(Format as a Percentage: `0.0%`)*

---

## 4. Visual Layout & UI Design

Create a single-page Executive Dashboard with a **Dark Theme** (e.g., Charcoal background `#1A1C1E` and Accent colors `#0A84FF` and `#30D158`).

### Header Banner
* **Visual**: Text Box.
* **Content**: "Executive Sales Performance Dashboard" (Size 20, Semi-Bold, white text).
* **Position**: Top, full width.

### KPI Cards (Row of 4 across the top)
1. **Total Revenue Card**:
   * Value: `[Total Revenue]` (Display unit: Auto, e.g., $1.24M).
   * Title: "Total Revenue".
2. **Total Profit Card**:
   * Value: `[Total Profit]` (e.g., $415.5K).
   * Title: "Net Profit".
3. **Net Margin Card**:
   * Value: `[Profit Margin %]` (e.g., 33.4%).
   * Title: "Profit Margin".
4. **Units Sold Card**:
   * Value: `[Total Units Sold]` (e.g., 12.5K units).
   * Title: "Total Units Sold".

### Charts Section (Middle Row)
* **Left: Monthly Revenue Trend (Line Chart)**
  * Axis (X-axis): `fact_sales[date]` (grouped by Year & Month).
  * Values (Y-axis): `[Total Revenue]` (Line) and `[MoM Revenue Growth %]` (Tooltips).
  * Styling: Smooth line interpolation, color `#0A84FF`, markers enabled.
* **Right: Product Category Breakdown (Donut Chart)**
  * Legend: `dim_products[category]`.
  * Values: `[Total Revenue]`.
  * Styling: Show Category + percentage of total labels.

### Table & Geo Section (Bottom Row)
* **Left: Top 5 Best-Selling Products (Clustered Bar Chart)**
  * Y-axis: `dim_products[product_name]`.
  * X-axis: `[Total Revenue]`.
  * Filters: Top N filter applied to `dim_products[product_name]`, N = 5, by value `[Total Revenue]`.
* **Right: Sales by Country (Map Visual)**
  * Location: `dim_customers[country]`.
  * Bubble size: `[Total Revenue]`.
  * Styling: Dark map background style, bubble size scaled appropriately.

---

## 5. Connecting Directly to AWS RDS (Production Deployment)

When deploying to production, modify the data source credentials:
1. In Power BI, go to **Home** -> **Transform Data** -> **Data Source Settings**.
2. Select the MySQL Connection and click **Edit Permissions**.
3. Set the new endpoint address (your RDS instance URL) and username/password.
4. Save and click **Refresh** on the dashboard ribbon.
