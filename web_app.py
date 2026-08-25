import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import urllib.parse
import base64
import json
import random

st.set_page_config(page_title="Raju Bhaiya Online Store & Billing", page_icon="🏬", layout="wide")

DB_NAME = "shop.db"

ALL_PERMISSIONS = [
    "🛍️ ऑनलाइन स्टोर देखें",
    "💰 मल्टी-आइटम बिलिंग",
    "➕ नया स्टॉक / प्रोडक्ट जोड़ें",
    "📦 स्टॉक व ऑनलाइन शो",
    "📒 उधारी/खाता अलर्ट",
    "👔 ऑपरेटर बिक्री रिपोर्ट",
    "💵 ऑपरेटर मासिक कमीशन",
    "📊 एडमिन डैशबोर्ड",
    "👥 ऑपरेटर मैनेजमेंट",
    "🎨 स्टोर बैनर व सेटिंग्स"
]

# --- डेटाबेस ऑटो-सेटअप ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            phone TEXT DEFAULT '',
            commission_percent REAL DEFAULT 0,
            role TEXT,
            permissions TEXT DEFAULT '["🛍️ ऑनलाइन स्टोर देखें", "💰 मल्टी-आइटम बिलिंग", "📦 स्टॉक व ऑनलाइन शो"]'
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS shop_settings (
            id INTEGER PRIMARY KEY,
            shop_title TEXT DEFAULT 'Raju Bhaiya Online Store',
            shop_subtitle TEXT DEFAULT 'डिजिटल प्रोडक्ट कैटलॉग एवं ऑनलाइन ऑर्डर',
            shop_phone TEXT DEFAULT '8349596263',
            banner_image TEXT DEFAULT ''
        )
    """)
    c.execute("INSERT OR IGNORE INTO shop_settings (id, shop_title, shop_subtitle, shop_phone, banner_image) VALUES (1, 'Raju Bhaiya Online Store', 'डिजिटल प्रोडक्ट कैटलॉग एवं ऑनलाइन ऑर्डर', '8349596263', '')")

    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            buy_price REAL NOT NULL,
            sell_price REAL NOT NULL,
            gst_percent REAL DEFAULT 0,
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
            gst_percent REAL DEFAULT 0,
            gst_amount REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            profit REAL NOT NULL,
            operator_commission REAL DEFAULT 0,
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

    def add_col(tbl, col, typ):
        try:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass

    add_col("users", "phone", "TEXT DEFAULT ''")
    add_col("users", "commission_percent", "REAL DEFAULT 0")
    add_col("users", "permissions", "TEXT DEFAULT '[]'")
    add_col("shop_settings", "shop_phone", "TEXT DEFAULT '8349596263'")
    add_col("sales", "operator_commission", "REAL DEFAULT 0")
    add_col("products", "gst_percent", "REAL DEFAULT 0")
    add_col("products", "category", "TEXT DEFAULT 'General'")
    add_col("products", "description", "TEXT DEFAULT ''")
    add_col("products", "image_url", "TEXT DEFAULT ''")
    add_col("products", "is_online", "INTEGER DEFAULT 1")
    add_col("sales", "gst_percent", "REAL DEFAULT 0")
    add_col("sales", "gst_amount", "REAL DEFAULT 0")
    add_col("sales", "bill_no", "TEXT")
    add_col("sales", "sold_by", "TEXT")
    add_col("sales", "customer_name", "TEXT")
    add_col("sales", "customer_phone", "TEXT")
    add_col("sales", "payment_mode", "TEXT")
    add_col("sales", "due_date", "TEXT")

    admin_perms = json.dumps(ALL_PERMISSIONS)
    default_op_perms = json.dumps(["🛍️ ऑनलाइन स्टोर देखें", "💰 मल्टी-आइटम बिलिंग", "📦 स्टॉक व ऑनलाइन शो", "📒 उधारी/खाता अलर्ट"])

    c.execute("INSERT OR IGNORE INTO users (username, password, phone, commission_percent, role, permissions) VALUES ('admin', 'admin123', '8349596263', 0, 'admin', ?)", (admin_perms,))
    c.execute("INSERT OR IGNORE INTO users (username, password, phone, commission_percent, role, permissions) VALUES ('operator', 'op123', '', 5.0, 'operator', ?)", (default_op_perms,))

    conn.commit()
    conn.close()

init_db()

# --- सेशन्स ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.username = ""
    st.session_state.permissions = []
if "billing_cart" not in st.session_state:
    st.session_state.billing_cart = []
if "online_cart" not in st.session_state:
    st.session_state.online_cart = []
if "last_bill" not in st.session_state:
    st.session_state.last_bill = None
if "reset_stage" not in st.session_state:
    st.session_state.reset_stage = "enter_user"
if "generated_otp" not in st.session_state:
    st.session_state.generated_otp = None
if "reset_target_user" not in st.session_state:
    st.session_state.reset_target_user = None

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
        st.session_state.permissions = []
        st.rerun()
    
    if st.session_state.role == "admin":
        user_menu = ALL_PERMISSIONS
    else:
        user_menu = [p for p in st.session_state.permissions if p in ALL_PERMISSIONS]
        if "🛍️ ऑनलाइन स्टोर देखें" not in user_menu:
            user_menu.insert(0, "🛍️ ऑनलाइन स्टोर देखें")
        if not user_menu:
            user_menu = ["🛍️ ऑनलाइन स्टोर देखें", "💰 मल्टी-आइटम बिलिंग"]
    
    mode = st.sidebar.radio("मेन्यू चुनें:", user_menu)

# ==========================================
# 1. पब्लिक ऑनलाइन स्टोर / ऑनलाइन स्टोर देखें
# ==========================================
if mode in ["🛍️ ऑनलाइन स्टोर (Customer View)", "🛍️ ऑनलाइन स्टोर देखें"]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT shop_title, shop_subtitle, shop_phone, banner_image FROM shop_settings WHERE id=1")
    settings = c.fetchone()
    
    shop_title = settings[0] if settings else "Raju Bhaiya Online Store"
    shop_subtitle = settings[1] if settings else "डिजिटल प्रोडक्ट कैटलॉग एवं ऑनलाइन ऑर्डर"
    shop_phone = settings[2] if settings and settings[2] else "8349596263"
    banner_img = settings[3] if settings else ""
    
    online_prods = pd.read_sql_query("SELECT id, name, category, sell_price, gst_percent, stock, description, image_url FROM products WHERE is_online=1 AND stock > 0", conn)
    conn.close()

    h_col1, h_col2 = st.columns([1, 4])
    with h_col1:
        if banner_img and len(str(banner_img).strip()) > 5:
            st.image(banner_img, width=120)
        else:
            st.markdown("<div style='font-size: 70px; text-align: center;'>🏬</div>", unsafe_allow_html=True)
    with h_col2:
        st.markdown(f"<h1 style='margin-bottom:0px; color:#1E88E5;'>{shop_title}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='margin-top:2px; margin-bottom:5px; color:#2e7d32;'>📞 संपर्क सूत्र: +91 {shop_phone}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:15px; color:#555;'>{shop_subtitle}</p>", unsafe_allow_html=True)

    st.divider()

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

    if not filtered_prods.empty:
        grid_cols = st.columns(3)
        for i, row in filtered_prods.reset_index().iterrows():
            with grid_cols[i % 3]:
                with st.container(border=True):
                    if row["image_url"] and len(str(row["image_url"]).strip()) > 5:
                        st.image(row["image_url"], use_container_width=True)
                    else:
                        st.markdown("📦 **[फोटो उपलब्ध नहीं]**")
                    
                    st.subheader(row["name"])
                    st.markdown(f"**कीमत:** <span style='font-size:18px; color:green;'>₹{row['sell_price']:.2f}</span> <small>(GST {row['gst_percent']}%)</small>", unsafe_allow_html=True)
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

        order_lines = [f"- {r['name']} x {r['qty']} = Rs {r['total']:.2f}" for _, r in cart_summary.iterrows()]
        order_text = (
            f"नमस्ते, मुझे *{shop_title}* से यह सामान ऑर्डर करना है:\n\n"
            f"*ऑर्डर विवरण:*\n" + "\n".join(order_lines) +
            f"\n\n*कुल राशि:* Rs {grand_total:.2f}\n"
            f"*ग्राहक का नाम:* {cust_cname}\n"
            f"*मोबाइल:* {cust_cphone}\n"
            f"*पता:* {cust_caddr}"
        )
        
        wa_url = f"https://wa.me/91{shop_phone}?text={urllib.parse.quote(order_text)}"

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
    login_tab, forgot_tab = st.tabs(["🔑 लॉगिन करें", "🔄 पासवर्ड भूल गए? (Forgot Password)"])
    
    with login_tab:
        st.subheader("🔐 दुकान स्टाफ एवं एडमिन लॉगिन")
        col1, col2 = st.columns([1, 2])
        with col1:
            u = st.text_input("यूज़रनेम (Username)", key="main_username")
            p = st.text_input("पासवर्ड (Password)", type="password", key="main_password")
            if st.button("लॉगिन करें", use_container_width=True):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT role, permissions FROM users WHERE username=? AND password=?", (u.strip(), p.strip()))
                user = cursor.fetchone()
                conn.close()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = u.strip()
                    st.session_state.role = user[0]
                    try:
                        st.session_state.permissions = json.loads(user[1]) if user[1] else []
                    except:
                        st.session_state.permissions = []
                    st.rerun()
                else:
                    st.error("❌ गलत यूज़रनेम या पासवर्ड!")

    with forgot_tab:
        st.subheader("📱 मोबाइल OTP द्वारा पासवर्ड रीसेट")
        col_f1, _ = st.columns([1, 1])
        with col_f1:
            if st.session_state.reset_stage == "enter_user":
                target_u = st.text_input("अपना यूज़रनेम या रजिस्टर्ड मोबाइल नंबर दर्ज करें:")
                if st.button("📩 OTP भेजें", use_container_width=True):
                    if target_u.strip():
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("SELECT username, phone FROM users WHERE username=? OR phone=?", (target_u.strip(), target_u.strip()))
                        matched_user = cursor.fetchone()
                        conn.close()
                        
                        if matched_user:
                            if not matched_user[1]:
                                st.error("⚠️ इस आईडी के साथ कोई मोबाइल नंबर लिंक नहीं है। कृपया एडमिन से रीसेट करवाएं!")
                            else:
                                gen_otp = str(random.randint(100000, 999999))
                                st.session_state.generated_otp = gen_otp
                                st.session_state.reset_target_user = matched_user[0]
                                st.session_state.reset_target_phone = matched_user[1]
                                st.session_state.reset_stage = "verify_otp"
                                st.rerun()
                        else:
                            st.error("⚠️ यह यूज़रनेम या मोबाइल नंबर नहीं मिला!")
                    else:
                        st.warning("कृपया यूज़रनेम दर्ज करें!")

            elif st.session_state.reset_stage == "verify_otp":
                masked_phone = st.session_target_phone[-4:] if hasattr(st.session_state, 'reset_target_phone') else ""
                st.info(f"📲 मोबाइल नंबर के लिए 6-अंकों का OTP कोड:")
                st.success(f"🔐 आपका सुरक्षा OTP कोड: **{st.session_state.generated_otp}**")
                
                wa_otp_text = f"दुकान सॉफ्टवेयर पासवर्ड रीसेट OTP कोड: {st.session_state.generated_otp}"
                wa_otp_link = f"https://wa.me/91{st.session_state.reset_target_phone}?text={urllib.parse.quote(wa_otp_text)}"
                st.link_button("💬 व्हाट्सएप पर OTP कोड खोलें", wa_otp_link)
                
                entered_otp = st.text_input("6-अंकों का OTP दर्ज करें:", max_chars=6)
                new_pass = st.text_input("नया पासवर्ड (New Password):", type="password")
                
                c_ot1, c_ot2 = st.columns(2)
                with c_ot1:
                    if st.button("✅ पासवर्ड बदलें", type="primary", use_container_width=True):
                        if entered_otp.strip() == str(st.session_state.generated_otp):
                            if len(new_pass.strip()) >= 4:
                                conn = sqlite3.connect(DB_NAME)
                                cursor = conn.cursor()
                                cursor.execute("UPDATE users SET password=? WHERE username=?", (new_pass.strip(), st.session_state.reset_target_user))
                                conn.commit()
                                conn.close()
                                
                                st.success("🎉 पासवर्ड बदल गया! अब लॉगिन करें।")
                                st.session_state.reset_stage = "enter_user"
                                st.session_state.generated_otp = None
                                st.session_state.reset_target_user = None
                            else:
                                st.error("पासवर्ड कम से कम 4 अक्षरों का होना चाहिए!")
                        else:
                            st.error("❌ गलत OTP दर्ज किया गया है!")
                
                with c_ot2:
                    if st.button("रद्द करें (Cancel)", use_container_width=True):
                        st.session_state.reset_stage = "enter_user"
                        st.session_state.generated_otp = None
                        st.rerun()

# ==========================================
# 3. मल्टी-आइटम बिलिंग काउंटर
# ==========================================
elif mode == "💰 मल्टी-आइटम बिलिंग":
    st.subheader("🛒 काउंटर बिलिंग (Multi-Item Billing with GST)")
    
    conn = sqlite3.connect(DB_NAME)
    prods = pd.read_sql_query("SELECT id, name, sell_price, gst_percent, stock, buy_price FROM products WHERE stock > 0", conn)
    
    c_comm = conn.cursor()
    c_comm.execute("SELECT commission_percent FROM users WHERE username=?", (st.session_state.username,))
    row_comm = c_comm.fetchone()
    op_comm_rate = float(row_comm[0]) if row_comm and row_comm[0] else 0.0
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

        col1, col2, col3, col4 = st.columns([1, 2, 1, 2])
        max_allowed = max(1, avail_stock)
        qty = col1.number_input("मात्रा", min_value=1, max_value=max_allowed, value=1, disabled=(avail_stock <= 0))
        rate = col2.number_input("बिक्री दर (₹)", min_value=0.0, value=float(item_data["sell_price"]))
        gst_p = col3.number_input("GST %", min_value=0.0, value=float(item_data["gst_percent"]), step=1.0)
        
        with col4:
            st.write(f"दुकान में शेष: **{max(0, avail_stock)}** पीस")
            if st.button("➕ लिस्ट में जोड़ें", use_container_width=True, disabled=(avail_stock <= 0)):
                if avail_stock < qty:
                    st.error("स्टॉक पर्याप्त नहीं है!")
                elif rate < float(item_data["buy_price"]) and st.session_state.role != "admin":
                    st.error("⚠️ खरीद मूल्य से कम पर बेचने के लिए एडमिन अनुमति चाहिए!")
                else:
                    base_total = rate * qty
                    gst_amt = (base_total * gst_p) / 100.0
                    final_item_total = base_total + gst_amt
                    net_item_profit = (rate - item_data["buy_price"]) * qty
                    calc_commission = (net_item_profit * op_comm_rate) / 100.0 if net_item_profit > 0 else 0.0

                    st.session_state.billing_cart.append({
                        "id": int(item_data["id"]),
                        "name": str(selected_prod),
                        "qty": int(qty),
                        "rate": float(rate),
                        "buy_price": float(item_data["buy_price"]),
                        "gst_percent": float(gst_p),
                        "gst_amount": float(gst_amt),
                        "total": float(final_item_total),
                        "profit": float(net_item_profit),
                        "commission": float(calc_commission)
                    })
                    st.rerun()
    else:
        st.warning("दुकान में कोई सामान स्टॉक में नहीं है!")

    if st.session_state.billing_cart:
        st.markdown("---")
        st.markdown("#### 📋 चालू बिल लिस्ट")
        cart_df = pd.DataFrame(st.session_state.billing_cart)[["name", "qty", "rate", "gst_percent", "gst_amount", "total"]]
        cart_df.columns = ["सामान", "मात्रा", "दर (₹)", "GST %", "GST (₹)", "कुल (₹)"]
        st.dataframe(cart_df, use_container_width=True)

        total_bill_amount = sum(item["total"] for item in st.session_state.billing_cart)
        total_gst_collected = sum(item["gst_amount"] for item in st.session_state.billing_cart)
        
        st.markdown(f"### 💵 कुल बिल राशि: **₹{total_bill_amount:.2f}** <small style='font-size:15px;'>(कुल GST शामिल: ₹{total_gst_collected:.2f})</small>", unsafe_allow_html=True)

        c_pay1, c_pay2 = st.columns(2)
        payment_mode = c_pay1.selectbox("💳 भुगतान का तरीका (Payment Mode)", ["नकद (Cash)", "ऑनलाइन (UPI / Scanner)", "उधारी (Credit / Udhar)"])
        
        due_date_val = None
        if payment_mode == "उधारी (Credit / Udhar)":
            due_date_val = c_pay2.date_input("📅 उधारी चुकाने की अंतिम तारीख (Due Date)", min_value=date.today(), value=date.today() + timedelta(days=7))

        col_b1, col_b2 = st.columns([2, 1])
        with col_b1:
            if st.button("✅ फाइनल GST बिल काटें और स्टॉक घटाएं", type="primary", use_container_width=True):
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
                            INSERT INTO sales (bill_no, product_id, product_name, quantity, sell_price, gst_percent, gst_amount, total_amount, profit, operator_commission, sold_by, customer_name, customer_phone, payment_mode, due_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (bill_no, int(item["id"]), item["name"], int(item["qty"]), float(item["rate"]), float(item["gst_percent"]), float(item["gst_amount"]), float(item["total"]), float(item["profit"]), float(item.get("commission", 0.0)), str(st.session_state.username), str(cust_name), str(cust_phone), str(payment_mode), str(due_date_val) if due_date_val else ""))

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
                        "total_gst": total_gst_collected,
                        "sold_by": st.session_state.username
                    }
                    st.session_state.billing_cart = []
                    st.success("GST बिल सफलतापूर्वक कट गया!")
                    st.rerun()

        with col_b2:
            if st.button("❌ लिस्ट खाली करें", use_container_width=True):
                st.session_state.billing_cart = []
                st.rerun()

    if st.session_state.last_bill:
        b = st.session_state.last_bill
        st.divider()
        st.subheader("🧾 GST बिल इनवॉइस / रसीद")

        rows_html = "".join([f"<tr><td>{it['name']}</td><td>{it['qty']}</td><td>₹{it['rate']:.2f}</td><td>{it['gst_percent']}%</td><td>₹{it['total']:.2f}</td></tr>" for it in b["items"]])
        due_txt = f"<b>उधारी देय तिथि:</b> {b['due_date']}<br/>" if b.get('due_date') and b['due_date'] != 'N/A' else ""
        phone_txt = b['phone'] if b.get('phone') else 'N/A'

        bill_html = f"""
        <div id="printArea" style="border: 1px solid #000; padding: 15px; width: 360px; font-family: monospace; background: #fff; color: #000; margin: auto;">
            <h3 style="text-align:center; margin:0;">Raju Bhaiya Store</h3>
            <p style="text-align:center; margin:2px 0 10px 0; font-size:12px;">टैक्स इनवॉइस | धन्यवाद! पुनः पधारें</p>
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
            <table style="width:100%; font-size:12px; text-align:left;">
                <tr><th>सामान</th><th>मात्रा</th><th>दर</th><th>GST</th><th>कुल</th></tr>
                {rows_html}
            </table>
            <hr style="border-top: 1px dashed #000;"/>
            <div style="font-size: 13px; text-align: right;">
                <b>कुल GST: ₹{b.get('total_gst', 0.0):.2f}</b><br/>
                <h3 style="margin:5px 0;">फाइनल कुल राशि: ₹{b['total']:.2f}</h3>
            </div>
            <hr style="border-top: 1px dashed #000;"/>
            <p style="text-align:center; font-size:11px; margin:0;">कंप्यूटरीकृत GST रसीद | सॉफ्टवेयर जनरेटेड</p>
        </div>
        """
        st.components.v1.html(bill_html, height=400)

        print_script = f"""
        <html><body>
        <button onclick="printBill()" style="background-color:#2ed573; color:white; padding:10px 20px; font-size:15px; font-weight:bold; border:none; border-radius:5px; cursor:pointer; width:100%;">🖨️ यह GST बिल प्रिंट करें (Print / Save PDF)</button>
        <script>
        function printBill() {{
            var win = window.open('', '', 'height=600,width=450');
            win.document.write('<html><head><title>Print GST Bill</title></head><body style="margin:20px;">');
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

# ==========================================
# 4. नया स्टॉक / प्रोडक्ट जोड़ें
# ==========================================
elif mode == "➕ नया स्टॉक / प्रोडक्ट जोड़ें":
    st.subheader("➕ नया सामान स्टॉक एवं ऑनलाइन स्टोर में जोड़ें")
    
    with st.form("add_item_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        name = c1.text_input("सामान का नाम *", placeholder="उदा. 65W Fast Data Cable / 12x18 Photo Frame")
        category = c2.text_input("कैटेगरी *", value="जनरल")
        gst_slab = c3.selectbox("GST दर (%) *", [0, 5, 12, 18, 28], index=3)
        
        c4, c5, c6 = st.columns(3)
        buy_p = c4.number_input("खरीद लागत मूल्य (₹) *", min_value=0.0, step=1.0)
        sell_p = c5.number_input("बिक्री मूल्य (₹) *", min_value=0.0, step=1.0)
        stock = c6.number_input("स्टॉक मात्रा (Qty) *", min_value=1, step=1, value=10)
        
        alert = st.number_input("कम स्टॉक अलर्ट सीमा", min_value=1, value=3)
        desc = st.text_input("सामान का विवरण / वारंटी नोट", placeholder="उदा. लाइफटाइम गारंटी / ओरिजिनल क्वालिटी")
        
        st.markdown("---")
        st.markdown("#### 📸 फोटो अपलोड करने का माध्यम चुनें:")
        photo_choice = st.radio("कहाँ से फोटो अपलोड करनी है?", ["📁 गैलरी / कंप्यूटर से फ़ाइल चुनें (Browse)", "📷 लाइव कैमरे से फोटो खींचें", "🔗 ऑनलाइन इमेज लिंक (URL)"], horizontal=True)
        
        uploaded_file = None
        web_link = ""
        
        if photo_choice == "📁 गैलरी / कंप्यूटर से फ़ाइल चुनें (Browse)":
            uploaded_file = st.file_uploader("कंप्यूटर या मोबाइल से फोटो सेलेक्ट करें", type=["jpg", "jpeg", "png", "webp"])
        elif photo_choice == "📷 लाइव कैमरे से फोटो खींचें":
            uploaded_file = st.camera_input("कैमरा चालू करके फोटो क्लिक करें")
        else:
            web_link = st.text_input("फोटो का ऑनलाइन लिंक (Image URL)", placeholder="https://example.com/product.jpg")

        is_on = st.checkbox("🌐 इस सामान को ऑनलाइन डिजिटल कैटलॉग पर लाइव दिखाएं", value=True)

        if st.form_submit_button("💾 नया स्टॉक सुरक्षित करें", use_container_width=True):
            if not name.strip():
                st.warning("⚠️ कृपया सामान का नाम दर्ज करें!")
            else:
                final_photo_data = ""
                if uploaded_file is not None:
                    file_bytes = uploaded_file.getvalue()
                    encoded = base64.b64encode(file_bytes).decode()
                    mime_type = uploaded_file.type
                    final_photo_data = f"data:{mime_type};base64,{encoded}"
                elif web_link.strip():
                    final_photo_data = web_link.strip()

                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO products (name, category, buy_price, sell_price, gst_percent, stock, min_alert, description, image_url, is_online)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name.strip(), category.strip(), buy_p, sell_p, float(gst_slab), stock, alert, desc.strip(), final_photo_data, 1 if is_on else 0))
                conn.commit()
                conn.close()
                st.success(f"✅ '{name}' (GST: {gst_slab}%) सफलतापूर्वक स्टॉक में जुड़ गया!")

# ==========================================
# 5. स्टॉक व ऑनलाइन शो
# ==========================================
elif mode == "📦 स्टॉक व ऑनलाइन शो":
    st.subheader("📦 दुकान का लाइव स्टॉक एवं GST लिस्टिंग")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, name, category, buy_price, sell_price, gst_percent, stock, min_alert, is_online FROM products", conn)
    conn.close()

    search = st.text_input("🔍 सामान सर्च करें")
    if search:
        df = df[df["name"].str.contains(search, case=False, na=False)]

    st.dataframe(df, use_container_width=True)

# ==========================================
# 6. उधारी/खाता अलर्ट
# ==========================================
elif mode == "📒 उधारी/खाता अलर्ट":
    st.subheader("📒 ग्राहक उधारी रजिस्टर एवं WhatsApp पेमेंट रिमाइंडर")
    conn = sqlite3.connect(DB_NAME)
    
    c_set = conn.cursor()
    c_set.execute("SELECT shop_title, shop_phone FROM shop_settings WHERE id=1")
    s_info = c_set.fetchone()
    current_shop_name = s_info[0] if s_info else "Raju Bhaiya Store"
    current_shop_phone = s_info[1] if s_info and s_info[1] else "8349596263"

    udhar_df = pd.read_sql_query("SELECT id, bill_no, customer_name, customer_phone, total_amount, paid_amount, due_date, status FROM udhar_ledger WHERE status='PENDING'", conn)
    
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

        st.markdown("#### 📋 सक्रिय उधारी लिस्ट एवं 1-क्लिक WhatsApp तगादा:")
        for idx, row in udhar_df.iterrows():
            c_u1, c_u2, c_u3, c_u4 = st.columns([3, 2, 2, 3])
            is_overdue = row['due_date_dt'] < today_dt
            status_tag = "🔴 तारीख निकल गई!" if is_overdue else "🟢 सक्रिय"
            
            c_u1.write(f"**{row['customer_name']}**\n\n📱 `{row['customer_phone'] if row['customer_phone'] else 'N/A'}`\n\nबिल: `{row['bill_no']}`")
            c_u2.write(f"बकाया: **₹{row['baki_amount']:.2f}**\n\n(कुल ₹{row['total_amount']:.2f})")
            c_u3.write(f"देय तारीख:\n**{row['due_date']}**\n\n{status_tag}")
            
            reminder_text = (
                f"नमस्ते *{row['customer_name']}* जी,\n\n"
                f"यह संदेश *{current_shop_name}* की तरफ से है।\n"
                f"आपके बिल नं. *{row['bill_no']}* का कुल बकाया राशि *₹{row['baki_amount']:.2f}* है, "
                f"जिसके भुगतान की नियत तारीख *{row['due_date']}* थी।\n\n"
                f"{'⚠️ *सूचना:* कृपया जल्द से जल्द भुगतान सुनिश्चित करें।' if is_overdue else 'कृपया समय पर भुगतान कर सहयोग करें।'}\n\n"
                f"धन्यवाद,\n*{current_shop_name}*\n📞 संपर्क: +91 {current_shop_phone}"
            )
            
            c_phone_clean = "".join([d for d in str(row['customer_phone']) if d.isdigit()])
            if len(c_phone_clean) == 10:
                c_phone_clean = "91" + c_phone_clean
                
            wa_reminder_url = f"https://wa.me/{c_phone_clean}?text={urllib.parse.quote(reminder_text)}"

            with c_u4:
                if row['customer_phone'] and len(c_phone_clean) >= 10:
                    st.link_button("📲 WhatsApp तगादा भेजें", wa_reminder_url, use_container_width=True)
                else:
                    st.caption("⚠️ मोबाइल नंबर नहीं है")
                    
                if st.button(f"💰 पूरा भुगतान मिला", key=f"pay_{row['id']}", use_container_width=True):
                    c = conn.cursor()
                    c.execute("UPDATE udhar_ledger SET paid_amount = total_amount, status = 'PAID' WHERE id = ?", (int(row['id']),))
                    conn.commit()
                    st.success(f"{row['customer_name']} का खाता चुकता हो गया!")
                    st.rerun()
            st.divider()
    else:
        st.success("दुकान में किसी ग्राहक की कोई उधारी बकाया नहीं है!")
    conn.close()

# ==========================================
# 7. ऑपरेटर बिक्री रिपोर्ट
# ==========================================
elif mode == "👔 ऑपरेटर बिक्री रिपोर्ट":
    st.subheader("👔 ऑपरेटर बिक्री एवं परफॉरमेंस रिपोर्ट")
    
    conn = sqlite3.connect(DB_NAME)
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    conn.close()

    if not sales_df.empty:
        sales_df["sale_date"] = pd.to_datetime(sales_df["sale_date"])
        all_sellers = ["सभी ऑपरेटर (All Staff)"] + sorted(sales_df["sold_by"].dropna().unique().tolist())

        c_f1, c_f2 = st.columns([2, 2])
        chosen_seller = c_f1.selectbox("👤 किस ऑपरेटर की बिक्री देखनी है?", all_sellers)
        time_period = c_f2.selectbox("📅 समय सीमा चुनें", ["आज (Today)", "कल (Yesterday)", "पिछले 7 दिन", "पिछले 30 दिन", "शुरुआत से अब तक (All Time)"])

        now = datetime.now()
        filtered_df = sales_df.copy()

        if chosen_seller != "सभी ऑपरेटर (All Staff)":
            filtered_df = filtered_df[filtered_df["sold_by"] == chosen_seller]

        if time_period == "आज (Today)":
            filtered_df = filtered_df[filtered_df["sale_date"].dt.date == now.date()]
        elif time_period == "कल (Yesterday)":
            filtered_df = filtered_df[filtered_df["sale_date"].dt.date == (now - timedelta(days=1)).date()]
        elif time_period == "पिछले 7 दिन":
            filtered_df = filtered_df[filtered_df["sale_date"] >= (now - timedelta(days=7))]
        elif time_period == "पिछले 30 दिन":
            filtered_df = filtered_df[filtered_df["sale_date"] >= (now - timedelta(days=30))]

        st.divider()

        if not filtered_df.empty:
            total_op_sales = filtered_df["total_amount"].sum()
            total_op_profit = filtered_df["profit"].sum()
            total_bills_count = filtered_df["bill_no"].nunique()
            total_items_count = filtered_df["quantity"].sum()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("कुल बिल काटे", f"{total_bills_count} बिल")
            m2.metric("कुल सामान बेचा", f"{total_items_count} पीस")
            m3.metric("कुल बिक्री राशि", f"₹{total_op_sales:.2f}")
            m4.metric("शुद्ध मुनाफ़ा दिलाया", f"₹{total_op_profit:.2f}")

            st.divider()

            col_s1, col_s2 = st.columns([1, 1])
            with col_s1:
                st.markdown("#### 📦 कौन-कौन सा सामान कितना बेचा:")
                item_breakdown = filtered_df.groupby("product_name").agg(
                    कुल_मात्रा=('quantity', 'sum'),
                    कुल_बिक्री=('total_amount', 'sum'),
                    मुनाफा=('profit', 'sum')
                ).reset_index().sort_values(by="कुल_मात्रा", ascending=False)
                
                st.dataframe(item_breakdown.rename(columns={
                    "product_name": "सामान का नाम",
                    "कुल_मात्रा": "बेची गई मात्रा",
                    "कुल_बिक्री": "बिक्री (₹)",
                    "मुनाफा": "कमाई (₹)"
                }), use_container_width=True)

            with col_s2:
                st.markdown("#### 📊 बिक्री चार्ट")
                fig_op = px.bar(item_breakdown.head(8), x="product_name", y="कुल_बिक्री", color="कुल_मात्रा", title="टॉप सेलिंग आइटम्स")
                st.plotly_chart(fig_op, use_container_width=True)
        else:
            st.warning("चुने गए समय और ऑपरेटर के लिए कोई रिकॉर्ड नहीं मिला!")
    else:
        st.info("अभी कोई बिक्री डेटा उपलब्ध नहीं है।")

# ==========================================
# 8. ऑपरेटर मासिक कमीशन
# ==========================================
elif mode == "💵 ऑपरेटर मासिक कमीशन":
    st.subheader("💵 ऑपरेटर मासिक कमीशन व पे-आउट रजिस्टर")
    st.caption("मुनाफ़े पर आधारित मासिक कमीशन का स्वचालित हिसाब")

    conn = sqlite3.connect(DB_NAME)
    sales_df = pd.read_sql_query("SELECT * FROM sales WHERE sold_by != 'admin'", conn)
    users_df = pd.read_sql_query("SELECT username, commission_percent FROM users WHERE role='operator'", conn)
    conn.close()

    if not users_df.empty:
        col_c1, col_c2 = st.columns(2)
        op_list = users_df["username"].tolist()
        sel_op = col_c1.selectbox("👤 ऑपरेटर चुनें:", op_list)
        
        current_year = datetime.now().year
        months_list = [f"{m:02d}-{current_year}" for m in range(1, 13)]
        default_idx = datetime.now().month - 1
        sel_month = col_c2.selectbox("📅 महीना चुनें (MM-YYYY):", months_list, index=default_idx)

        op_info = users_df[users_df["username"] == sel_op].iloc[0]
        comm_pct = float(op_info["commission_percent"]) if op_info["commission_percent"] else 0.0

        st.info(f"💡 **{sel_op}** का निर्धारित मुनाफ़ा कमीशन स्लैब: **{comm_pct}%**")

        if not sales_df.empty:
            sales_df["sale_date"] = pd.to_datetime(sales_df["sale_date"])
            sales_df["month_str"] = sales_df["sale_date"].dt.strftime("%m-%Y")
            
            monthly_op_sales = sales_df[(sales_df["sold_by"] == sel_op) & (sales_df["month_str"] == sel_month)]

            if not monthly_op_sales.empty:
                m_sales = monthly_op_sales["total_amount"].sum()
                m_profit = monthly_op_sales["profit"].sum()
                
                if "operator_commission" in monthly_op_sales.columns and monthly_op_sales["operator_commission"].sum() > 0:
                    total_comm_earned = monthly_op_sales["operator_commission"].sum()
                else:
                    total_comm_earned = (m_profit * comm_pct) / 100.0 if m_profit > 0 else 0.0

                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric(f"महीने की कुल बिक्री ({sel_month})", f"₹{m_sales:.2f}")
                c_m2.metric("दुकान को हुआ कुल मुनाफ़ा", f"₹{m_profit:.2f}")
                c_m3.metric("🎯 ऑपरेटर का कुल कमीशन", f"₹{total_comm_earned:.2f}")

                st.divider()
                st.markdown(f"#### 📋 {sel_op} द्वारा {sel_month} में की गई सभी बिलिंग का हिसाब:")
                st.dataframe(monthly_op_sales[["bill_no", "sale_date", "product_name", "quantity", "total_amount", "profit", "operator_commission"]].rename(columns={
                    "bill_no": "बिल नं",
                    "sale_date": "तारीख",
                    "product_name": "सामान",
                    "quantity": "मात्रा",
                    "total_amount": "बिक्री (₹)",
                    "profit": "मुनाफ़ा (₹)",
                    "operator_commission": "कमीशन (₹)"
                }), use_container_width=True)
            else:
                st.warning(f"{sel_op} ने {sel_month} महीने में कोई बिलिंग नहीं की है।")
        else:
            st.info("अभी कोई ऑपरेटर बिक्री डेटा उपलब्ध नहीं है।")
    else:
        st.info("दुकान में कोई ऑपरेटर नहीं है।")

# ==========================================
# 9. एडमिन डैशबोर्ड
# ==========================================
elif mode == "📊 एडमिन डैशबोर्ड":
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

        pending_udhar_total = (udhar_df['total_amount'] - udhar_df['paid_amount']).sum() if not udhar_df.empty else 0.0
        total_gst_all = sales_df["gst_amount"].sum() if "gst_amount" in sales_df.columns else 0.0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("आज का मुनाफ़ा", f"₹{today_sales['profit'].sum():.2f}", f"बिक्री: ₹{today_sales['total_amount'].sum():.2f}")
        c2.metric("कल का मुनाफ़ा", f"₹{yesterday_sales['profit'].sum():.2f}", f"बिक्री: ₹{yesterday_sales['total_amount'].sum():.2f}")
        c3.metric("कुल एकत्रित GST", f"₹{total_gst_all:.2f}", "टैक्स फाइलिंग हेतु")
        c4.metric("मार्केट में कुल उधारी", f"₹{pending_udhar_total:.2f}", "बकाया")

        st.divider()
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("🔥 सबसे ज़्यादा बिकने वाले सामान")
            top_items = sales_df.groupby("product_name")["quantity"].sum().reset_index()
            fig1 = px.bar(top_items.sort_values(by="quantity", ascending=False).head(10), x="product_name", y="quantity", color="quantity")
            st.plotly_chart(fig1, use_container_width=True)

        with col_right:
            st.subheader("⚠️ न बिकने वाला स्टॉक (Dead Stock)")
            sold_ids = sales_df["product_id"].unique()
            dead_stock = products_df[~products_df["id"].isin(sold_ids)]
            if not dead_stock.empty:
                st.dataframe(dead_stock[["name", "stock", "buy_price", "gst_percent"]], use_container_width=True)
            else:
                st.success("सभी सामान सक्रिय बिक रहे हैं!")
    else:
        st.info("अभी कोई बिक्री डेटा उपलब्ध नहीं है।")

# ==========================================
# 10. ऑपरेटर मैनेजमेंट
# ==========================================
elif mode == "👥 ऑपरेटर मैनेजमेंट":
    st.subheader("👥 ऑपरेटर (स्टाफ) आईडी, कमीशन % एवं परमिशन कंट्रोल")
    
    tab1, tab2, tab3 = st.tabs(["➕ नया ऑपरेटर बनाएं", "⚙️ परमिशन व कमीशन % अपडेट", "🔑 सीधा पासवर्ड रीसेट (Admin)"])
    
    with tab1:
        with st.form("add_user_form", clear_on_submit=True):
            st.markdown("#### 1. ऑपरेटर क्रेडेंशियल्स एवं कमीशन")
            c_u1, c_u2, c_u3 = st.columns(3)
            u_name = c_u1.text_input("नया यूज़रनेम *", placeholder="उदा. rahul, sandeep")
            u_phone = c_u2.text_input("ऑपरेटर का मोबाइल नंबर *", placeholder="उदा. 98XXXXXXXX", max_chars=10)
            u_comm = c_u3.number_input("मुनाफ़ा कमीशन (%):", min_value=0.0, max_value=100.0, value=5.0, step=0.5)
            u_pass = st.text_input("पासवर्ड *", type="password")
            
            st.markdown("#### 2. इस ऑपरेटर को कौन-से एक्सेस देने हैं?")
            selected_permissions = []
            
            p_cols = st.columns(2)
            for i, perm in enumerate(ALL_PERMISSIONS):
                with p_cols[i % 2]:
                    is_checked = perm in ["🛍️ ऑनलाइन स्टोर देखें", "💰 मल्टी-आइटम बिलिंग", "📦 स्टॉक व ऑनलाइन शो"]
                    if st.checkbox(perm, value=is_checked, key=f"new_perm_{perm}"):
                        selected_permissions.append(perm)
            
            if st.form_submit_button("💾 ऑपरेटर सुरक्षित करें", use_container_width=True):
                if u_name.strip() and u_pass.strip() and u_phone.strip():
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    try:
                        perms_json = json.dumps(selected_permissions)
                        cursor.execute("INSERT INTO users (username, password, phone, commission_percent, role, permissions) VALUES (?, ?, ?, ?, 'operator', ?)", (u_name.strip(), u_pass.strip(), u_phone.strip(), float(u_comm), perms_json))
                        conn.commit()
                        st.success(f"✅ ऑपरेटर '{u_name}' (कमीशन: {u_comm}%) सफलतापूर्वक बन गया!")
                    except sqlite3.IntegrityError:
                        st.error("⚠️ यह यूज़रनेम पहले से मौजूद है!")
                    conn.close()
                else:
                    st.warning("कृपया यूज़रनेम, मोबाइल नंबर और पासवर्ड तीनों भरें!")

    with tab2:
        st.markdown("#### ⚙️ ऑपरेटर परमिशन, कमीशन व मोबाइल एडिट करें")
        conn = sqlite3.connect(DB_NAME)
        ops_df = pd.read_sql_query("SELECT id, username, phone, commission_percent, permissions FROM users WHERE role='operator'", conn)
        conn.close()
        
        if not ops_df.empty:
            selected_op = st.selectbox("ऑपरेटर चुनें:", ops_df["username"].tolist())
            op_row = ops_df[ops_df["username"] == selected_op].iloc[0]
            
            try:
                curr_perms = json.loads(op_row["permissions"]) if op_row["permissions"] else []
            except:
                curr_perms = []
            
            with st.form("edit_perms_form"):
                c_e1, c_e2 = st.columns(2)
                up_phone = c_e1.text_input("मोबाइल नंबर:", value=str(op_row["phone"]) if op_row["phone"] else "", max_chars=10)
                up_comm = c_e2.number_input("मुनाफ़ा कमीशन (%):", min_value=0.0, max_value=100.0, value=float(op_row["commission_percent"]) if op_row["commission_percent"] else 0.0, step=0.5)

                st.write(f"**'{selected_op}' के चालू एक्सेस:**")
                updated_perms = []
                e_cols = st.columns(2)
                for i, perm in enumerate(ALL_PERMISSIONS):
                    with e_cols[i % 2]:
                        checked = perm in curr_perms
                        if st.checkbox(perm, value=checked, key=f"edit_perm_{selected_op}_{perm}"):
                            updated_perms.append(perm)
                
                if st.form_submit_button("🔄 विवरण व कमीशन अपडेट करें", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("UPDATE users SET phone = ?, commission_percent = ?, permissions = ? WHERE username = ?", (up_phone.strip(), float(up_comm), json.dumps(updated_perms), selected_op))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ '{selected_op}' का विवरण और {up_comm}% कमीशन अपडेट हो गया!")
                    st.rerun()
        else:
            st.info("अभी कोई ऑपरेटर मौजूद नहीं है।")

    with tab3:
        st.markdown("#### 🔑 एडमिन द्वारा किसी ऑपरेटर का पासवर्ड सीधे बदलें")
        if not ops_df.empty:
            with st.form("admin_reset_pass"):
                target_op = st.selectbox("जिस ऑपरेटर का पासवर्ड बदलना है:", ops_df["username"].tolist(), key="admin_sel_op")
                admin_new_pass = st.text_input("नया पासवर्ड सेट करें:", type="password")
                if st.form_submit_button("💾 पासवर्ड तुरंत बदलें", use_container_width=True):
                    if len(admin_new_pass.strip()) >= 4:
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("UPDATE users SET password = ? WHERE username = ?", (admin_new_pass.strip(), target_op))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ ऑपरेटर '{target_op}' का नया पासवर्ड तुरंत सेट हो गया!")
                    else:
                        st.error("पासवर्ड कम से कम 4 अक्षरों का होना चाहिए!")
        else:
            st.info("कोई ऑपरेटर उपलब्ध नहीं है।")

# ==========================================
# 11. स्टोर बैनर एवं नाम सेटिंग्स
# ==========================================
elif mode == "🎨 स्टोर बैनर व सेटिंग्स":
    st.subheader("🎨 ऑनलाइन स्टोर ब्रांडिंग व सेटिंग्स")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT shop_title, shop_subtitle, shop_phone, banner_image FROM shop_settings WHERE id=1")
    current_settings = c.fetchone()
    conn.close()
    
    cur_title = current_settings[0] if current_settings else "Raju Bhaiya Online Store"
    cur_sub = current_settings[1] if current_settings else "डिजिटल प्रोडक्ट कैटलॉग एवं ऑनलाइन ऑर्डर"
    cur_phone = current_settings[2] if current_settings and current_settings[2] else "8349596263"
    cur_banner = current_settings[3] if current_settings else ""

    with st.form("shop_settings_form"):
        st.markdown("#### 1. दुकान / स्टोर का नाम एवं संपर्क")
        c_st1, c_st2 = st.columns(2)
        new_title = c_st1.text_input("स्टोर का नाम (Store Title)", value=cur_title)
        new_phone = c_st2.text_input("स्टोर संपर्क नंबर (Mobile / WhatsApp No.) *", value=cur_phone, max_chars=10)
        
        new_sub = st.text_input("टैगलाइन / सबटाइटल (Subtitle)", value=cur_sub)
        
        st.markdown("---")
        st.markdown("#### 2. दुकान का लोगो / बैनर फोटो")
        
        if cur_banner and len(str(cur_banner).strip()) > 5:
            st.image(cur_banner, caption="वर्तमान बैनर / फोटो", width=200)
            
        banner_choice = st.radio("फोटो अपलोड का माध्यम:", ["📁 कंप्यूटर / मोबाइल से फोटो अपलोड करें", "🔗 ऑनलाइन वेब लिंक (Image URL)"], horizontal=True)
        
        banner_file = None
        banner_url_in = ""
        
        if banner_choice == "📁 कंप्यूटर / मोबाइल से फोटो अपलोड करें":
            banner_file = st.file_uploader("दुकान का लोगो या बैनर फोटो चुनें", type=["jpg", "jpeg", "png", "webp"])
        else:
            banner_url_in = st.text_input("फोटो का ऑनलाइन लिंक (Image URL)", value=cur_banner if cur_banner.startswith("http") else "")

        if st.form_submit_button("💾 सेटिंग्स सुरक्षित करें", use_container_width=True):
            final_banner_data = cur_banner
            if banner_file is not None:
                b_bytes = banner_file.getvalue()
                b64 = base64.b64encode(b_bytes).decode()
                m_type = banner_file.type
                final_banner_data = f"data:{m_type};base64,{b64}"
            elif banner_url_in.strip():
                final_banner_data = banner_url_in.strip()

            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE shop_settings SET shop_title=?, shop_subtitle=?, shop_phone=?, banner_image=? WHERE id=1", (new_title.strip(), new_sub.strip(), new_phone.strip(), final_banner_data))
            conn.commit()
            conn.close()
            st.success("✅ ऑनलाइन स्टोर का नाम, संपर्क नंबर और फोटो अपडेट हो गया!")
            st.rerun()