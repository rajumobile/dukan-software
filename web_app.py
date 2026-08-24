import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date

st.set_page_config(page_title="दुकान व्यापार डैशबोर्ड", page_icon="🏬", layout="wide")

DB_NAME = "shop.db"

# --- डेटाबेस ऑटो-रिपेयर व सेटअप ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('operator', 'op123', 'operator')")
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            buy_price REAL NOT NULL,
            sell_price REAL NOT NULL,
            stock INTEGER NOT NULL,
            min_alert INTEGER DEFAULT 3
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            sell_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            profit REAL NOT NULL,
            sold_by TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            payment_mode TEXT,
            due_date TEXT,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS udhar_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            total_amount REAL NOT NULL,
            paid_amount REAL DEFAULT 0,
            due_date TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # पुराने कॉलम ऑटो-चेक
    def add_col(tbl, col, typ):
        try:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass

    add_col("sales", "bill_no", "TEXT")
    add_col("sales", "sold_by", "TEXT")
    add_col("sales", "customer_name", "TEXT")
    add_col("sales", "customer_phone", "TEXT")
    add_col("sales", "payment_mode", "TEXT")
    add_col("sales", "due_date", "TEXT")

    conn.commit()
    conn.close()

init_db()

# --- सेशन स्टेट इनिशियलाइज़ेशन ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.username = ""
if "cart" not in st.session_state:
    st.session_state.cart = []
if "last_bill" not in st.session_state:
    st.session_state.last_bill = None

# --- लॉगिन स्क्रीन ---
def login_screen():
    st.title("🏬 दुकान व्यापार पोर्टल - लॉगिन")
    col1, col2 = st.columns([1, 2])
    with col1:
        u = st.text_input("यूज़रनेम (Username)")
        p = st.text_input("पासवर्ड (Password)", type="password")
        if st.button("लॉगिन करें", use_container_width=True):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (u.strip(), p.strip()))
            user = cursor.fetchone()
            conn.close()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = u.strip()
                st.session_state.role = user[0]
                st.rerun()
            else:
                st.error("गलत यूज़रनेम या पासवर्ड!")

if not st.session_state.logged_in:
    login_screen()
    st.stop()

# --- साइडबार ---
st.sidebar.title(f"👤 {st.session_state.username.upper()} ({st.session_state.role.upper()})")
if st.sidebar.button("लॉगआउट"):
    st.session_state.logged_in = False
    st.session_state.cart = []
    st.session_state.last_bill = None
    st.rerun()

menu = ["💰 मल्टी-आइटम बिलिंग", "📒 उधारी/खाता अलर्ट", "📦 स्टॉक स्थिति"]
if st.session_state.role == "admin":
    menu = ["📊 एडमिन डैशबोर्ड (चार्ट्स)", "➕ नया स्टॉक जोड़ें", "💰 मल्टी-आइटम बिलिंग", "📒 उधारी/खाता अलर्ट", "📦 स्टॉक स्थिति", "👥 ऑपरेटर मैनेजमेंट"]

choice = st.sidebar.radio("मेन्यू चुनें", menu)

