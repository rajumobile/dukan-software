import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import urllib.parse

st.set_page_config(page_title="दुकान व्यापार एवं ऑनलाइन स्टोर", page_icon="🛍️", layout="wide")

DB_NAME = "shop.db"

# --- डेटाबेस ऑटो-सेटअप ---
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
            category TEXT DEFAULT 'General',
            buy_price REAL NOT NULL,
            sell_price REAL NOT NULL,
            stock INTEGER NOT NULL,
            min_alert INTEGER DEFAULT 3,
            description TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            is_online INTEGER DEFAULT 1
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

    # ऑटो कॉलम अपग्रेड
    def add_col(tbl, col, typ):
        try:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass

    add_col("products", "category", "TEXT DEFAULT 'General'")
    add_col("products", "description", "TEXT DEFAULT ''")
    add_col("products", "image_url", "TEXT DEFAULT ''")
    add_col("products", "is_online", "INTEGER DEFAULT 1")
    add_col("sales", "bill_no", "TEXT")
    add_col("sales", "sold_by", "TEXT")
    add_col("sales", "customer_name", "TEXT")
    add_col("sales", "customer_phone", "TEXT")
    add_col("sales", "payment_mode", "TEXT")
    add_col("sales", "due_date", "TEXT")

    conn.commit()
    conn.close()

init_db()

# --- सेशन्स ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.username = ""
if "billing_cart" not in st.session_state:
    st.session_state.billing_cart = []
if "online_cart" not in st.session_state:
    st.session_state.online_cart = []
if "last_bill" not in st.session_state:
    st.session_state.last_bill = None

# --- साइडबार नेविगेशन ---
st.sidebar.markdown("## 🏬 व्यापार पोर्टल")

if not st.session_state.logged_in:
    mode = st.sidebar.radio("मोड चुनें:", ["🛍️ ऑनलाइन स्टोर (Customer View)", "🔐 स्टाफ लॉगिन"])
