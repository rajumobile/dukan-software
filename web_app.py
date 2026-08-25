import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import urllib.parse
import base64
import json
import random

st.set_page_config(page_title="Raju Bhaiya Enterprise ERP & POS", page_icon="🏢", layout="wide")

DB_NAME = "shop.db"

ALL_PERMISSIONS = [
    "🛍️ ऑनलाइन स्टोर देखें",
    "⚡ सुपरफास्ट POS बिलिंग",
    "🔄 सेल्स रिटर्न व रिफंड",
    "🏷️ बारकोड स्टिकर प्रिंटर",
    "📄 GSTR-1 टैक्स रिपोर्ट",
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
    
    # 1. टेबल्स बनाना
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            phone TEXT DEFAULT '',
            commission_percent REAL DEFAULT 0,
            role TEXT,
            permissions TEXT DEFAULT '["🛍️ ऑनलाइन स्टोर देखें", "⚡ सुपरफास्ट POS बिलिंग", "📦 स्टॉक व ऑनलाइन शो"]'
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS shop_settings (
            id INTEGER PRIMARY KEY,
            shop_title TEXT DEFAULT 'Raju Bhaiya Online Store',
            shop_subtitle TEXT DEFAULT 'डिजिटल प्रोडक्ट कैटलॉग एवं ऑनलाइन ऑर्डर',
            shop_phone TEXT DEFAULT '8349596263',
            shop_gstin TEXT DEFAULT '',
            upi_id TEXT DEFAULT '8349596263@upi',
            banner_image TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_no TEXT DEFAULT '',
            name TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            hsn_code TEXT DEFAULT '8504',
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
            serial_no TEXT DEFAULT '',
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
        CREATE TABLE IF NOT EXISTS sales_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT,
            product_id INTEGER,
            product_name TEXT,
            returned_qty INTEGER,
            refund_amount REAL,
            return_reason TEXT,
            returned_by TEXT,
            return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # 2. पुराने डेटाबेस में नए कॉलम ऑटो-अपग्रेड (INSERT से पहले)
    def add_col(tbl, col, typ):
        try:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass

    add_col("shop_settings", "shop_phone", "TEXT DEFAULT '8349596263'")
    add_col("shop_settings", "shop_gstin", "TEXT DEFAULT ''")
    add_col("shop_settings", "upi_id", "TEXT DEFAULT '8349596263@upi'")
    add_col("products", "serial_no", "TEXT DEFAULT ''")
    add_col("products", "hsn_code", "TEXT DEFAULT '8504'")
    add_col("products", "gst_percent", "REAL DEFAULT 0")
    add_col("products", "category", "TEXT DEFAULT 'General'")
    add_col("products", "description", "TEXT DEFAULT ''")
    add_col("products", "image_url", "TEXT DEFAULT ''")
    add_col("products", "is_online", "INTEGER DEFAULT 1")
    add_col("sales", "serial_no", "TEXT DEFAULT ''")
    add_col("sales", "operator_commission", "REAL DEFAULT 0")
    add_col("sales", "gst_percent", "REAL DEFAULT 0")
    add_col("sales", "gst_amount", "REAL DEFAULT 0")
    add_col("sales", "bill_no", "TEXT")
    add_col("sales", "sold_by", "TEXT")
    add_col("sales", "customer_name", "TEXT")
    add_col("sales", "customer_phone", "TEXT")
    add_col("sales", "payment_mode", "TEXT")
    add_col("sales", "due_date", "TEXT")
    add_col("users", "phone", "TEXT DEFAULT ''")
    add_col("users", "commission_percent", "REAL DEFAULT 0")
    add_col("users", "permissions", "TEXT DEFAULT '[]'")

    # 3. डिफ़ॉल्ट डेटा दर्ज करना
    c.execute("INSERT OR IGNORE INTO shop_settings (id, shop_title, shop_subtitle, shop_phone, shop_gstin, upi_id, banner_image) VALUES (1, 'Raju Bhaiya Online Store', 'डिजिटल प्रोडक्ट कैटलॉग एवं ऑनलाइन ऑर्डर', '8349596263', '', '8349596263@upi', '')")

    admin_perms = json.dumps(ALL_PERMISSIONS)
    default_op_perms = json.dumps(["🛍️ ऑनलाइन स्टोर देखें", "⚡ सुपरफास्ट POS बिलिंग", "📦 स्टॉक व ऑनलाइन शो", "📒 उधारी/खाता अलर्ट"])

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
if "gen_serial_code" not in st.session_state:
    st.session_state.gen_serial_code = f"SN-{random.randint(100000, 999999)}"

# --- साइडबार नेविगेशन ---
st.sidebar.markdown("## 🏢 व्यापार ERP पोर्टल")

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
            user_menu = ["🛍️ ऑनलाइन स्टोर देखें", "⚡ सुपरफास्ट POS बिलिंग"]
    
    mode = st.sidebar.radio("मेन्यू चुनें:", user_menu)

# ==========================================
# 1. पब्लिक ऑनलाइन स्टोर
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
    
    online_prods = pd.read_sql_query("SELECT id, serial_no, name, category, sell_price, gst_percent, stock, description, image_url FROM products WHERE is_online=1 AND stock > 0", conn)
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
    search_query = col_s1.text_input("🔍 सामान या सीरियल नंबर खोजें", placeholder="सामान का नाम या सीरियल नंबर लिखें...")
    
    categories = ["सभी (All)"] + (online_prods["category"].dropna().unique().tolist() if not online_prods.empty else [])
    selected_cat = col_s2.selectbox("कैटेगरी फ़िल्टर", categories)

    filtered_prods = online_prods.copy()
    if not filtered_prods.empty:
        if search_query.strip():
            filtered_prods = filtered_prods[
                filtered_prods["name"].str.contains(search_query, case=False, na=False) |
                filtered_prods["serial_no"].str.contains(search_query, case=False, na=False)
            ]
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
                    if row["serial_no"]:
                        st.caption(f"🔢 S/N: `{row['serial_no']}`")
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
                st.info("📲 मोबाइल नंबर के लिए 6-अंकों का OTP कोड:")
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
# 3. सुपरफास्ट POS बारकोड बिलिंग व डायनामिक UPI QR
# ==========================================
elif mode in ["⚡ सुपरफास्ट POS बिलिंग", "💰 मल्टी-आइटम बिलिंग"]:
    st.subheader("⚡ सुपरफास्ट POS बारकोड बिलिंग काउंटर")
    
    conn = sqlite3.connect(DB_NAME)
    prods = pd.read_sql_query("SELECT id, serial_no, name, sell_price, gst_percent, stock, buy_price FROM products WHERE stock > 0", conn)
    
    c_set = conn.cursor()
    c_set.execute("SELECT shop_title, shop_phone, upi_id, shop_gstin FROM shop_settings WHERE id=1")
    s_info = c_set.fetchone()
    current_shop_name = s_info[0] if s_info else "Raju Bhaiya Store"
    current_shop_phone = s_info[1] if s_info and s_info[1] else "8349596263"
    current_upi_id = s_info[2] if s_info and s_info[2] else "8349596263@upi"
    current_gstin = s_info[3] if s_info and s_info[3] else ""

    c_comm = conn.cursor()
    c_comm.execute("SELECT commission_percent FROM users WHERE username=?", (st.session_state.username,))
    row_comm = c_comm.fetchone()
    op_comm_rate = float(row_comm[0]) if row_comm and row_comm[0] else 0.0
    conn.close()

    col_c1, col_c2 = st.columns(2)
    cust_name = col_c1.text_input("ग्राहक का नाम", value="नकद ग्राहक")
    cust_phone = col_c2.text_input("ग्राहक का मोबाइल नंबर", value="")

    st.markdown("---")
    
    st.markdown("#### ⚡ 1. बारकोड स्कैनर से तुरंत जोड़ें (Instant Barcode Scan)")
    with st.form("barcode_scan_form", clear_on_submit=True):
        sc_col1, sc_col2 = st.columns([3, 1])
        scanned_code = sc_col1.text_input("⚡ बारकोड / S/N स्कैन करें (Scan Barcode & Enter)", placeholder="बारकोड स्कैनर बीप करें या टाइप करें...")
        scan_submit = sc_col2.form_submit_button("⚡ स्कैन कर बिल में जोड़ें", use_container_width=True)

        if scan_submit and scanned_code.strip():
            matched_item = prods[prods["serial_no"].str.lower() == scanned_code.strip().lower()]
            if not matched_item.empty:
                item_data = matched_item.iloc[0]
                already_in_cart = sum(item["qty"] for item in st.session_state.billing_cart if item["id"] == int(item_data["id"]))
                avail_stock = int(item_data["stock"]) - already_in_cart

                if avail_stock >= 1:
                    base_rate = float(item_data["sell_price"])
                    gst_p = float(item_data["gst_percent"])
                    gst_amt = (base_rate * gst_p) / 100.0
                    net_item_profit = base_rate - float(item_data["buy_price"])
                    calc_commission = (net_item_profit * op_comm_rate) / 100.0 if net_item_profit > 0 else 0.0

                    found = False
                    for it in st.session_state.billing_cart:
                        if it["id"] == int(item_data["id"]):
                            it["qty"] += 1
                            it["total"] = (it["rate"] + (it["rate"] * it["gst_percent"] / 100.0)) * it["qty"]
                            it["gst_amount"] = (it["rate"] * it["qty"] * it["gst_percent"]) / 100.0
                            it["profit"] = (it["rate"] - it["buy_price"]) * it["qty"]
                            it["commission"] = (it["profit"] * op_comm_rate) / 100.0 if it["profit"] > 0 else 0.0
                            found = True
                            break
                    
                    if not found:
                        st.session_state.billing_cart.append({
                            "id": int(item_data["id"]),
                            "serial_no": str(item_data["serial_no"]),
                            "name": str(item_data["name"]),
                            "qty": 1,
                            "rate": base_rate,
                            "buy_price": float(item_data["buy_price"]),
                            "gst_percent": gst_p,
                            "gst_amount": gst_amt,
                            "total": base_rate + gst_amt,
                            "profit": net_item_profit,
                            "commission": calc_commission
                        })
                    st.success(f"⚡ '{item_data['name']}' बिल में जुड़ गया!")
                    st.rerun()
                else:
                    st.error("⚠️ इस सामान का स्टॉक समाप्त हो चुका है!")
            else:
                st.error(f"❌ '{scanned_code}' बारकोड/सीरियल नंबर से कोई सामान नहीं मिला!")

    st.markdown("#### 🛒 2. या मेन्यू से सामान चुनें (Manual Select)")
    if not prods.empty:
        prods["display_label"] = prods.apply(lambda r: f"{r['name']} (S/N: {r['serial_no']})" if r['serial_no'] else r['name'], axis=1)
        selected_display = st.selectbox("सामान चुनें", prods["display_label"].tolist())
        item_data = prods[prods["display_label"] == selected_display].iloc[0]

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
                        "serial_no": str(item_data["serial_no"]) if item_data["serial_no"] else "",
                        "name": str(item_data["name"]),
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
        st.markdown("#### 📋 चालू POS बिल लिस्ट")
        cart_df = pd.DataFrame(st.session_state.billing_cart)[["name", "serial_no", "qty", "rate", "gst_percent", "gst_amount", "total"]]
        cart_df.columns = ["सामान", "सीरियल नं", "मात्रा", "दर (₹)", "GST %", "GST (₹)", "कुल (₹)"]
        st.dataframe(cart_df, use_container_width=True)

        total_bill_amount = sum(item["total"] for item in st.session_state.billing_cart)
        total_gst_collected = sum(item["gst_amount"] for item in st.session_state.billing_cart)
        
        st.markdown(f"### 💵 कुल बिल राशि: **₹{total_bill_amount:.2f}** <small style='font-size:15px;'>(कुल GST शामिल: ₹{total_gst_collected:.2f})</small>", unsafe_allow_html=True)

        upi_url = f"upi://pay?pa={current_upi_id}&pn={urllib.parse.quote(current_shop_name)}&am={total_bill_amount:.2f}&cu=INR"
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(upi_url)}"

        c_pay1, c_pay2, c_pay3 = st.columns([2, 2, 2])
        payment_mode = c_pay1.selectbox("💳 भुगतान का तरीका (Payment Mode)", ["नकद (Cash)", "ऑनलाइन (UPI QR Scanner)", "उधारी (Credit / Udhar)"])
        
        due_date_val = None
        if payment_mode == "उधारी (Credit / Udhar)":
            due_date_val = c_pay2.date_input("📅 उधारी चुकाने की अंतिम तारीख (Due Date)", min_value=date.today(), value=date.today() + timedelta(days=7))
        elif payment_mode == "ऑनलाइन (UPI QR Scanner)":
            with c_pay3:
                st.image(qr_api_url, caption=f"₹{total_bill_amount:.2f} स्कैन करें", width=140)

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
                            INSERT INTO sales (bill_no, product_id, serial_no, product_name, quantity, sell_price, gst_percent, gst_amount, total_amount, profit, operator_commission, sold_by, customer_name, customer_phone, payment_mode, due_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (bill_no, int(item["id"]), str(item.get("serial_no", "")), item["name"], int(item["qty"]), float(item["rate"]), float(item["gst_percent"]), float(item["gst_amount"]), float(item["total"]), float(item["profit"]), float(item.get("commission", 0.0)), str(st.session_state.username), str(cust_name), str(cust_phone), str(payment_mode), str(due_date_val) if due_date_val else ""))

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
                        "sold_by": st.session_state.username,
                        "qr_url": qr_api_url
                    }
                    st.session_state.billing_cart = []
                    st.success("⚡ GST बिल सफलतापूर्वक कट गया!")
                    st.rerun()

        with col_b2:
            if st.button("❌ लिस्ट खाली करें", use_container_width=True):
                st.session_state.billing_cart = []
                st.rerun()

    if st.session_state.last_bill:
        b = st.session_state.last_bill
        st.divider()
        st.subheader("🧾 GST बिल इनवॉइस व UPI QR रसीद")

        rows_html = "".join([f"<tr><td>{it['name']}<br/><small style='color:#555;'>SN: {it.get('serial_no', 'N/A')}</small></td><td>{it['qty']}</td><td>₹{it['rate']:.2f}</td><td>{it['gst_percent']}%</td><td>₹{it['total']:.2f}</td></tr>" for it in b["items"]])
        due_txt = f"<b>उधारी देय तिथि:</b> {b['due_date']}<br/>" if b.get('due_date') and b['due_date'] != 'N/A' else ""
        phone_txt = b['phone'] if b.get('phone') else 'N/A'
        gst_txt = f"<b>GSTIN:</b> {current_gstin}<br/>" if current_gstin else ""

        bill_html = f"""
        <div id="printArea" style="border: 1px solid #000; padding: 15px; width: 360px; font-family: monospace; background: #fff; color: #000; margin: auto;">
            <h3 style="text-align:center; margin:0;">{current_shop_name}</h3>
            <p style="text-align:center; margin:2px 0 10px 0; font-size:12px;">टैक्स इनवॉइस | धन्यवाद! पुनः पधारें</p>
            <hr style="border-top: 1px dashed #000;"/>
            <div style="font-size: 13px;">
                {gst_txt}
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
                <tr><th>सामान (S/N)</th><th>मात्रा</th><th>दर</th><th>GST</th><th>कुल</th></tr>
                {rows_html}
            </table>
            <hr style="border-top: 1px dashed #000;"/>
            <div style="font-size: 13px; text-align: right;">
                <b>कुल GST: ₹{b.get('total_gst', 0.0):.2f}</b><br/>
                <h3 style="margin:5px 0;">कुल राशि: ₹{b['total']:.2f}</h3>
            </div>
            <hr style="border-top: 1px dashed #000;"/>
            <div style="text-align:center;">
                <img src="{b.get('qr_url')}" width="120" style="margin:5px 0;"/>
                <p style="font-size:11px; margin:0;">PhonePe / GPay / Paytm से स्कैन करें</p>
            </div>
            <hr style="border-top: 1px dashed #000;"/>
            <p style="text-align:center; font-size:11px; margin:0;">कंप्यूटरीकृत GST रसीद | सॉफ्टवेयर जनरेटेड</p>
        </div>
        """
        st.components.v1.html(bill_html, height=520)

        print_script = f"""
        <html><body>
        <button onclick="printBill()" style="background-color:#2ed573; color:white; padding:10px 20px; font-size:15px; font-weight:bold; border:none; border-radius:5px; cursor:pointer; width:100%;">🖨️ यह GST बिल प्रिंट करें (Print / Save PDF)</button>
        <script>
        function printBill() {{
            var win = window.open('', '', 'height=650,width=450');
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
# 4. सेल्स रिटर्न व रिफंड मैनेजमेंट (New Feature)
# ==========================================
elif mode == "🔄 सेल्स रिटर्न व रिफंड":
    st.subheader("🔄 सेल्स रिटर्न, रिप्लेसमेंट एवं रिफंड काउंटर")
    st.caption("पुराने बिल नंबर से सामान वापस लें और स्टॉक को ऑटोमैटिक दुरुस्त करें")

    conn = sqlite3.connect(DB_NAME)
    ret_bill_no = st.text_input("🔍 बिल नंबर दर्ज करें (उदा. BILL-20260825...):")

    if ret_bill_no.strip():
        bill_sales = pd.read_sql_query("SELECT id, bill_no, product_id, product_name, serial_no, quantity, sell_price, gst_percent, total_amount, sold_by, customer_name, sale_date FROM sales WHERE bill_no = ?", conn, params=(ret_bill_no.strip(),))
        
        if not bill_sales.empty:
            st.success(f"✅ बिल मिला: ग्राहक '{bill_sales.iloc[0]['customer_name']}' | तारीख: {bill_sales.iloc[0]['sale_date']}")
            st.dataframe(bill_sales[["product_name", "serial_no", "quantity", "sell_price", "gst_percent", "total_amount"]].rename(columns={
                'product_name': 'सामान', 'serial_no': 'सीरियल नं', 'quantity': 'बेची गई मात्रा', 'sell_price': 'दर', 'gst_percent': 'GST %', 'total_amount': 'कुल राशि'
            }), use_container_width=True)

            with st.form("process_return_form"):
                st.markdown("#### 📦 कौन सा सामान वापस लेना है?")
                selected_item_name = st.selectbox("सामान चुनें:", bill_sales["product_name"].tolist())
                sel_row = bill_sales[bill_sales["product_name"] == selected_item_name].iloc[0]

                c_r1, c_r2 = st.columns(2)
                ret_qty = c_r1.number_input("वापसी मात्रा (Qty):", min_value=1, max_value=int(sel_row["quantity"]), value=1)
                unit_price_with_tax = float(sel_row["total_amount"]) / int(sel_row["quantity"])
                calc_refund = unit_price_with_tax * ret_qty
                c_r2.metric("रिफंड बनने वाली राशि", f"₹{calc_refund:.2f}")

                reason = st.text_input("वापसी का कारण (Reason):", placeholder="उदा. डिफेक्टिव पीस / ग्राहक ने दूसरा मॉडल लिया")

                if st.form_submit_button("🔄 रिटर्न स्वीकार करें और स्टॉक में वापस जोड़ें", type="primary", use_container_width=True):
                    c = conn.cursor()
                    # 1. स्टॉक वापस बढ़ाएं
                    c.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (int(ret_qty), int(sel_row["product_id"])))
                    # 2. रिटर्न हिस्ट्री में दर्ज करें
                    c.execute("""
                        INSERT INTO sales_returns (bill_no, product_id, product_name, returned_qty, refund_amount, return_reason, returned_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (ret_bill_no.strip(), int(sel_row["product_id"]), selected_item_name, int(ret_qty), float(calc_refund), reason.strip(), str(st.session_state.username)))
                    conn.commit()
                    st.success(f"🎉 '{selected_item_name}' (x{ret_qty}) सफलतापूर्वक वापस ले लिया गया और दुकान के स्टॉक में जुड़ गया!")
                    st.rerun()
        else:
            st.error("❌ यह बिल नंबर नहीं मिला। कृपया सही बिल नंबर डालें।")
    
    st.divider()
    st.markdown("#### 📋 हाल ही में किए गए रिटर्न्स का रिकॉर्ड (Returns History)")
    ret_history = pd.read_sql_query("SELECT * FROM sales_returns ORDER BY return_date DESC LIMIT 20", conn)
    if not ret_history.empty:
        st.dataframe(ret_history.rename(columns={
            'bill_no': 'बिल नं', 'product_name': 'सामान', 'returned_qty': 'वापस मात्रा', 'refund_amount': 'रिफंड (₹)', 'return_reason': 'कारण', 'returned_by': 'कैशियर', 'return_date': 'तारीख'
        }), use_container_width=True)
    else:
        st.info("अभी कोई रिटर्न रिकॉर्ड मौजूद नहीं है।")
    conn.close()