# --- 1. एडमिन डैशबोर्ड ---
if choice == "📊 एडमिन डैशबोर्ड (चार्ट्स)":
    st.title("📈 बिज़नेस परफॉरमेंस व एनालिटिक्स")
    conn = sqlite3.connect(DB_NAME)
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    udhar_df = pd.read_sql_query("SELECT * FROM udhar_ledger WHERE status='PENDING'", conn)
    conn.close()

    if not sales_df.empty:
        sales_df["sale_date"] = pd.to_datetime(sales_df["sale_date"])
        now = datetime.now()

        today_sales = sales_df[sales_df["sale_date"].dt.date == now.date()]
        yesterday_sales = sales_df[sales_df["sale_date"].dt.date == (now - timedelta(days=1)).date()]
        week_sales = sales_df[sales_df["sale_date"] >= (now - timedelta(days=7))]
        month_sales = sales_df[sales_df["sale_date"] >= (now - timedelta(days=30))]
        year_sales = sales_df[sales_df["sale_date"] >= (now - timedelta(days=365))]

        pending_udhar_total = (udhar_df['total_amount'] - udhar_df['paid_amount']).sum() if not udhar_df.empty else 0.0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("आज का मुनाफ़ा", f"₹{today_sales['profit'].sum():.2f}", f"बिक्री: ₹{today_sales['total_amount'].sum():.2f}")
        c2.metric("कल का मुनाफ़ा", f"₹{yesterday_sales['profit'].sum():.2f}", f"बिक्री: ₹{yesterday_sales['total_amount'].sum():.2f}")
        c3.metric("7 दिन का मुनाफ़ा", f"₹{week_sales['profit'].sum():.2f}", f"बिक्री: ₹{week_sales['total_amount'].sum():.2f}")
        c4.metric("30 दिन का मुनाफ़ा", f"₹{month_sales['profit'].sum():.2f}", f"बिक्री: ₹{month_sales['total_amount'].sum():.2f}")
        c5.metric("मार्केट में कुल उधारी", f"₹{pending_udhar_total:.2f}", "बकाया वसूली")

        st.divider()
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("🔥 सबसे ज़्यादा बिकने वाले सामान")
            top_items = sales_df.groupby("product_name")["quantity"].sum().reset_index()
            fig1 = px.bar(top_items.sort_values(by="quantity", ascending=False).head(10), x="product_name", y="quantity", color="quantity", labels={"product_name": "सामान", "quantity": "मात्रा"})
            st.plotly_chart(fig1, use_container_width=True)

        with col_right:
            st.subheader("⚠️ न बिकने वाला स्टॉक (Dead Stock)")
            sold_ids = sales_df["product_id"].unique()
            dead_stock = products_df[~products_df["id"].isin(sold_ids)]
            if not dead_stock.empty:
                st.dataframe(dead_stock[["name", "stock", "buy_price"]].rename(columns={"name": "सामान", "stock": "उपलब्ध स्टॉक", "buy_price": "लागत मूल्य"}), use_container_width=True)
            else:
                st.success("सभी सामान की बिक्री नियमित चल रही है!")
    else:
        st.info("अभी कोई बिक्री डेटा उपलब्ध नहीं है।")

