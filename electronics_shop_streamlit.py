import sqlite3
from datetime import date, timedelta
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

DB_FILE = "electronics_shop.db"

st.set_page_config(
    page_title="Dabas Electronics | Shop Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------- Styling ---------------------------------------
st.markdown("""
<style>
.stApp { background: #071522; color: #e8f1fa; }
[data-testid="stSidebar"] { background: #091b2b; }
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #102438, #142d43);
    border: 1px solid #29445a; padding: 15px; border-radius: 12px;
}
[data-testid="stMetricLabel"] { color: #9db1c5 !important; }
[data-testid="stMetricValue"] { color: #e8f1fa !important; }
div[data-testid="stDataFrame"] { border: 1px solid #29445a; border-radius: 8px; }
h1, h2, h3 { color: #e8f1fa; }
div.stButton > button, div.stDownloadButton > button {
    border-radius: 8px; border: 1px solid #1685f8; font-weight: 600;
}
.small-muted { color: #9db1c5; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)


# ---------------------------- Database --------------------------------------
def connect():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT 'Other',
            brand TEXT NOT NULL DEFAULT 'Other',
            cost_price REAL NOT NULL DEFAULT 0,
            selling_price REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            reorder_level INTEGER NOT NULL DEFAULT 5
        );
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sold_at TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            unit_cost REAL NOT NULL,
            discount REAL NOT NULL DEFAULT 0,
            customer TEXT DEFAULT '',
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchased_at TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_cost REAL NOT NULL,
            supplier TEXT DEFAULT '',
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spent_at TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT DEFAULT ''
        );
        """)
        conn.commit()


def read_df(sql, params=()):
    with connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def run_sql(sql, params=()):
    with connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def load_sample_data():
    products_count = read_df("SELECT COUNT(*) AS n FROM products").iloc[0]["n"]
    if products_count:
        return False, "The database already contains products. Sample data was not added to avoid mixing it with your real records."
    items = [
        ("Samsung Galaxy A55", "Mobiles", "Samsung", 28000, 32999, 12, 4),
        ("iPhone 13", "Mobiles", "Apple", 36000, 41999, 3, 5),
        ("HP Laptop i5", "Laptops", "HP", 48000, 55999, 7, 3),
        ("Dell Inspiron i3", "Laptops", "Dell", 34000, 39999, 2, 3),
        ("boAt Airdopes", "Accessories", "boAt", 900, 1499, 18, 8),
        ("realme Charger 33W", "Accessories", "realme", 500, 899, 4, 10),
        ("Mi Power Bank", "Accessories", "Xiaomi", 1000, 1699, 6, 8),
        ("Samsung 43-inch TV", "TV & Audio", "Samsung", 24000, 28999, 2, 3),
        ("Sony Headphones", "TV & Audio", "Sony", 3500, 4999, 5, 3),
        ("LG Refrigerator", "Home Appliances", "LG", 22000, 26999, 4, 2),
        ("Logitech Keyboard", "Accessories", "Logitech", 700, 1199, 14, 5),
        ("USB-C Cable", "Accessories", "Generic", 120, 299, 30, 10),
    ]
    with connect() as conn:
        conn.executemany("""INSERT INTO products(name,category,brand,cost_price,selling_price,stock,reorder_level)
                            VALUES(?,?,?,?,?,?,?)""", items)
        rows = conn.execute("SELECT id,name,cost_price,selling_price FROM products").fetchall()
        rng = np.random.default_rng(12)
        today = date.today()
        for offset in range(89, -1, -1):
            day = today - timedelta(days=offset)
            for _ in range(int(rng.integers(1, 5))):
                p = rows[int(rng.integers(0, len(rows)))]
                qty = int(rng.integers(1, 4))
                conn.execute("""INSERT INTO sales(sold_at,product_id,product_name,quantity,unit_price,unit_cost,discount,customer)
                                VALUES(?,?,?,?,?,?,?,?)""",
                             (day.isoformat(), p["id"], p["name"], qty, float(p["selling_price"]),
                              float(p["cost_price"]), float(rng.choice([0, 0, 0, 50, 100])),
                              f"Customer {int(rng.integers(1, 45))}"))
        for p in rows:
            conn.execute("""INSERT INTO purchases(purchased_at,product_id,product_name,quantity,unit_cost,supplier)
                            VALUES(?,?,?,?,?,?)""",
                         (today.isoformat(), p["id"], p["name"], int(rng.integers(5, 16)),
                          float(p["cost_price"]), "Sample Supplier"))
        for cat, amount in [("Rent", 18000), ("Electricity", 3500), ("Salary", 22000),
                            ("Internet", 1200), ("Other", 1800)]:
            conn.execute("INSERT INTO expenses(spent_at,category,amount,note) VALUES(?,?,?,?)",
                         (today.isoformat(), cat, amount, "Sample expense"))
        conn.commit()
    return True, "Sample products, sales, purchases, and expenses have been added."


def metrics(start_date=None, end_date=None):
    sales = read_df("SELECT * FROM sales")
    purchases = read_df("SELECT * FROM purchases")
    expenses = read_df("SELECT * FROM expenses")
    products = read_df("SELECT * FROM products")

    if start_date and end_date:
        if not sales.empty:
            sales = sales[(sales["sold_at"] >= str(start_date)) & (sales["sold_at"] <= str(end_date))]
        if not purchases.empty:
            purchases = purchases[(purchases["purchased_at"] >= str(start_date)) & (purchases["purchased_at"] <= str(end_date))]
        if not expenses.empty:
            expenses = expenses[(expenses["spent_at"] >= str(start_date)) & (expenses["spent_at"] <= str(end_date))]

    revenue = float((sales["quantity"] * sales["unit_price"] - sales["discount"]).sum()) if not sales.empty else 0.0
    cogs = float((sales["quantity"] * sales["unit_cost"]).sum()) if not sales.empty else 0.0
    gross = revenue - cogs
    expense_total = float(expenses["amount"].sum()) if not expenses.empty else 0.0
    net = gross - expense_total
    purchase_total = float((purchases["quantity"] * purchases["unit_cost"]).sum()) if not purchases.empty else 0.0
    margin = gross / revenue * 100 if revenue else 0.0
    return sales, purchases, expenses, products, revenue, cogs, gross, expense_total, net, purchase_total, margin


def fmt(value):
    return f"₹{float(value or 0):,.2f}"


def add_chart_theme(ax):
    ax.set_facecolor("#102438")
    ax.tick_params(colors="#c7d7e6", labelsize=9)
    ax.xaxis.label.set_color("#c7d7e6")
    ax.yaxis.label.set_color("#c7d7e6")
    ax.title.set_color("#e8f1fa")
    for spine in ax.spines.values():
        spine.set_color("#29445a")
    ax.grid(axis="y", color="#29445a", alpha=0.65)
    ax.set_axisbelow(True)


# ---------------------------- Sidebar ---------------------------------------
init_db()
st.sidebar.markdown("# 🛒 Dabas Electronics")
st.sidebar.caption("Shop Management & Analytics")
page = st.sidebar.radio(
    "NAVIGATION",
    ["Dashboard", "Sales Analysis", "Products & Inventory", "Record Sale",
     "Record Purchase", "Expenses", "Reports & Export"],
)
st.sidebar.divider()
st.sidebar.markdown("### Quick actions")
if st.sidebar.button("↻ Refresh data", use_container_width=True):
    st.rerun()
if st.sidebar.button("＋ Load sample data", use_container_width=True):
    ok, msg = load_sample_data()
    (st.sidebar.success if ok else st.sidebar.info)(msg)
    st.rerun()
st.sidebar.caption("Records are stored in a local SQLite database.")


# ---------------------------- Dashboard -------------------------------------
st.title("Dabas Electronics")
st.caption("Shop Management & Analytics System")

if page == "Dashboard":
    st.subheader("Business Overview")
    st.caption("Summary uses all records currently stored in the database.")
    sales, purchases, expenses, products, revenue, cogs, gross, expense_total, net, purchase_total, margin = metrics()
    units = int(products["stock"].sum()) if not products.empty else 0
    low = products[products["stock"] <= products["reorder_level"]] if not products.empty else products

    cols = st.columns(6)
    cards = [
        ("Total Sales", fmt(revenue)),
        ("Purchase Value", fmt(purchase_total)),
        ("Gross Profit", fmt(gross)),
        ("Est. Net Profit", fmt(net)),
        ("Gross Margin", f"{margin:.1f}%"),
        ("Stock Units", f"{units:,}"),
    ]
    for col, (label, value) in zip(cols, cards):
        col.metric(label, value)

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("#### Sales & gross profit trend")
        if not sales.empty:
            s = sales.copy()
            s["sold_at"] = pd.to_datetime(s["sold_at"], errors="coerce")
            s["revenue"] = s["quantity"] * s["unit_price"] - s["discount"]
            s["gross_profit"] = s["revenue"] - s["quantity"] * s["unit_cost"]
            daily = s.groupby(s["sold_at"].dt.date)[["revenue", "gross_profit"]].sum().tail(30)
            fig, ax = plt.subplots(figsize=(8, 3.4))
            fig.patch.set_facecolor("#102438")
            ax.plot(daily.index.astype(str), daily["revenue"], marker="o", color="#1685f8", label="Sales")
            ax.plot(daily.index.astype(str), daily["gross_profit"], marker="o", color="#13c995", label="Gross profit")
            add_chart_theme(ax)
            ax.tick_params(axis="x", rotation=55)
            ax.legend(facecolor="#102438", labelcolor="#e8f1fa")
            fig.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.info("Record sales or load sample data to see the trend.")

    with right:
        st.markdown("#### Best-selling products")
        if not sales.empty:
            top = sales.groupby("product_name")["quantity"].sum().sort_values().tail(8)
            fig, ax = plt.subplots(figsize=(7, 3.4))
            fig.patch.set_facecolor("#102438")
            ax.barh(top.index, top.values, color="#27c7e7")
            ax.set_xlabel("Units sold")
            add_chart_theme(ax)
            fig.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.info("No sales yet.")

    left, right = st.columns(2)
    with left:
        st.markdown("#### Sales by category")
        if not sales.empty:
            cat = sales.groupby("product_name")["quantity"].sum().reset_index().merge(
                products[["name", "category"]], left_on="product_name", right_on="name", how="left")
            cat = cat.groupby("category")["quantity"].sum().sort_values(ascending=False)
            fig, ax = plt.subplots(figsize=(7, 3.2))
            fig.patch.set_facecolor("#102438")
            ax.bar(cat.index, cat.values, color=["#1685f8", "#13c995", "#ff9f43", "#9b5cf6", "#f34d68"][:len(cat)])
            ax.set_ylabel("Units sold")
            add_chart_theme(ax)
            ax.tick_params(axis="x", rotation=20)
            fig.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.info("No category sales data yet.")
    with right:
        st.markdown("#### Inventory alerts")
        if low.empty:
            st.success("No products are at or below their reorder level.")
        else:
            show = low[["name", "category", "stock", "reorder_level"]].copy()
            show["Suggested order"] = (show["reorder_level"] * 2 - show["stock"]).clip(lower=1)
            show.columns = ["Product", "Category", "Current stock", "Reorder at", "Suggested order"]
            st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("#### Key insights")
    insights = []
    insights.append(f"Gross profit is {fmt(gross)} and estimated net profit after recorded expenses is {fmt(net)}.")
    insights.append(f"{len(low)} product(s) are at or below their reorder level.")
    if not sales.empty:
        top_name = sales.groupby("product_name")["quantity"].sum().idxmax()
        top_qty = int(sales.groupby("product_name")["quantity"].sum().max())
        insights.append(f"Best seller by units: {top_name} ({top_qty} units).")
        sales2 = sales.assign(revenue=sales["quantity"] * sales["unit_price"] - sales["discount"])
        best_revenue = sales2.groupby("product_name")["revenue"].sum().idxmax()
        insights.append(f"Highest revenue product in recorded sales: {best_revenue}.")
    for item in insights:
        st.write("•", item)
    st.caption("Net profit is an estimate based on recorded sales, product costs and expenses. Tax, returns, payment fees and other unrecorded costs are not automatically included.")


# ---------------------------- Sales Analysis --------------------------------
elif page == "Sales Analysis":
    st.subheader("Sales Analysis")
    sales = read_df("SELECT * FROM sales ORDER BY sold_at DESC")
    products = read_df("SELECT * FROM products")
    if sales.empty:
        st.info("No sales yet. Record a sale or load sample data.")
    else:
        sales["sold_at"] = pd.to_datetime(sales["sold_at"], errors="coerce")
        sales["Revenue"] = sales["quantity"] * sales["unit_price"] - sales["discount"]
        sales["Gross profit"] = sales["Revenue"] - sales["quantity"] * sales["unit_cost"]
        start, end = st.columns(2)
        min_day = sales["sold_at"].min().date()
        max_day = sales["sold_at"].max().date()
        start_date = start.date_input("From date", value=min_day, min_value=min_day, max_value=max_day)
        end_date = end.date_input("To date", value=max_day, min_value=min_day, max_value=max_day)
        if start_date > end_date:
            st.error("Start date must be on or before end date.")
        else:
            filtered = sales[(sales["sold_at"].dt.date >= start_date) & (sales["sold_at"].dt.date <= end_date)]
            r = filtered["Revenue"].sum()
            g = filtered["Gross profit"].sum()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sales", fmt(r))
            c2.metric("Gross profit", fmt(g))
            c3.metric("Units sold", f"{int(filtered['quantity'].sum()):,}")
            c4.metric("Transactions", f"{len(filtered):,}")
            a, b = st.columns(2)
            with a:
                st.markdown("#### Revenue by product")
                prod = filtered.groupby("product_name")["Revenue"].sum().sort_values().tail(10)
                fig, ax = plt.subplots(figsize=(7, 4))
                fig.patch.set_facecolor("#102438")
                ax.barh(prod.index, prod.values, color="#1685f8")
                ax.set_xlabel("Revenue ₹")
                add_chart_theme(ax)
                fig.tight_layout()
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
            with b:
                st.markdown("#### Profit by product")
                prof = filtered.groupby("product_name")["Gross profit"].sum().sort_values().tail(10)
                fig, ax = plt.subplots(figsize=(7, 4))
                fig.patch.set_facecolor("#102438")
                ax.barh(prof.index, prof.values, color="#13c995")
                ax.set_xlabel("Gross profit ₹")
                add_chart_theme(ax)
                fig.tight_layout()
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
            st.markdown("#### Transactions")
            st.dataframe(filtered.sort_values("sold_at", ascending=False), use_container_width=True, hide_index=True)


# ---------------------------- Products & Inventory -------------------------
elif page == "Products & Inventory":
    st.subheader("Products & Inventory")
    with st.expander("＋ Add a product", expanded=True):
        with st.form("add_product_form", clear_on_submit=True):
            a, b, c = st.columns(3)
            name = a.text_input("Product name")
            category = b.selectbox("Category", ["Mobiles", "Laptops", "Accessories", "TV & Audio", "Home Appliances", "Other"])
            brand = c.text_input("Brand", value="Other")
            d, e, f, g = st.columns(4)
            cost = d.number_input("Cost price ₹", min_value=0.0, step=100.0)
            price = e.number_input("Selling price ₹", min_value=0.0, step=100.0)
            stock = f.number_input("Opening stock", min_value=0, step=1)
            reorder = g.number_input("Reorder level", min_value=0, step=1, value=5)
            submitted = st.form_submit_button("Add product", type="primary")
            if submitted:
                if not name.strip():
                    st.error("Enter a product name.")
                else:
                    try:
                        run_sql("""INSERT INTO products(name,category,brand,cost_price,selling_price,stock,reorder_level)
                                   VALUES(?,?,?,?,?,?,?)""",
                                (name.strip(), category, brand.strip() or "Other", cost, price, int(stock), int(reorder)))
                        st.success(f"{name} added.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("A product with that name already exists.")
    products = read_df("SELECT * FROM products ORDER BY name")
    if not products.empty:
        low_only = st.toggle("Show only low-stock products", value=False)
        view = products[products["stock"] <= products["reorder_level"]] if low_only else products
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.download_button("Download inventory CSV", products.to_csv(index=False).encode("utf-8"),
                           file_name="products_inventory.csv", mime="text/csv")
        st.markdown("#### Adjust stock")
        names = products["name"].tolist()
        selected_name = st.selectbox("Product to adjust", names, key="adjust_product")
        selected = products[products["name"] == selected_name].iloc[0]
        with st.form("adjust_stock_form"):
            st.caption(f"Current stock: {int(selected['stock'])}")
            change = st.number_input("Quantity to add (use negative number to remove)", value=0, step=1)
            go = st.form_submit_button("Update stock")
            if go:
                new_stock = int(selected["stock"]) + int(change)
                if new_stock < 0:
                    st.error("Stock cannot become negative.")
                else:
                    run_sql("UPDATE products SET stock=? WHERE id=?", (new_stock, int(selected["id"])))
                    st.success("Stock updated.")
                    st.rerun()
    else:
        st.info("No products yet. Add your first product above.")


# ---------------------------- Record Sale -----------------------------------
elif page == "Record Sale":
    st.subheader("Record a Sale")
    products = read_df("SELECT * FROM products WHERE stock > 0 ORDER BY name")
    if products.empty:
        st.warning("No products are currently in stock. Add products or record a purchase first.")
    else:
        with st.form("sale_form", clear_on_submit=True):
            names = products["name"].tolist()
            product_name = st.selectbox("Product", names)
            product = products[products["name"] == product_name].iloc[0]
            st.caption(f"Available stock: {int(product['stock'])} | Selling price: {fmt(product['selling_price'])} | Cost price: {fmt(product['cost_price'])}")
            a, b, c = st.columns(3)
            qty = a.number_input("Quantity", min_value=1, max_value=int(product["stock"]), value=1, step=1)
            discount = b.number_input("Total discount ₹", min_value=0.0, value=0.0, step=50.0)
            customer = c.text_input("Customer name (optional)")
            submit = st.form_submit_button("Save sale", type="primary")
            if submit:
                total = int(qty) * float(product["selling_price"])
                if discount > total:
                    st.error("Discount cannot exceed sale total.")
                else:
                    with connect() as conn:
                        conn.execute("""INSERT INTO sales(sold_at,product_id,product_name,quantity,unit_price,unit_cost,discount,customer)
                                        VALUES(?,?,?,?,?,?,?,?)""",
                                     (date.today().isoformat(), int(product["id"]), product_name, int(qty),
                                      float(product["selling_price"]), float(product["cost_price"]), float(discount), customer.strip()))
                        conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (int(qty), int(product["id"])))
                        conn.commit()
                    st.success(f"Sale saved. Sale value: {fmt(total-discount)}")
                    st.rerun()
    st.markdown("#### Recent sales")
    recent = read_df("SELECT id,sold_at,product_name,quantity,unit_price,discount,customer FROM sales ORDER BY id DESC LIMIT 100")
    st.dataframe(recent, use_container_width=True, hide_index=True)


# ---------------------------- Record Purchase -------------------------------
elif page == "Record Purchase":
    st.subheader("Record Stock Purchase")
    products = read_df("SELECT * FROM products ORDER BY name")
    if products.empty:
        st.warning("Add a product before recording a purchase.")
    else:
        with st.form("purchase_form", clear_on_submit=True):
            product_name = st.selectbox("Product", products["name"].tolist())
            product = products[products["name"] == product_name].iloc[0]
            a, b, c = st.columns(3)
            qty = a.number_input("Quantity purchased", min_value=1, value=1, step=1)
            unit_cost = b.number_input("Cost per unit ₹", min_value=0.0, value=float(product["cost_price"]), step=100.0)
            supplier = c.text_input("Supplier", value="")
            submit = st.form_submit_button("Save purchase", type="primary")
            if submit:
                with connect() as conn:
                    conn.execute("""INSERT INTO purchases(purchased_at,product_id,product_name,quantity,unit_cost,supplier)
                                    VALUES(?,?,?,?,?,?)""",
                                 (date.today().isoformat(), int(product["id"]), product_name, int(qty), float(unit_cost), supplier.strip()))
                    conn.execute("UPDATE products SET stock=stock+?, cost_price=? WHERE id=?",
                                 (int(qty), float(unit_cost), int(product["id"])))
                    conn.commit()
                st.success(f"Purchase saved. Stock increased by {int(qty)}.")
                st.rerun()
    purchases = read_df("SELECT * FROM purchases ORDER BY id DESC LIMIT 100")
    st.markdown("#### Recent purchases")
    st.dataframe(purchases, use_container_width=True, hide_index=True)


# ---------------------------- Expenses --------------------------------------
elif page == "Expenses":
    st.subheader("Shop Expenses")
    with st.form("expense_form", clear_on_submit=True):
        a, b = st.columns(2)
        category = a.selectbox("Expense category", ["Rent", "Electricity", "Salary", "Internet", "Transport", "Marketing", "Repairs", "Packaging", "Other"])
        amount = b.number_input("Amount ₹", min_value=0.01, value=1000.0, step=100.0)
        note = st.text_input("Description / note")
        submit = st.form_submit_button("Add expense", type="primary")
        if submit:
            run_sql("INSERT INTO expenses(spent_at,category,amount,note) VALUES(?,?,?,?)",
                    (date.today().isoformat(), category, float(amount), note.strip()))
            st.success("Expense recorded.")
            st.rerun()
    expenses = read_df("SELECT * FROM expenses ORDER BY spent_at DESC")
    if not expenses.empty:
        st.metric("Total recorded expenses", fmt(expenses["amount"].sum()))
        st.dataframe(expenses, use_container_width=True, hide_index=True)
        bycat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(8, 3.5))
        fig.patch.set_facecolor("#102438")
        ax.bar(bycat.index, bycat.values, color="#ff9f43")
        ax.set_ylabel("Amount ₹")
        add_chart_theme(ax)
        ax.tick_params(axis="x", rotation=20)
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        st.download_button("Download expenses CSV", expenses.to_csv(index=False).encode("utf-8"),
                           file_name="shop_expenses.csv", mime="text/csv")
    else:
        st.info("No expenses recorded yet.")