# ==========================================
# 5. बारकोड व QR स्टिकर प्रिंटर (New Feature)
# ==========================================
elif mode == "🏷️ बारकोड स्टिकर प्रिंटर":
    st.subheader("🏷️ प्रोडक्ट बारकोड / QR स्टिकर व प्राइस टैग जनरेटर")
    st.caption("दुकान के सामान पर चिपकाने के लिए थर्मल स्टिकर / बारकोड लेबल प्रिंट करें")

    conn = sqlite3.connect(DB_NAME)
    products_df = pd.read_sql_query("SELECT id, serial_no, name, category, sell_price, gst_percent FROM products", conn)
    
    c_set = conn.cursor()
    c_set.execute("SELECT shop_title FROM shop_settings WHERE id=1")
    s_info = c_set.fetchone()
    current_shop_name = s_info[0] if s_info else "Raju Bhaiya Store"
    conn.close()

    if not products_df.empty:
        products_df["label"] = products_df.apply(lambda r: f"{r['name']} (S/N: {r['serial_no']})" if r['serial_no'] else r['name'], axis=1)
        selected_prod_label = st.selectbox("जिस सामान का स्टिकर बनाना है चुनें:", products_df["label"].tolist())
        target_prod = products_df[products_df["label"] == selected_prod_label].iloc[0]

        col_st1, col_st2 = st.columns([1, 1])
        with col_st1:
            copies = st.number_input("कितने स्टिकर प्रिंट करने हैं?", min_value=1, max_value=50, value=6)
            show_price = st.checkbox("स्टीकर पर बिक्री मूल्य (MRP) दिखाएं", value=True)
            sn_code = target_prod["serial_no"] if target_prod["serial_no"] else f"ITEM-{target_prod['id']:06d}"
            
            # बारकोड इमेज URL (Barcode API)
            barcode_img_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={urllib.parse.quote(sn_code)}&scale=2&height=10&includetext"

        with col_st2:
            st.markdown("#### 👁️ लाइव स्टिकर प्रीव्यू:")
            price_tag_html = f"<div style='font-size:16px; font-weight:bold; color:black;'>MRP: ₹{target_prod['sell_price']:.2f}</div>" if show_price else ""
            
            single_tag_html = f"""
            <div style="border: 2px dashed #333; padding: 10px; width: 190px; text-align: center; font-family: sans-serif; background: #fff; border-radius: 6px; margin: auto;">
                <div style="font-size: 11px; font-weight: bold; color: #1E88E5; text-transform: uppercase;">{current_shop_name}</div>
                <div style="font-size: 13px; font-weight: bold; margin: 3px 0; color: #000;">{target_prod['name']}</div>
                <img src="{barcode_img_url}" style="max-width: 160px; height: 45px; margin: 4px 0;"/>
                {price_tag_html}
                <div style="font-size: 10px; color: #666;">GST {target_prod['gst_percent']}% Incl.</div>
            </div>
            """
            st.components.v1.html(single_tag_html, height=180)

        st.divider()
        st.markdown("#### 🖨️ स्टिकर प्रिंट शीट (Print Sticker Sheet)")
        
        all_tags_html = "".join([f"<div style='border: 1px solid #ccc; padding: 8px; width: 175px; text-align: center; font-family: sans-serif; background: #fff; margin: 6px; display: inline-block; border-radius: 4px;'>"
                                 f"<div style='font-size: 10px; font-weight: bold; color: #333;'>{current_shop_name}</div>"
                                 f"<div style='font-size: 12px; font-weight: bold; color: #000;'>{target_prod['name'][:20]}</div>"
                                 f"<img src='{barcode_img_url}' style='width: 140px; height: 40px; margin: 3px 0;'/>"
                                 f"{price_tag_html}"
                                 f"</div>" for _ in range(int(copies))])

        print_sheet_script = f"""
        <html><body>
        <button onclick="printLabels()" style="background-color:#1E88E5; color:white; padding:12px 24px; font-size:16px; font-weight:bold; border:none; border-radius:6px; cursor:pointer; width:100%;">🖨️ ये सभी {copies} स्टिकर प्रिंट करें (Print Barcode Sheet)</button>
        <script>
        function printLabels() {{
            var win = window.open('', '', 'height=600,width=800');
            win.document.write('<html><head><title>Print Barcodes</title></head><body style="margin:10px; font-family:sans-serif;">');
            win.document.write(`<div style="display:flex; flex-wrap:wrap;">{all_tags_html}</div>`);
            win.document.write('</body></html>');
            win.document.close();
            win.focus();
            setTimeout(function() {{ win.print(); win.close(); }}, 400);
        }}
        </script>
        </body></html>
        """
        st.components.v1.html(print_sheet_script, height=70)
    else:
        st.info("दुकान में कोई सामान नहीं है।")