# --- 2. नया स्टॉक जोड़ें ---
elif choice == "➕ नया स्टॉक जोड़ें":
    st.subheader("➕ नया सामान स्टॉक में जोड़ें")
    with st.form("add_item_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("सामान का नाम")
        buy_p = c2.number_input("खरीद मूल्य (₹)", min_value=0.0, step=1.0)
        sell_p = c1.number_input("तय बिक्री मूल्य (₹)", min_value=0.0, step=1.0)
        stock = c2.number_input("मात्रा (Stock Qty)", min_value=1, step=1)
        alert = c1.number_input("कम स्टॉक अलर्ट सीमा", min_value=1, value=3)
        
        if st.form_submit_button("स्टॉक में सेव करें"):
            if name.strip():
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO products (name, buy_price, sell_price, stock, min_alert) VALUES (?, ?, ?, ?, ?)", (name.strip(), buy_p, sell_p, stock, alert))
                conn.commit()
                conn.close()
                st.success(f"'{name}' स्टॉक में जुड़ गया!")
            else:
                st.warning("सामान का नाम दर्ज करें!")

# --- 3. मल्टी-आइटम बिलिंग काउंटर ---
elif choice == "💰 मल्टी-आइटम बिलिंग":
    st.subheader("🛒 ग्राहक बिलिंग काउंटर (Multi-Item Billing)")
    
    conn = sqlite3.connect(DB_NAME)
    prods = pd.read_sql_query("SELECT id, name, sell_price, stock, buy_price FROM products WHERE stock > 0", conn)
    conn.close()

    col_c1, col_c2 = st.columns(2)
    cust_name = col_c1.text_input("ग्राहक का नाम", value="नकद ग्राहक")
    cust_phone = col_c2.text_input("ग्राहक का मोबाइल नंबर", value="")

    st.markdown("---")
    st.markdown("#### ➕ बिल में सामान जोड़ें")
    
    if not prods.empty:
        prod_names = prods["name"].tolist()
        selected_prod = st.selectbox("सामान चुनें", prod_names)
        item_data = prods[prods["name"] == selected_prod].iloc[0]

        # कार्ट में पहले से जुड़े स्टॉक की गणना
        already_in_cart = sum(item["qty"] for item in st.session_state.cart if item["id"] == int(item_data["id"]))
        avail_stock = int(item_data["stock"]) - already_in_cart

        col1, col2, col3 = st.columns([2, 2, 2])
        
        # सुरक्षित स्टॉक इनपुट (ताकि एरर न आए)
        max_allowed = max(1, avail_stock)
        qty = col1.number_input("मात्रा", min_value=1, max_value=max_allowed, value=1, disabled=(avail_stock <= 0))
        rate = col2.number_input("बिक्री रेट (₹)", min_value=0.0, value=float(item_data["sell_price"]))
        
        with col3:
            st.write(f"दुकान में शेष: **{max(0, avail_stock)}** पीस")
            if st.button("➕ लिस्ट में जोड़ें", use_container_width=True, disabled=(avail_stock <= 0)):
                if avail_stock < qty:
                    st.error("स्टॉक पर्याप्त नहीं है!")
                elif rate < float(item_data["buy_price"]) and st.session_state.role != "admin":
                    st.error("⚠️ खरीद मूल्य से कम पर बेचने के लिए एडमिन अनुमति चाहिए!")
                else:
                    st.session_state.cart.append({
                        "id": int(item_data["id"]),
                        "name": str(selected_prod),
                        "qty": int(qty),
                        "rate": float(rate),
                        "buy_price": float(item_data["buy_price"]),
                        "total": float(rate * qty),
                        "profit": float((rate - item_data["buy_price"]) * qty)
                    })
                    st.rerun()
    else:
        st.warning("दुकान में कोई सामान स्टॉक में नहीं है! कृपया पहले नया स्टॉक जोड़ें।")

    # कार्ट लिस्ट तालिका
    if st.session_state.cart:
        st.markdown("---")
        st.markdown("#### 📋 चालू बिल लिस्ट")
        cart_df = pd.DataFrame(st.session_state.cart)[["name", "qty", "rate", "total"]]
        cart_df.columns = ["सामान", "मात्रा", "दर (₹)", "कुल (₹)"]
        st.dataframe(cart_df, use_container_width=True)

        total_bill_amount = sum(item["total"] for item in st.session_state.cart)
        st.markdown(f"### 💵 कुल बिल राशि: **₹{total_bill_amount:.2f}**")

        c_pay1, c_pay2 = st.columns(2)
        payment_mode = c_pay1.selectbox("💳 भुगतान का तरीका (Payment Mode)", ["नकद (Cash)", "ऑनलाइन (UPI / Scanner)", "उधारी (Credit / Udhar)"])
        
        due_date_val = None
        if payment_mode == "उधारी (Credit / Udhar)":
            due_date_val = c_pay2.date_input("📅 उधारी चुकाने की अंतिम तारीख (Due Date)", min_value=date.today(), value=date.today() + timedelta(days=7))

        col_b1, col_b2 = st.columns([2, 1])
        with col_b1:
            if st.button("✅ फाइनल बिल काटें और स्टॉक घटाएं", type="primary", use_container_width=True):
                if payment_mode == "उधारी (Credit / Udhar)" and (not cust_name.strip() or cust_name.strip() == "नकद ग्राहक"):
                    st.error("उधारी बिल के लिए कृपया ग्राहक का सही नाम दर्ज करें!")
                else:
                    bill_no = "BILL-" + datetime.now().strftime("%Y%m%d%H%M%S")
                    now_str = datetime.now().strftime("%d-%m-%Y %I:%M %p")
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()

                    for item in st.session_state.cart:
                        cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (int(item["qty"]), int(item["id"])))
                        cursor.execute("""
                            INSERT INTO sales (bill_no, product_id, product_name, quantity, sell_price, total_amount, profit, sold_by, customer_name, customer_phone, payment_mode, due_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (bill_no, int(item["id"]), item["name"], int(item["qty"]), float(item["rate"]), float(item["total"]), float(item["profit"]), str(st.session_state.username), str(cust_name), str(cust_phone), str(payment_mode), str(due_date_val) if due_date_val else ""))

                    if payment_mode == "उधारी (Credit / Udhar)":
                        cursor.execute("""
                            INSERT INTO udhar_ledger (bill_no, customer_name, customer_phone, total_amount, paid_amount, due_date, status)
                            VALUES (?, ?, ?, ?, 0, ?, 'PENDING')
                        """, (bill_no, str(cust_name), str(cust_phone), float(total_bill_amount), str(due_date_val)))

                    conn.commit()
                    conn.close()

                    st.session_state.last_bill = {
                        "bill_no": bill_no,
                        "date": now_str,
                        "customer": cust_name,
                        "phone": cust_phone,
                        "payment_mode": payment_mode,
                        "due_date": str(due_date_val) if due_date_val else "N/A",
                        "items": list(st.session_state.cart),
                        "total": total_bill_amount,
                        "sold_by": st.session_state.username
                    }
                    st.session_state.cart = []
                    st.success("बिल सफलतापूर्वक कट गया!")
                    st.rerun()

        with col_b2:
            if st.button("❌ लिस्ट खाली करें", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

    # --- रसीद प्रिंट सेक्शन ---
    if st.session_state.last_bill:
        b = st.session_state.last_bill
        st.divider()
        st.subheader("🧾 बिल इनवॉइस / रसीद")

        rows_html = "".join([f"<tr><td>{it['name']}</td><td>{it['qty']}</td><td>₹{it['rate']:.2f}</td><td>₹{it['total']:.2f}</td></tr>" for it in b["items"]])

        bill_html = f"""
        <div id="printArea" style="border: 1px solid #000; padding: 15px; width: 340px; font-family: monospace; background: #fff; color: #000; margin: auto;">
            <h3 style="text-align:center; margin:0;">दुकान बिक्री रसीद</h3>
            <p style="text-align:center; margin:2px 0 10px 0; font-size:12px;">धन्यवाद! पुनः पधारें</p>
            <hr style="border-top: 1px dashed #000;"/>
            <div style="font-size: 13px;">
                <b>बिल नं:</b> {b['bill_no']}<br/>
                <b>तारीख:</b> {b['date']}<br/>
                <b>ग्राहक:</b> {b['customer']}<br/>
                <b>मोबाइल:</b> {b['phone'] if b['phone'] else 'N/A'}<br/>
                <b>भुगतान:</b> {b['payment_mode']}<br/>
                {"<b>उधारी देय तिथि:</b> " + b['due_date'] + "<br/>" if b['due_date'] != 'N/A' else ""}
                <b>कैशियर:</b> {b['sold_by']}
            </div>
            <hr style="border-top: 1px dashed #000;"/>
            <table style="width:100%; font-size:13px; text-align:left;">
                <tr><th>सामान</th><th>मात्रा</th><th>दर</th><th>कुल</th></tr>
                {rows_html}
            </table>
            <hr style="border-top: 1px dashed #000;"/>
            <h3 style="text-align:right; margin:5px 0;">कुल राशि: ₹{b['total']:.2f}</h3>
            <hr style="border-top: 1px dashed #000;"/>
            <p style="text-align:center; font-size:11px; margin:0;">कंप्यूटरीकृत रसीद | सॉफ्टवेयर जनरेटेड</p>
        </div>
        """

        st.components.v1.html(bill_html, height=380)

        print_script = f"""
        <html>
        <body>
        <button onclick="printBill()" style="background-color:#2ed573; color:white; padding:10px 20px; font-size:15px; font-weight:bold; border:none; border-radius:5px; cursor:pointer; width:100%;">🖨️ यह बिल प्रिंट करें (Print / Save PDF)</button>
        <script>
        function printBill() {{
            var win = window.open('', '', 'height=600,width=450');
            win.document.write('<html><head><title>Print Bill</title></head><body style="margin:20px;">');
            win.document.write(`{bill_html}`);
            win.document.write('</body></html>');
            win.document.close();
            win.focus();
            setTimeout(function() {{
                win.print();
                win.close();
            }}, 400);
        }}
        </script>
        </body>
        </html>
        """
        st.components.v1.html(print_script, height=60)

# --- 4. उधारी / खाता अलर्ट सेक्शन ---
elif choice == "📒 उधारी/खाता अलर्ट":
    st.subheader("📒 ग्राहक उधारी रजिस्टर एवं अलर्ट")
    conn = sqlite3.connect(DB_NAME)
    udhar_df = pd.read_sql_query("SELECT id, bill_no, customer_name, customer_phone, total_amount, paid_amount, due_date, status, created_at FROM udhar_ledger WHERE status='PENDING'", conn)
    
    if not udhar_df.empty:
        udhar_df["baki_amount"] = udhar_df["total_amount"] - udhar_df["paid_amount"]
        udhar_df["due_date_dt"] = pd.to_datetime(udhar_df["due_date"])
        today_dt = pd.to_datetime(date.today())

        overdue = udhar_df[udhar_df["due_date_dt"] < today_dt]
        today_due = udhar_df[udhar_df["due_date_dt"] == today_dt]

        if not overdue.empty:
            st.error(f"🚨 अलर्ट: {len(overdue)} ग्राहकों की उधारी चुकाने की अंतिम तारीख निकल चुकी है!")
        if not today_due.empty:
            st.warning(f"⚠️ ध्यान दें: {len(today_due)} ग्राहकों से आज उधारी वसूली की तारीख है!")

        st.markdown("#### 📋 सक्रिय उधारी लिस्ट")
        for idx, row in udhar_df.iterrows():
            c_u1, c_u2, c_u3, c_u4 = st.columns([3, 2, 2, 2])
            is_overdue = "🔴 तारीख निकल गई!" if row['due_date_dt'] < today_dt else "🟢 सक्रिय"
            c_u1.write(f"**{row['customer_name']}** ({row['customer_phone']})\n\nबिल: `{row['bill_no']}`")
            c_u2.write(f"बकाया: **₹{row['baki_amount']:.2f}** (कुल ₹{row['total_amount']:.2f})")
            c_u3.write(f"देय तारीख: **{row['due_date']}**\n\n{is_overdue}")
            
            with c_u4:
                if st.button(f"💰 पूरा भुगतान मिला", key=f"pay_{row['id']}"):
                    c = conn.cursor()
                    c.execute("UPDATE udhar_ledger SET paid_amount = total_amount, status = 'PAID' WHERE id = ?", (int(row['id']),))
                    conn.commit()
                    st.success(f"{row['customer_name']} का खाता चुकता हो गया!")
                    st.rerun()
            st.divider()
    else:
        st.success("दुकान में किसी ग्राहक की कोई उधारी बकाया नहीं है!")
    conn.close()

# --- 5. स्टॉक स्थिति ---
elif choice == "📦 स्टॉक स्थिति":
    st.subheader("📦 दुकान का लाइव स्टॉक")
    conn = sqlite3.connect(DB_NAME)
    if st.session_state.role == "admin":
        df = pd.read_sql_query("SELECT id, name, buy_price, sell_price, stock, min_alert FROM products", conn)
    else:
        df = pd.read_sql_query("SELECT id, name, sell_price, stock FROM products", conn)
    conn.close()

    search = st.text_input("🔍 सामान सर्च करें")
    if search:
        df = df[df["name"].str.contains(search, case=False, na=False)]

    st.datafram