else:
    st.sidebar.markdown(f"**लॉगिन:** `{st.session_state.username.upper()}` ({st.session_state.role.upper()})")
    if st.sidebar.button("🚪 लॉगआउट", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.billing_cart = []
        st.session_state.last_bill = None
        st.rerun()
    
    admin_menu = ["💰 मल्टी-आइटम बिलिंग", "➕ नया स्टॉक / प्रोडक्ट जोड़ें", "📦 स्टॉक व ऑनलाइन शो", "📒 उधारी/खाता अलर्ट", "📊 एडमिन डैशबोर्ड", "👥 ऑपरेटर मैनेजमेंट", "🛍️ ऑनलाइन स्टोर देखें"]
    operator_menu = ["💰 मल्टी-आइटम बिलिंग", "📦 स्टॉक स्थिति", "📒 उधारी/खाता अलर्ट", "🛍️ ऑनलाइन स्टोर देखें"]
    
    menu_options = admin_menu if st.session_state.role == "admin" else operator_menu
    mode = st.sidebar.radio("मेन्यू चुनें:", menu_options)

# ==========================================
# 1. पब्लिक ऑनलाइन स्टोर (Customer Catalog + WhatsApp Order)
# ==========================================
if mode in ["🛍️ ऑनलाइन स्टोर (Customer View)", "🛍️ ऑनलाइन स्टोर देखें"]:
    st.title("🛍️ डिजिटल प्रोडक्ट कैटलॉग एवं ऑनलाइन ऑर्डर")
    st.caption("सीधे सामान चुनें और व्हाट्सएप पर ऑर्डर भेजें")

    conn = sqlite3.connect(DB_NAME)
    online_prods = pd.read_sql_query("SELECT id, name, category, sell_price, stock, description, image_url FROM products WHERE is_online=1 AND stock > 0", conn)
    conn.close()

    col_s1, col_s2 = st.columns([3, 1])
    search_query = col_s1.text_input("🔍 सामान खोजें (Product Search)", placeholder="सामान का नाम लिखें...")
    
    categories = ["सभी (All)"] + (online_prods["category"].dropna().unique().tolist() if not online_prods.empty else [])
    selected_cat = col_s2.selectbox("कैटेगरी फ़िल्टर", categories)

    filtered_prods = online_prods.copy()
    if not filtered_prods.empty:
        if search_query.strip():
            filtered_prods = filtered_prods[filtered_prods["name"].str.contains(search_query, case=False, na=False)]
        if selected_cat != "सभी (All)":
            filtered_prods = filtered_prods[filtered_prods["category"] == selected_cat]

    st.divider()

    # प्रोडक्ट कार्ड्स ग्रिड
    if not filtered_prods.empty:
        grid_cols = st.columns(3)
        for i, row in filtered_prods.reset_index().iterrows():
            with grid_cols[i % 3]:
                with st.container(border=True):
                    if row["image_url"] and str(row["image_url"]).strip().startswith("http"):
                        st.image(row["image_url"], use_container_width=True)
                    else:
                        st.markdown("📦 **[फोटो उपलब्ध नहीं]**")
                    
                    st.subheader(row["name"])
                    st.markdown(f"**कीमत:** <span style='font-size:18px; color:green;'>₹{row['sell_price']:.2f}</span>", unsafe_allow_html=True)
                    if row["description"]:
                        st.caption(row["description"])
                    st.write(f"उपलब्ध: `{row['stock']}` पीस")

                    if st.button(f"🛒 कार्ट में जोड़ें", key=f"add_online_{row['id']}", use_container_width=True):
                        st.session_state.online_cart.append({
                            "id": int(row["id"]),
                            "name": row["name"],
                            "price": float(row["sell_price"])
                        })
                        st.success(f"{row['name']} जोड़ा गया!")
                        st.rerun()
    else:
        st.info("फिलहाल ऑनलाइन स्टोर में कोई प्रोडक्ट उपलब्ध नहीं है।")

    # कस्टमर ऑनलाइन कार्ट व व्हाट्सएप ऑर्डर
    if st.session_state.online_cart:
        st.divider()
        st.subheader("🛒 आपका ऑनलाइन कार्ट (Your Order)")
        
        cart_summary = pd.DataFrame(st.session_state.online_cart).groupby(["id", "name", "price"]).size().reset_index(name="qty")
        cart_summary["total"] = cart_summary["price"] * cart_summary["qty"]
        
        st.dataframe(cart_summary[["name", "qty", "price", "total"]].rename(columns={"name": "सामान", "qty": "मात्रा", "price": "दर (₹)", "total": "कुल (₹)"}), use_container_width=True)
        
        grand_total = cart_summary["total"].sum()
        st.markdown(f"### कुल ऑर्डर राशि: **₹{grand_total:.2f}**")

        c_o1, c_o2 = st.columns(2)
        cust_cname = c_o1.text_input("आपका नाम (Customer Name)", placeholder="उदा. रमेश कुमार")
        cust_cphone = c_o2.text_input("आपका व्हाट्सएप नंबर (Mobile No.)", placeholder="उदा. 98XXXXXXXX")
        cust_caddr = st.text_area("डिलीवरी का पता / नोट (Delivery Address)", placeholder="गाँव/शहर, पिनकोड...")

        # व्हाट्सएप मैसेज बनाना
        order_lines = [f"- {r['name']} x {r['qty']} = Rs {r['total']:.2f}" for _, r in cart_summary.iterrows()]
        order_text = (
            f"नमस्ते, मुझे आपकी दुकान से यह सामान ऑर्डर करना है:\n\n"
            f"*ऑर्डर विवरण:*\n" + "\n".join(order_lines) +
            f"\n\n*कुल राशि:* Rs {grand_total:.2f}\n"
            f"*ग्राहक का नाम:* {cust_cname}\n"
            f"*मोबाइल:* {cust_cphone}\n"
            f"*पता:* {cust_caddr}"
        )
        
        # अपना व्हाट्सएप नंबर यहाँ सेट करें
        SHOP_WHATSAPP_NUMBER = "918349596263"
        wa_url = f"https://wa.me/{SHOP_WHATSAPP_NUMBER}?text={urllib.parse.quote(order_text)}"

        c_wa1, c_wa2 = st.columns([2, 1])
        with c_wa1:
            st.link_button("📲 सीधे व्हाट्सएप पर ऑर्डर भेजें (Send Order on WhatsApp)", wa_url, type="primary", use_container_width=True)
        with c_wa2:
            if st.button("❌ कार्ट खाली करें", use_container_width=True):
                st.session_state.online_cart = []
                st.rerun()

# ==========================================
# 2. स्टाफ लॉगिन स्क्रीन
# ==========================================
elif mode == "🔐 स्टाफ लॉगिन":
    st.title("🔐 दुकान स्टाफ एवं एडमिन लॉगिन")
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

# ==========================================
# 3. नया स्टॉक / प्रोडक्ट जोड़ें (फोटो और ऑनलाइन टॉगल सहित)
# ==========================================
elif mode == "➕ नया स्टॉक / प्रोडक्ट जोड़ें":
    st.subheader("➕ नया सामान स्टॉक एवं ऑनलाइन स्टोर में जोड़ें")
    with st.form("add_item_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("सामान का नाम *")
        category = c2.text_input("कैटेगरी (जैसे: डेटा केबल, मोबाइल एक्सेसरीज, फोटो फ्रेम)", value="जनरल")
        
        buy_p = c1.number_input("खरीद लागत मूल्य (₹) *", min_value=0.0, step=1.0)
        sell_p = c2.number_input("बिक्री मूल्य (₹) *", min_value=0.0, step=1.0)
        
        stock = c1.number_input("स्टॉक मात्रा (Qty) *", min_value=1, step=1)
        alert = c2.number_input("कम स्टॉक अलर्ट सीमा", min_value=1, value=3)
        
        desc = st.text_input("सामान का विवरण / वारंटी नोट (जैसे: 6 माह की गारंटी)", value="")
        img_link = st.text_input("फोटो का ऑनलाइन लिंक (Image URL) [वैकल्पिक]", placeholder="https://example.com/photo.jpg")
        is_on = st.checkbox("🌐 इस सामान को ऑनलाइन स्टोर (Digital Catalog) पर दिखाएं", value=True)

        if st.form_submit_button("💾 स्टॉक में सेव करें", use_container_width=True):
            if name.strip():
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO products (name, category, buy_price, sell_price, stock, min_alert, description, image_url, is_online)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name.strip(), category.strip(), buy_p, sell_p, stock, alert, desc.strip(), img_link.strip(), 1 if is_on else 0))
                conn.commit()
                conn.close()
                st.success(f"'{name}' स्टॉक और ऑनलाइन कैटलॉग में जुड़ गया!")
            else:
                st.warning("कृपया सामान का नाम दर्ज करें!")