# ==========================================
# 6. GSTR-1 टैक्स रिपोर्ट व E-Way Bill (New Feature)
# ==========================================
elif mode == "📄 GSTR-1 टैक्स रिपोर्ट":
    st.subheader("📄 GSTR-1 एवं सरकारी टैक्स रिटर्न रिपोर्ट")
    st.caption("GST पोर्टल के मानक अनुसार 1-क्लिक Excel / CSV फाइल डाउनलोड करें")

    conn = sqlite3.connect(DB_NAME)
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    c_set = conn.cursor()
    c_set.execute("SELECT shop_gstin, shop_title FROM shop_settings WHERE id=1")
    s_gst = c_set.fetchone()
    current_gstin = s_gst[0] if s_gst and s_gst[0] else "N/A"
    conn.close()

    if not sales_df.empty:
        sales_df["sale_date"] = pd.to_datetime(sales_df["sale_date"])
        sales_df["month_str"] = sales_df["sale_date"].dt.strftime("%m-%Y")

        c_g1, c_g2 = st.columns(2)
        all_months = sorted(sales_df["month_str"].unique().tolist(), reverse=True)
        sel_gst_month = c_g1.selectbox("📅 टैक्स फाइलिंग महीना चुनें:", all_months)
        c_g2.info(f"🏢 आपकी दुकान का GSTIN: **{current_gstin}**")

        monthly_sales = sales_df[sales_df["month_str"] == sel_gst_month]

        if not monthly_sales.empty:
            total_taxable_val = monthly_sales["sell_price"] * monthly_sales["quantity"]
            total_gst_val = monthly_sales["gst_amount"].sum()
            total_invoice_val = monthly_sales["total_amount"].sum()

            g_m1, g_m2, g_m3, g_m4 = st.columns(4)
            g_m1.metric("कुल इनवॉइस वैल्यू", f"₹{total_invoice_val:.2f}")
            g_m2.metric("कर योग्य मूल्य (Taxable)", f"₹{total_taxable_val.sum():.2f}")
            g_m3.metric("कुल एकत्रित GST", f"₹{total_gst_val:.2f}")
            g_m4.metric("कुल काटे गए इनवॉइस", f"{monthly_sales['bill_no'].nunique()} बिल्स")

            st.divider()

            # GSTR-1 B2C / B2B फॉर्मेट टेबल
            gstr1_df = pd.DataFrame({
                "Invoice Number": monthly_sales["bill_no"],
                "Invoice Date": monthly_sales["sale_date"].dt.strftime("%d-%b-%Y"),
                "Customer Name": monthly_sales["customer_name"],
                "Item Description": monthly_sales["product_name"],
                "Quantity": monthly_sales["quantity"],
                "Taxable Value (Rs)": (monthly_sales["sell_price"] * monthly_sales["quantity"]).round(2),
                "GST Rate (%)": monthly_sales["gst_percent"],
                "CGST Amount (Rs)": (monthly_sales["gst_amount"] / 2.0).round(2),
                "SGST Amount (Rs)": (monthly_sales["gst_amount"] / 2.0).round(2),
                "Total GST (Rs)": monthly_sales["gst_amount"].round(2),
                "Total Invoice Value (Rs)": monthly_sales["total_amount"].round(2),
                "Place of Supply": "Madhya Pradesh (23)"
            })

            st.markdown(f"#### 📋 {sel_gst_month} की GSTR-1 टेबल-वाइज समरी:")
            st.dataframe(gstr1_df, use_container_width=True)

            # CSV / Excel Download Buttons
            csv_data = gstr1_df.to_csv(index=False).encode('utf-8')
            
            c_d1, c_d2 = st.columns(2)
            c_d1.download_button(
                label=f"📥 GSTR-1 रिपोर्ट डाउनलोड करें (CSV Format)",
                data=csv_data,
                file_name=f"GSTR1_Report_{sel_gst_month}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
            
            with c_d2:
                # HSN Summary Table
                hsn_summary = monthly_sales.groupby("product_name").agg(
                    Total_Qty=('quantity', 'sum'),
                    Total_Taxable=('sell_price', lambda x: (x * monthly_sales.loc[x.index, 'quantity']).sum()),
                    Total_GST=('gst_amount', 'sum'),
                    Total_Value=('total_amount', 'sum')
                ).reset_index()
                hsn_csv = hsn_summary.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 HSN समरी रिपोर्ट डाउनलोड करें (CSV)",
                    data=hsn_csv,
                    file_name=f"HSN_Summary_{sel_gst_month}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.warning("इस महीने में कोई बिक्री दर्ज नहीं है।")
    else:
        st.info("अभी कोई बिक्री रिकॉर्ड मौजूद नहीं है।")

# ==========================================
# 7. नया स्टॉक / प्रोडक्ट जोड़ें
# ==========================================
elif mode == "➕ नया स्टॉक / प्रोडक्ट जोड़ें":
    st.subheader("➕ नया सामान स्टॉक एवं ऑनलाइन स्टोर में जोड़ें")
    
    c_sn_top1, c_sn_top2 = st.columns([3, 1])
    with c_sn_top2:
        if st.button("🎲 नया सीरियल नंबर बनाएं (Auto Gen)", use_container_width=True):
            st.session_state.gen_serial_code = f"SN-{random.randint(100000, 999999)}"
            st.rerun()

    with st.form("add_item_form", clear_on_submit=True):
        c_s1, c_s2 = st.columns([2, 2])
        serial_no_in = c_s1.text_input("सामान का सीरियल नंबर / बारकोड (Serial No. / SKU)", value=st.session_state.gen_serial_code)
        name = c_s2.text_input("सामान का नाम *", placeholder="उदा. 65W Fast Data Cable / 12x18 Photo Frame")
        
        c1, c2, c3 = st.columns(3)
        category = c1.text_input("कैटेगरी *", value="जनरल")
        hsn = c2.text_input("HSN / SAC कोड", value="8504")
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
                    INSERT INTO products (serial_no, name, category, hsn_code, buy_price, sell_price, gst_percent, stock, min_alert, description, image_url, is_online)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (serial_no_in.strip(), name.strip(), category.strip(), hsn.strip(), buy_p, sell_p, float(gst_slab), stock, alert, desc.strip(), final_photo_data, 1 if is_on else 0))
                conn.commit()
                conn.close()
                st.success(f"✅ '{name}' (S/N: {serial_no_in}) सफलतापूर्वक स्टॉक में जुड़ गया!")
                st.session_state.gen_serial_code = f"SN-{random.randint(100000, 999999)}"