# ---------------------------- Reports & Export ------------------------------
elif page == "Reports & Export":
    st.subheader("Reports & Business Insights")
    sales, purchases, expenses, products, revenue, cogs, gross, expense_total, net, purchase_total, margin = metrics()
    a, b, c, d = st.columns(4)
    a.metric("Revenue after discounts", fmt(revenue))
    b.metric("Cost of goods sold", fmt(cogs))
    c.metric("Gross profit", fmt(gross))
    d.metric("Estimated net profit", fmt(net))
    st.caption("Estimated net profit = sales revenue after discounts − cost of goods sold − recorded operating expenses.")
    st.markdown("#### Top products")
    if not sales.empty:
        s = sales.copy()
        s["revenue"] = s["quantity"] * s["unit_price"] - s["discount"]
        s["gross_profit"] = s["revenue"] - s["quantity"] * s["unit_cost"]
        top = s.groupby("product_name").agg(
            units_sold=("quantity", "sum"),
            revenue=("revenue", "sum"),
            gross_profit=("gross_profit", "sum")
        ).sort_values("units_sold", ascending=False).reset_index()
        st.dataframe(top, use_container_width=True, hide_index=True)
        st.download_button("Download sales analysis CSV", top.to_csv(index=False).encode("utf-8"),
                           file_name="sales_analysis.csv", mime="text/csv")
    else:
        st.info("No sales records available yet.")
    st.markdown("#### Purchase recommendations")
    if not products.empty:
        sales_units = sales.groupby("product_id")["quantity"].sum().to_dict() if not sales.empty else {}
        rec = products.copy()
        rec["units sold (all-time)"] = rec["id"].map(sales_units).fillna(0).astype(int)
        rec["suggested order"] = (rec["reorder_level"] * 2 - rec["stock"]).clip(lower=0).astype(int)
        rec["status"] = np.where(rec["stock"] <= rec["reorder_level"], "REORDER", "OK")
        rec = rec.sort_values(["status", "units sold (all-time)"], ascending=[True, False])
        st.dataframe(rec[["name", "category", "brand", "stock", "reorder_level",
                          "units sold (all-time)", "suggested order", "status"]],
                     use_container_width=True, hide_index=True)
        st.download_button("Download purchase recommendations CSV", rec.to_csv(index=False).encode("utf-8"),
                           file_name="purchase_recommendations.csv", mime="text/csv")
    st.markdown("#### Export raw records")
    for label, df, filename in [
        ("Sales", sales, "sales.csv"),
        ("Purchases", purchases, "purchases.csv"),
        ("Products", products, "products.csv"),
        ("Expenses", expenses, "expenses.csv"),
    ]:
        st.download_button(f"Download {label} CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name=filename, mime="text/csv", key=f"export_{filename}")
    st.warning("For reliable accounting, record every sale, purchase, discount and expense. Tax, returns, credit notes and payment fees are not modeled automatically.")