# ==========================================
# 4. मल्टी-आइटम बिलिंग काउंटर
# ==========================================
elif mode == "💰 मल्टी-आइटम बिलिंग":
    st.subheader("🛒 काउंटर बिलिंग (Multi-Item Billing)")
    
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

        already_in_cart = sum(item["qty"] for item in st.session_state.billing_cart if item["id"] == int(item_data["id"]))
        avail_stock = int(item_data["stock"]) - already_in_cart

        col1, col2, col3 = st.columns([2, 2, 2])
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
                    st.session_state.billing_cart.append({
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
        st.warning("दुकान में कोई सामान स्टॉक में नहीं है!")

    if st.session_state.billing_cart:
        st.markdown("---")
        st.markdown("#### 📋 चालू बिल लिस्ट")
        cart_df = pd.DataFrame(st.session_state.billing_cart)[["name", "qty", "rate", "total"]]
        cart_df.columns = ["सामान", "मात्रा", "दर (₹)", "कुल (₹)"]
        st.dataframe(cart_df, use_container_width=True)

        total_bill_amount = sum(item["total"] for item in st.session_state.billing_cart)
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

                    for item in st.session_state.billing_cart:
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
                        "items": list(st.session_state.billing_cart),
                        "total": total_bill_amount,
                        "sold_by": st.session_state.username
                    }
                    st.session_state.billing_cart = []
                    st.success("बिल सफलतापूर्वक कट गया!")
                    st.rerun()

        with col_b2:
            if st.button("❌ लिस्ट खाली करें", use_container_width=True):
                st.session_state.billing_cart = []
                st.rerun()

   # रसीद प्रिंट
    if st.session_state.last_bill:
        b = st.session_state.last_bill
        st.divider()
        st.subheader("🧾 बिल इनवॉइस / रसीद")

        rows_html = "".join([f"<tr><td>{it['name']}</td><td>{it['qty']}</td><td>₹{it['rate']:.2f}</td><td>₹{it['total']:.2f}</td></tr>" for it in b["items"]])

        due_txt = f"<b>उधारी देय तिथि:</b> {b['due_date']}<br/>" if b.get('due_date') and b['due_date'] != 'N/A' else ""
        phone_txt = b['phone'] if b.get('phone') else 'N/A'

        bill_html = f"""
        <div id="printArea" style="border: 1px solid #000; padding: 15px; width: 340px; font-family: monospace; background: #fff; color: #000; margin: auto;">
            <h3 style="text-align:center; margin:0;">दुकान बिक्री रसीद</h3>
            <p style="text-align:center; margin:2px 0 10px 0; font-size:12px;">धन्यवाद! पुनः पधारें</p>
            <hr style="border-top: 1px dashed #000;"/>
            <div style="font-size: 13px;">
                <b>बिल नं:</b> {b['bill_no']}<br/>
                <b>तारीख:</b> {b['date']}<br/>
                <b>ग्राहक:</b> {b['customer']}<br/>
                <b>मोबाइल:</b> {phone_txt}<br/>
                <b>भुगतान:</b> {b['payment_mode']}<br/>
                {due_txt}
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
        <html><body>
        <button onclick="printBill()" style="background-color:#2ed573; color:white; padding:10px 20px; font-size:15px; font-weight:bold; border:none; border-radius:5px; cursor:pointer; width:100%;">🖨️ यह बिल प्रिंट करें (Print / Save PDF)</button>
        <script>
        function printBill() {{
            var win = window.open('', '', 'height=600,width=450');
            win.document.write('<html><head><title>Print Bill</title></head><body style="margin:20px;">');
            win.document.write(`{bill_html}`);
            win.document.write('</body></html>');
            win.document.close();
            win.focus();
            setTimeout(function() {{ win.print(); win.close(); }}, 400);
        }}
        </script>
        </body></html>
        """
        st.components.v1.html(print_script, height=60)