# ==========================================
# 8. स्टॉक व ऑनलाइन शो
# ==========================================
elif mode == "📦 स्टॉक व ऑनलाइन शो":
    st.subheader("📦 दुकान का लाइव स्टॉक एवं GST लिस्टिंग")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, serial_no, name, category, hsn_code, buy_price, sell_price, gst_percent, stock, min_alert, is_online FROM products", conn)
    conn.close()

    search = st.text_input("🔍 सामान या सीरियल नंबर सर्च करें")
    if search:
        df = df[df["name"].str.contains(search, case=False, na=False) | df["serial_no"].str.contains(search, case=False, na=False)]

    st.dataframe(df.rename(columns={
        "serial_no": "सीरियल नं",
        "name": "सामान",
        "category": "कैटेगरी",
        "hsn_code": "HSN कोड",
        "buy_price": "खरीद दर (₹)",
        "sell_price": "बिक्री दर (₹)",
        "gst_percent": "GST %",
        "stock": "स्टॉक मात्रा",
        "min_alert": "अलर्ट सीमा",
        "is_online": "ऑनलाइन शो (1=हाँ, 0=ना)"
    }), use_container_width=True)

# ==========================================
# 9. उधारी/खाता अलर्ट
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
# 10. ऑपरेटर बिक्री रिपोर्ट
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
# 11. ऑपरेटर मासिक कमीशन
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
# 12. एडमिन डैशबोर्ड
# ==========================================
elif mode == "📊 एडमिन डैशबोर्ड":
    st.markdown("<h2 style='margin-bottom:0px;'>📊 एंटरप्राइज बिज़नेस इंटेलिजेंस व एनालिटिक्स</h2>", unsafe_allow_html=True)
    st.caption("रियल-टाइम वित्तीय विश्लेषण, इन्वेंटरी हेल्थ और परफॉरमेंस इनसाइट्स")

    conn = sqlite3.connect(DB_NAME)
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    udhar_df = pd.read_sql_query("SELECT * FROM udhar_ledger", conn)
    conn.close()

    if not sales_df.empty:
        sales_df["sale_date"] = pd.to_datetime(sales_df["sale_date"])
        now = datetime.now()

        today_sales = sales_df[sales_df["sale_date"].dt.date == now.date()]
        total_rev = sales_df["total_amount"].sum()
        total_prof = sales_df["profit"].sum()
        margin_pct = (total_prof / total_rev * 100) if total_rev > 0 else 0.0
        
        pending_udhar_total = (udhar_df[udhar_df["status"] == "PENDING"]["total_amount"] - udhar_df[udhar_df["status"] == "PENDING"]["paid_amount"]).sum() if not udhar_df.empty else 0.0
        stock_buy_val = (products_df["stock"] * products_df["buy_price"]).sum() if not products_df.empty else 0.0
        stock_sell_val = (products_df["stock"] * products_df["sell_price"]).sum() if not products_df.empty else 0.0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("💵 आज की बिक्री", f"₹{today_sales['total_amount'].sum():.2f}", f"मुनाफ़ा: ₹{today_sales['profit'].sum():.2f}")
        k2.metric("💰 कुल शुद्ध मुनाफ़ा", f"₹{total_prof:.2f}", f"मार्जिन: {margin_pct:.1f}%")
        k3.metric("📦 इन्वेंटरी वैल्यूएशन", f"₹{stock_buy_val:.2f}", f"बिक्री मूल्य: ₹{stock_sell_val:.2f}")
        k4.metric("📒 मार्केट में उधारी", f"₹{pending_udhar_total:.2f}", "बकाया वसूली")
        k5.metric("🧾 कुल काटे गए बिल", f"{sales_df['bill_no'].nunique()} बिल", f"{sales_df['quantity'].sum()} कुल पीस")

        st.divider()

        tab_rev, tab_prod, tab_inv, tab_udhar, tab_staff = st.tabs([
            "📈 1. सेल व रेवेन्यू ट्रैकर",
            "🏆 2. प्रोडक्ट परफॉरमेंस (Fast vs Slow)",
            "📦 3. इन्वेंटरी व स्टॉक हेल्थ",
            "📒 4. उधारी व रिकवरी रिपोर्ट",
            "👔 5. ऑपरेटर लीडरबोर्ड"
        ])

        with tab_rev:
            daily_grp = sales_df.groupby(sales_df["sale_date"].dt.date).agg(
                कुल_बिक्री=('total_amount', 'sum'),
                शुद्ध_मुनाफा=('profit', 'sum')
            ).reset_index().rename(columns={'sale_date': 'तारीख'})

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=daily_grp['तारीख'], y=daily_grp['कुल_बिक्री'], mode='lines+markers', name='बिक्री (₹)', line=dict(color='#1E88E5', width=3)))
            fig_trend.add_trace(go.Scatter(x=daily_grp['तारीख'], y=daily_grp['शुद्ध_मुनाफा'], mode='lines+markers', name='मुनाफ़ा (₹)', line=dict(color='#2ed573', width=3)))
            fig_trend.update_layout(height=340, margin=dict(l=20, r=20, t=30, b=20), hovermode='x unified')
            st.plotly_chart(fig_trend, use_container_width=True)

            c_p1, c_p2 = st.columns([1, 1])
            with c_p1:
                st.markdown("#### 💳 पेमेंट मोड ब्रेकडाउन")
                pay_grp = sales_df.groupby("payment_mode")["total_amount"].sum().reset_index()
                fig_pay = px.pie(pay_grp, names="payment_mode", values="total_amount", hole=0.45)
                st.plotly_chart(fig_pay, use_container_width=True)
            with c_p2:
                st.markdown("#### 🕒 घंटे के हिसाब से बिक्री (Peak Hours)")
                sales_df['hour'] = sales_df['sale_date'].dt.hour
                hr_grp = sales_df.groupby('hour')['total_amount'].sum().reset_index()
                fig_hr = px.bar(hr_grp, x='hour', y='total_amount', labels={'hour': 'समय (24 घंटे)', 'total_amount': 'बिक्री (₹)'}, color='total_amount')
                st.plotly_chart(fig_hr, use_container_width=True)

        with tab_prod:
            col_tp1, col_tp2 = st.columns(2)
            prod_perf = sales_df.groupby("product_name").agg(
                बिका_स्टॉक=('quantity', 'sum'),
                कुल_सेल=('total_amount', 'sum'),
                कमाई=('profit', 'sum')
            ).reset_index()

            with col_tp1:
                st.markdown("#### 🔥 सबसे ज़्यादा बिकने वाले सामान (Top Selling)")
                top_10 = prod_perf.sort_values(by="बिका_स्टॉक", ascending=False).head(10)
                st.dataframe(top_10.rename(columns={'product_name': 'सामान', 'बिका_स्टॉक': 'कुल पीस', 'कुल_सेल': 'बिक्री (₹)', 'कमाई': 'मुनाफ़ा (₹)'}), use_container_width=True)

            with col_tp2:
                st.markdown("#### 💎 सबसे ज़्यादा मुनाफ़ा देने वाले सामान (Most Profitable)")
                top_prof = prod_perf.sort_values(by="कमाई", ascending=False).head(10)
                st.dataframe(top_prof.rename(columns={'product_name': 'सामान', 'बिका_स्टॉक': 'कुल पीस', 'कुल_सेल': 'बिक्री (₹)', 'कमाई': 'मुनाफ़ा (₹)'}), use_container_width=True)

            st.divider()
            st.markdown("#### ⚠️ कम बिकने वाले / न बिकने वाले सामान (Slow Moving & Dead Stock)")
            sold_ids = sales_df["product_id"].unique()
            dead_stock = products_df[~products_df["id"].isin(sold_ids)]
            if not dead_stock.empty:
                st.warning(f"🚨 कुल {len(dead_stock)} सामान ऐसे हैं जिनकी एक भी यूनिट नहीं बिकी है!")
                st.dataframe(dead_stock[["serial_no", "name", "category", "stock", "buy_price", "sell_price"]], use_container_width=True)
            else:
                st.success("🎉 दुकान के सभी सामान सक्रिय रूप से बिक रहे हैं।")

        with tab_inv:
            st.markdown("#### 📦 स्टॉक अलर्ट व इन्वेंटरी हेल्थ रिपोर्ट")
            low_stock_items = products_df[products_df["stock"] <= products_df["min_alert"]]
            c_in1, c_in2 = st.columns(2)
            with c_in1:
                if not low_stock_items.empty:
                    st.error(f"🚨 रिऑर्डर करें: {len(low_stock_items)} सामान कम स्टॉक सीमा पर हैं!")
                    st.dataframe(low_stock_items[["name", "stock", "min_alert", "buy_price"]], use_container_width=True)
                else:
                    st.success("दुकान के सभी सामान पर्याप्त स्टॉक में हैं।")
            with c_in2:
                cat_grp = products_df.groupby("category")["stock"].sum().reset_index()
                fig_cat = px.pie(cat_grp, names="category", values="stock", hole=0.3)
                st.plotly_chart(fig_cat, use_container_width=True)

        with tab_udhar:
            st.markdown("#### 📒 ग्राहक उधारी रिकवरी ट्रैकिंग")
            if not udhar_df.empty:
                udhar_df["due_date_dt"] = pd.to_datetime(udhar_df["due_date"])
                udhar_df["baki"] = udhar_df["total_amount"] - udhar_df["paid_amount"]
                total_market_udhar = udhar_df[udhar_df["status"] == "PENDING"]["baki"].sum()
                recovered_total = udhar_df[udhar_df["status"] == "PAID"]["total_amount"].sum()
                
                u_m1, u_m2 = st.columns(2)
                u_m1.metric("कुल बकाया उधारी", f"₹{total_market_udhar:.2f}")
                u_m2.metric("कुल रिकवर राशि", f"₹{recovered_total:.2f}")

                st.dataframe(udhar_df[["bill_no", "customer_name", "customer_phone", "total_amount", "baki", "due_date", "status"]], use_container_width=True)
            else:
                st.success("दुकान में किसी ग्राहक की कोई उधारी नहीं है।")

        with tab_staff:
            st.markdown("#### 🏆 ऑपरेटर परफॉरमेंस व रेवेन्यू रैंकिंग")
            staff_grp = sales_df.groupby("sold_by").agg(
                कुल_बिल=('bill_no', 'nunique'),
                कुल_बिक्री=('total_amount', 'sum'),
                शुद्ध_कमाई=('profit', 'sum')
            ).reset_index().sort_values(by="कुल_बिक्री", ascending=False)
            
            c_st1, c_st2 = st.columns([1, 1])
            with c_st1:
                st.dataframe(staff_grp.rename(columns={'sold_by': 'ऑपरेटर', 'कुल_बिल': 'बिल काटे', 'कुल_बिक्री': 'सेल (₹)', 'शुद्ध_कमाई': 'मुनाफ़ा (₹)'}), use_container_width=True)
            with c_st2:
                fig_staff = px.bar(staff_grp, x="sold_by", y="कुल_बिक्री", color="शुद्ध_कमाई", title="स्टाफ सेल तुलना")
                st.plotly_chart(fig_staff, use_container_width=True)
    else:
        st.info("📊 बिज़नेस एनालिटिक्स डैशबोर्ड देखने के लिए पहले कुछ बिल काटें।")

# ==========================================
# 13. ऑपरेटर मैनेजमेंट
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
                    is_checked = perm in ["🛍️ ऑनलाइन स्टोर देखें", "⚡ सुपरफास्ट POS बिलिंग", "📦 स्टॉक व ऑनलाइन शो"]
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
# 14. स्टोर सेटिंग्स
# ==========================================
elif mode == "🎨 स्टोर बैनर व सेटिंग्स":
    st.subheader("🎨 ऑनलाइन स्टोर ब्रांडिंग, GSTIN व UPI सेटिंग्स")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT shop_title, shop_subtitle, shop_phone, upi_id, shop_gstin, banner_image FROM shop_settings WHERE id=1")
    current_settings = c.fetchone()
    conn.close()
    
    cur_title = current_settings[0] if current_settings else "Raju Bhaiya Online Store"
    cur_sub = current_settings[1] if current_settings else "डिजिटल प्रोडक्ट कैटलॉग एवं ऑनलाइन ऑर्डर"
    cur_phone = current_settings[2] if current_settings and current_settings[2] else "8349596263"
    cur_upi = current_settings[3] if current_settings and current_settings[3] else "8349596263@upi"
    cur_gstin = current_settings[4] if current_settings and len(current_settings) > 4 and current_settings[4] else ""
    cur_banner = current_settings[5] if current_settings and len(current_settings) > 5 else ""

    with st.form("shop_settings_form"):
        st.markdown("#### 1. दुकान / स्टोर का नाम एवं संपर्क")
        c_st1, c_st2 = st.columns(2)
        new_title = c_st1.text_input("स्टोर का नाम (Store Title)", value=cur_title)
        new_phone = c_st2.text_input("स्टोर संपर्क नंबर (Mobile / WhatsApp No.) *", value=cur_phone, max_chars=10)
        
        c_st3, c_st4 = st.columns(2)
        new_upi = c_st3.text_input("💳 दुकान की UPI ID *", value=cur_upi)
        new_gstin = c_st4.text_input("🏢 GSTIN नंबर (यदि लागू हो)", value=cur_gstin, placeholder="उदा. 23AAAAA0000A1Z5")
        
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
            c.execute("UPDATE shop_settings SET shop_title=?, shop_subtitle=?, shop_phone=?, upi_id=?, shop_gstin=?, banner_image=? WHERE id=1", (new_title.strip(), new_sub.strip(), new_phone.strip(), new_upi.strip(), new_gstin.strip(), final_banner_data))
            conn.commit()
            conn.close()
            st.success("✅ ऑनलाइन स्टोर का नाम, GSTIN, संपर्क नंबर, UPI ID और फोटो अपडेट हो गया!")
            st.rerun()# ==========================================
# ==========================================
# 5. बारकोड व QR स्टिकर प्रिंटर (रीप्रिंट व कस्टम रेंज सपोर्ट सहित)
# ==========================================
elif mode == "🏷️ बारकोड स्टिकर प्रिंटर":
    st.subheader("🏷️ प्रोडक्ट बारकोड स्टिकर व प्राइस टैग जनरेटर")
    st.caption("यूनिक सीरियल नंबर बारकोड प्रिंट करें अथवा खराब हुए स्टिकर दोबारा निकालें")

    conn = sqlite3.connect(DB_NAME)
    products_df = pd.read_sql_query("SELECT id, serial_no, name, category, sell_price, gst_percent FROM products", conn)
    
    c_set = conn.cursor()
    c_set.execute("SELECT shop_title FROM shop_settings WHERE id=1")
    s_info = c_set.fetchone()
    current_shop_name = s_info[0] if s_info else "Raju Bhaiya Store"
    conn.close()

    if not products_df.empty:
        products_df["label"] = products_df.apply(lambda r: f"{r['name']} (S/N: {r['serial_no']})" if r['serial_no'] else r['name'], axis=1)
        selected_prod_label = st.selectbox("जिस सामान का स्टिकर बनाना है चुनें:", products_df["label"].tolist())
        target_prod = products_df[products_df["label"] == selected_prod_label].iloc[0]

        base_sn = str(target_prod["serial_no"]).strip() if target_prod["serial_no"] else f"ITEM{target_prod['id']:04d}"
        
        col_st1, col_st2 = st.columns([1, 1])
        with col_st1:
            print_action = st.radio(
                "प्रिंट विकल्प चुनें:",
                [
                    "🆕 नए स्टिकर प्रिंट करें (1 से शुरू)",
                    "🔄 खराब हुए स्टिकर दोबारा निकालें (Reprint Custom Range)",
                    "🏷️ सभी स्टिकर पर एक जैसा कोड (Same Batch/SKU)"
                ]
            )
            
            generated_codes = []
            
            if print_action == "🆕 नए स्टिकर प्रिंट करें (1 से शुरू)":
                copies = st.number_input("कितने स्टिकर प्रिंट करने हैं?", min_value=1, max_value=60, value=6)
                for i in range(1, int(copies) + 1):
                    generated_codes.append(f"{base_sn}-{i:02d}")
                    
            elif print_action == "🔄 खराब हुए स्टिकर दोबारा निकालें (Reprint Custom Range)":
                st.warning("⚠️ जो स्टिकर खराब हुए हैं उनका नंबर रेंज चुनें:")
                c_rn1, c_rn2 = st.columns(2)
                start_num = c_rn1.number_input("कहाँ से (From S/N No.):", min_value=1, max_value=100, value=3)
                end_num = c_rn2.number_input("कहाँ तक (To S/N No.):", min_value=int(start_num), max_value=100, value=5)
                
                for i in range(int(start_num), int(end_num) + 1):
                    generated_codes.append(f"{base_sn}-{i:02d}")
                copies = len(generated_codes)
                
            else:
                copies = st.number_input("कितने स्टिकर प्रिंट करने हैं?", min_value=1, max_value=60, value=6)
                generated_codes = [base_sn] * int(copies)

            show_price = st.checkbox("स्टीकर पर बिक्री मूल्य (MRP) दिखाएं", value=True)
            
            if generated_codes:
                st.info(f"💡 कुल प्रिंट होने वाले स्टिकर: **{len(generated_codes)}** (कोड: `{generated_codes[0]}` से `{generated_codes[-1]}`)")

        with col_st2:
            st.markdown("#### 👁️ लाइव स्टिकर प्रीव्यू:")
            sample_code = generated_codes[0] if generated_codes else base_sn
            price_display = f"<div style='font-size:15px; font-weight:bold; color:#000;'>MRP: ₹{target_prod['sell_price']:.2f}</div>" if show_price else ""
            
            preview_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
                <style>
                    body {{ margin: 0; background: transparent; display: flex; justify-content: center; align-items: center; }}
                    .tag-box {{
                        border: 2px dashed #1E88E5;
                        padding: 10px;
                        width: 210px;
                        text-align: center;
                        font-family: Arial, sans-serif;
                        background: #ffffff;
                        border-radius: 8px;
                    }}
                    .shop-title {{ font-size: 11px; font-weight: bold; color: #1E88E5; text-transform: uppercase; margin-bottom: 2px; }}
                    .prod-title {{ font-size: 13px; font-weight: bold; color: #111; margin-bottom: 4px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
                    svg {{ max-width: 190px; height: 50px; }}
                    .tax-info {{ font-size: 10px; color: #666; margin-top: 2px; }}
                </style>
            </head>
            <body>
                <div class="tag-box">
                    <div class="shop-title">{current_shop_name}</div>
                    <div class="prod-title">{target_prod['name']}</div>
                    <svg id="preview_barcode"></svg>
                    {price_display}
                    <div class="tax-info">GST {target_prod['gst_percent']}% Incl.</div>
                </div>
                <script>
                    JsBarcode("#preview_barcode", "{sample_code}", {{
                        format: "CODE128",
                        width: 2,
                        height: 40,
                        displayValue: true,
                        fontSize: 13,
                        margin: 0
                    }});
                </script>
            </body>
            </html>
            """
            st.components.v1.html(preview_html, height=190)

        st.divider()
        st.markdown(f"#### 🖨️ {len(generated_codes)} बारकोड स्टिकर प्रिंट शीट:")

        tags_script_loop = "".join([f'JsBarcode("#barcode_{i}", "{code}", {{ format: "CODE128", width: 1.8, height: 38, displayValue: true, fontSize: 12, margin: 0 }});\n' for i, code in enumerate(generated_codes)])
        
        tags_divs_loop = "".join([f"""
        <div style='border: 1px solid #000; padding: 6px; width: 180px; text-align: center; font-family: Arial, sans-serif; background: #fff; margin: 5px; display: inline-block; border-radius: 4px; page-break-inside: avoid;'>
            <div style='font-size: 10px; font-weight: bold; color: #1E88E5;'>{current_shop_name}</div>
            <div style='font-size: 12px; font-weight: bold; color: #000; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;'>{target_prod['name']}</div>
            <svg id='barcode_{i}' style='max-width: 165px; height: 45px;'></svg>
            {price_display}
        </div>
        """ for i, _ in enumerate(generated_codes)])

        btn_text = f"🖨️ केवल खराब हुए {len(generated_codes)} स्टिकर रीप्रिंट करें" if print_action == "🔄 खराब हुए स्टिकर दोबारा निकालें (Reprint Custom Range)" else f"🖨️ ये सभी {len(generated_codes)} स्टिकर प्रिंट करें"

        print_sheet_script = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
        </head>
        <body style="margin:0; padding:0;">
            <button onclick="printLabels()" style="background-color:#1E88E5; color:white; padding:12px 24px; font-size:16px; font-weight:bold; border:none; border-radius:6px; cursor:pointer; width:100%;">{btn_text}</button>
            <script>
            function printLabels() {{
                var win = window.open('', '', 'height=650,width=850');
                win.document.write(`
                    <html>
                    <head>
                        <title>Print Barcode Stickers</title>
                        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"><\/script>
                        <style>
                            body {{ margin: 10px; font-family: Arial, sans-serif; }}
                            .print-grid {{ display: flex; flex-wrap: wrap; justify-content: flex-start; }}
                            @media print {{
                                button {{ display: none; }}
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="print-grid">
                            {tags_divs_loop}
                        </div>
                        <script>
                            {tags_script_loop}
                            setTimeout(function() {{ window.print(); window.close(); }}, 500);
                        <\/script>
                    </body>
                    </html>
                `);
                win.document.close();
                win.focus();
            }}
            </script>
        </body>
        </html>
        """
        st.components.v1.html(print_sheet_script, height=70)
    else:
        st.info("दुकान में कोई सामान नहीं है।")