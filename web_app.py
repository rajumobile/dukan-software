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
            lock_operator_price INTEGER DEFAULT 1,
            banner_image TEXT DEFAULT ''
        )
    """)

    # पुराने डेटाबेस में नए कॉलम्स ऑटो-अपग्रेड (INSERT से पहले जोड़ना जरूरी है)
    def add_col(tbl, col, typ):
        try:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass

    add_col("shop_settings", "lock_operator_price", "INTEGER DEFAULT 1")
    add_col("shop_settings", "shop_gstin", "TEXT DEFAULT ''")
    add_col("shop_settings", "upi_id", "TEXT DEFAULT '8349596263@upi'")
    add_col("shop_settings", "shop_phone", "TEXT DEFAULT '8349596263'")

    c.execute("INSERT OR IGNORE INTO shop_settings (id, shop_title, shop_subtitle, shop_phone, shop_gstin, upi_id, lock_operator_price, banner_image) VALUES (1, 'Raju Bhaiya Online Store', 'डिजिटल प्रोडक्ट कैटलॉग एवं ऑनलाइन ऑर्डर', '8349596263', '', '8349596263@upi', 1, '')")

    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        CREATE TABLE IF NOT EXISTS item_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            serial_no TEXT UNIQUE,
            status TEXT DEFAULT 'IN_STOCK',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    add_col("products", "hsn_code", "TEXT DEFAULT '8504'")
    add_col("sales", "serial_no", "TEXT DEFAULT ''")
    add_col("users", "phone", "TEXT DEFAULT ''")
    add_col("users", "commission_percent", "REAL DEFAULT 0")
    add_col("users", "permissions", "TEXT DEFAULT '[]'")
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
    search_query = col_s1.text_input("🔍 सामान खोजें", placeholder="सामान का नाम लिखें...")
    
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
# 3. सुपरफास्ट POS बारकोड बिलिंग (घाटा अलर्ट व फिक्स रेट लॉक सहित)
# ==========================================
elif mode in ["⚡ सुपरफास्ट POS बिलिंग", "💰 मल्टी-आइटम बिलिंग"]:
    st.subheader("⚡ सुपरफास्ट POS बारकोड बिलिंग काउंटर")
    
    conn = sqlite3.connect(DB_NAME)
    prods = pd.read_sql_query("SELECT id, name, sell_price, gst_percent, stock, buy_price FROM products WHERE stock > 0", conn)
    
    c_set = conn.cursor()
    c_set.execute("SELECT shop_title, shop_phone, upi_id, shop_gstin, lock_operator_price FROM shop_settings WHERE id=1")
    s_info = c_set.fetchone()
    current_shop_name = s_info[0] if s_info else "Raju Bhaiya Store"
    current_shop_phone = s_info[1] if s_info and s_info[1] else "8349596263"
    current_upi_id = s_info[2] if s_info and s_info[2] else "8349596263@upi"
    current_gstin = s_info[3] if s_info and s_info[3] else ""
    is_price_locked = bool(s_info[4]) if s_info and s_info[4] is not None else True

    c_comm = conn.cursor()
    c_comm.execute("SELECT commission_percent FROM users WHERE username=?", (st.session_state.username,))
    row_comm = c_comm.fetchone()
    op_comm_rate = float(row_comm[0]) if row_comm and row_comm[0] else 0.0
    conn.close()

    col_c1, col_c2 = st.columns(2)
    cust_name = col_c1.text_input("ग्राहक का नाम", value="नकद ग्राहक")
    cust_phone = col_c2.text_input("ग्राहक का मोबाइल नंबर", value="")

    st.markdown("---")
    
    st.markdown("#### ⚡ 1. बारकोड स्कैनर से तुरंत जोड़ें (Scan Barcode & Enter)")
    with st.form("barcode_scan_form", clear_on_submit=True):
        sc_col1, sc_col2 = st.columns([3, 1])
        scanned_code = sc_col1.text_input("⚡ बारकोड / सीरियल नंबर स्कैन करें:", placeholder="बारकोड स्कैनर बीप करें या टाइप करें...")
        scan_submit = sc_col2.form_submit_button("⚡ स्कैन कर बिल में जोड़ें", use_container_width=True)

        if scan_submit and scanned_code.strip():
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("""
                SELECT u.id, u.product_id, u.serial_no, p.name, p.sell_price, p.buy_price, p.gst_percent, p.stock
                FROM item_units u
                JOIN products p ON u.product_id = p.id
                WHERE u.serial_no = ? AND u.status = 'IN_STOCK'
            """, (scanned_code.strip(),))
            matched_unit = c.fetchone()
            conn.close()

            if matched_unit:
                unit_id, p_id, s_no, p_name, s_price, b_price, gst_p, p_stock = matched_unit
                already_scanned_serials = [it["serial_no"] for it in st.session_state.billing_cart]
                
                if s_no in already_scanned_serials:
                    st.warning(f"⚠️ यह पीस (S/N: {s_no}) पहले से बिल में जुड़ा हुआ है!")
                else:
                    base_rate = float(s_price)
                    gst_amt = (base_rate * float(gst_p)) / 100.0
                    net_item_profit = base_rate - float(b_price)
                    calc_commission = (net_item_profit * op_comm_rate) / 100.0 if net_item_profit > 0 else 0.0

                    st.session_state.billing_cart.append({
                        "unit_id": int(unit_id),
                        "id": int(p_id),
                        "serial_no": str(s_no),
                        "name": str(p_name),
                        "qty": 1,
                        "rate": base_rate,
                        "buy_price": float(b_price),
                        "gst_percent": float(gst_p),
                        "gst_amount": float(gst_amt),
                        "total": base_rate + gst_amt,
                        "profit": net_item_profit,
                        "commission": calc_commission
                    })
                    st.success(f"⚡ '{p_name}' (S/N: {s_no}) बिल में जुड़ गया!")
                    st.rerun()
            else:
                st.error(f"❌ '{scanned_code}' सीरियल नंबर उपलब्ध नहीं है या पहले ही बिक चुका है!")

    st.markdown("#### 🛒 2. या मेन्यू से सामान चुनें (Manual Select)")
    if not prods.empty:
        selected_prod = st.selectbox("सामान चुनें", prods["name"].tolist())
        item_data = prods[prods["name"] == selected_prod].iloc[0]

        already_in_cart = sum(item["qty"] for item in st.session_state.billing_cart if item["id"] == int(item_data["id"]))
        avail_stock = int(item_data["stock"]) - already_in_cart

        col1, col2, col3, col4 = st.columns([1, 2, 1, 2])
        max_allowed = max(1, avail_stock)
        qty = col1.number_input("मात्रा", min_value=1, max_value=max_allowed, value=1, disabled=(avail_stock <= 0))
        
        # ऑपरेटर के लिए लॉक स्थिति चेक
        rate_disabled = is_price_locked and (st.session_state.role != "admin")
        rate = col2.number_input("बिक्री दर (₹)", min_value=0.0, value=float(item_data["sell_price"]), disabled=rate_disabled)
        gst_p = col3.number_input("GST %", min_value=0.0, value=float(item_data["gst_percent"]), step=1.0)
        
        # ⚠️ घाटा (Loss) और कम दर अलर्ट नोटिफिकेशन
        fixed_price = float(item_data["sell_price"])
        cost_price = float(item_data["buy_price"])
        
        if rate < cost_price:
            per_piece_loss = cost_price - rate
            st.error(f"🚨 **चेतावनी (Loss Alert):** यह सामान खरीद मूल्य (₹{cost_price:.2f}) से कम पर बेचा जा रहा है! आपको प्रति पीस **₹{per_piece_loss:.2f} का घाटा (नुकसान)** होगा!")
        elif rate < fixed_price:
            reduced_margin = fixed_price - rate
            st.warning(f"⚠️ **ध्यान दें:** निर्धारित मूल्य ₹{fixed_price:.2f} से ₹{reduced_margin:.2f} कम दर पर बेचा जा रहा है!")

        with col4:
            st.write(f"दुकान में शेष: **{max(0, avail_stock)}** पीस")
            if st.button("➕ लिस्ट में जोड़ें", use_container_width=True, disabled=(avail_stock <= 0)):
                if avail_stock < qty:
                    st.error("स्टॉक पर्याप्त नहीं है!")
                elif rate < cost_price and st.session_state.role != "admin":
                    st.error("❌ ऑपरेटर को घाटे में सामान बेचने की अनुमति नहीं है!")
                else:
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("SELECT id, serial_no FROM item_units WHERE product_id = ? AND status = 'IN_STOCK' LIMIT ?", (int(item_data["id"]), int(qty)))
                    available_units = c.fetchall()
                    conn.close()

                    for u_row in available_units:
                        base_total = rate
                        gst_amt = (base_total * gst_p) / 100.0
                        net_item_profit = rate - cost_price
                        calc_commission = (net_item_profit * op_comm_rate) / 100.0 if net_item_profit > 0 else 0.0

                        st.session_state.billing_cart.append({
                            "unit_id": int(u_row[0]),
                            "id": int(item_data["id"]),
                            "serial_no": str(u_row[1]),
                            "name": str(item_data["name"]),
                            "qty": 1,
                            "rate": float(rate),
                            "buy_price": cost_price,
                            "gst_percent": float(gst_p),
                            "gst_amount": float(gst_amt),
                            "total": float(base_total + gst_amt),
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
                        if item.get("unit_id"):
                            cursor.execute("UPDATE item_units SET status = 'SOLD' WHERE id = ?", (int(item["unit_id"]),))
                        elif item.get("serial_no"):
                            cursor.execute("UPDATE item_units SET status = 'SOLD' WHERE serial_no = ?", (str(item["serial_no"]),))
                        
                        cursor.execute("UPDATE products SET stock = stock - 1 WHERE id = ?", (int(item["id"]),))
                        
                        cursor.execute("""
                            INSERT INTO sales (bill_no, product_id, serial_no, product_name, quantity, sell_price, gst_percent, gst_amount, total_amount, profit, operator_commission, sold_by, customer_name, customer_phone, payment_mode, due_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (bill_no, int(item["id"]), str(item.get("serial_no", "")), item["name"], 1, float(item["rate"]), float(item["gst_percent"]), float(item["gst_amount"]), float(item["total"]), float(item["profit"]), float(item.get("commission", 0.0)), str(st.session_state.username), str(cust_name), str(cust_phone), str(payment_mode), str(due_date_val) if due_date_val else ""))

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

# ==========================================
# 4. सेल्स रिटर्न व रिफंड मैनेजमेंट
# ==========================================
elif mode == "🔄 सेल्स रिटर्न व रिफंड":
    st.subheader("🔄 सेल्स रिटर्न, रिप्लेसमेंट एवं रिफंड काउंटर")
    conn = sqlite3.connect(DB_NAME)
    ret_bill_no = st.text_input("🔍 बिल नंबर दर्ज करें (उदा. BILL-20260825...):")

    if ret_bill_no.strip():
        bill_sales = pd.read_sql_query("SELECT id, bill_no, product_id, product_name, serial_no, quantity, sell_price, gst_percent, total_amount, sold_by, customer_name, sale_date FROM sales WHERE bill_no = ?", conn, params=(ret_bill_no.strip(),))
        
        if not bill_sales.empty:
            st.success(f"✅ बिल मिला: ग्राहक '{bill_sales.iloc[0]['customer_name']}'")
            st.dataframe(bill_sales[["product_name", "serial_no", "sell_price", "gst_percent", "total_amount"]], use_container_width=True)

            with st.form("process_return_form"):
                selected_item_name = st.selectbox("वापस लेने वाला सामान चुनें:", bill_sales["product_name"].tolist())
                sel_row = bill_sales[bill_sales["product_name"] == selected_item_name].iloc[0]
                reason = st.text_input("वापसी का कारण (Reason):", placeholder="उदा. डिफेक्टिव पीस")

                if st.form_submit_button("🔄 रिटर्न स्वीकार करें", type="primary", use_container_width=True):
                    c = conn.cursor()
                    c.execute("UPDATE products SET stock = stock + 1 WHERE id = ?", (int(sel_row["product_id"]),))
                    if sel_row["serial_no"]:
                        c.execute("UPDATE item_units SET status = 'IN_STOCK' WHERE serial_no = ?", (str(sel_row["serial_no"]),))
                    
                    c.execute("""
                        INSERT INTO sales_returns (bill_no, product_id, product_name, returned_qty, refund_amount, return_reason, returned_by)
                        VALUES (?, ?, ?, 1, ?, ?, ?)
                    """, (ret_bill_no.strip(), int(sel_row["product_id"]), selected_item_name, float(sel_row["total_amount"]), reason.strip(), str(st.session_state.username)))
                    conn.commit()
                    st.success(f"🎉 '{selected_item_name}' वापस ले लिया गया और स्टॉक में जुड़ गया!")
                    st.rerun()
        else:
            st.error("❌ यह बिल नंबर नहीं मिला।")
    conn.close()

# ==========================================
# 5. बारकोड व QR स्टिकर प्रिंटर
# ==========================================
elif mode == "🏷️ बारकोड स्टिकर प्रिंटर":
    st.subheader("🏷️ प्रोडक्ट बारकोड स्टिकर व प्राइस टैग जनरेटर")
    st.caption("चयनित सामान के प्रत्येक उपलब्ध पीस का अलग-अलग बारकोड स्टिकर प्रिंट करें")

    conn = sqlite3.connect(DB_NAME)
    products_df = pd.read_sql_query("SELECT id, name, category, sell_price, gst_percent, stock FROM products WHERE stock > 0", conn)
    
    c_set = conn.cursor()
    c_set.execute("SELECT shop_title FROM shop_settings WHERE id=1")
    s_info = c_set.fetchone()
    current_shop_name = s_info[0] if s_info else "Raju Bhaiya Store"

    if not products_df.empty:
        selected_prod_name = st.selectbox("सामान चुनें:", products_df["name"].tolist())
        target_prod = products_df[products_df["name"] == selected_prod_name].iloc[0]
        p_id = int(target_prod["id"])
        total_stock = int(target_prod["stock"])

        units_df = pd.read_sql_query("SELECT id, serial_no FROM item_units WHERE product_id = ? AND status = 'IN_STOCK'", conn, params=(p_id,))
        conn.close()

        all_units_serials = units_df["serial_no"].tolist() if not units_df.empty else [f"SN-{p_id:04d}-{i+1:02d}" for i in range(total_stock)]

        col_st1, col_st2 = st.columns([1, 1])
        with col_st1:
            print_mode = st.radio("प्रिंट विकल्प चुनें:", [f"🖨️ दुकान में मौजूद सभी {len(all_units_serials)} पीस प्रिंट करें", "🎯 केवल कुछ चुनिंदा पीस चुनें"])
            selected_serials_to_print = all_units_serials if print_mode.startswith("🖨️ दुकान में मौजूद सभी") else st.multiselect("सीरियल नंबर चुनें:", all_units_serials, default=all_units_serials[:min(6, len(all_units_serials))])
            show_price = st.checkbox("स्टीकर पर MRP दिखाएं", value=True)
            st.success(f"✅ कुल प्रिंट होने वाले बारकोड: **{len(selected_serials_to_print)}** पीस")

        with col_st2:
            sample_code = selected_serials_to_print[0] if selected_serials_to_print else "SN-000000"
            price_display = f"<div style='font-size:15px; font-weight:bold; color:#000;'>MRP: ₹{target_prod['sell_price']:.2f}</div>" if show_price else ""
            
            preview_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
                <style>
                    body {{ margin: 0; background: transparent; display: flex; justify-content: center; align-items: center; }}
                    .tag-box {{ border: 2px dashed #1E88E5; padding: 10px; width: 210px; text-align: center; font-family: Arial, sans-serif; background: #ffffff; border-radius: 8px; }}
                    .shop-title {{ font-size: 11px; font-weight: bold; color: #1E88E5; text-transform: uppercase; margin-bottom: 2px; }}
                    .prod-title {{ font-size: 13px; font-weight: bold; color: #111; margin-bottom: 4px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
                    svg {{ max-width: 190px; height: 50px; }}
                </style>
            </head>
            <body>
                <div class="tag-box">
                    <div class="shop-title">{current_shop_name}</div>
                    <div class="prod-title">{target_prod['name']}</div>
                    <svg id="preview_barcode"></svg>
                    {price_display}
                </div>
                <script>
                    JsBarcode("#preview_barcode", "{sample_code}", {{ format: "CODE128", width: 2, height: 40, displayValue: true, fontSize: 13, margin: 0 }});
                </script>
            </body>
            </html>
            """
            st.components.v1.html(preview_html, height=190)

        st.divider()
        tags_script_loop = "".join([f'JsBarcode("#barcode_{i}", "{code}", {{ format: "CODE128", width: 1.8, height: 38, displayValue: true, fontSize: 12, margin: 0 }});\n' for i, code in enumerate(selected_serials_to_print)])
        tags_divs_loop = "".join([f"""
        <div style='border: 1px solid #000; padding: 6px; width: 180px; text-align: center; font-family: Arial, sans-serif; background: #fff; margin: 5px; display: inline-block; border-radius: 4px; page-break-inside: avoid;'>
            <div style='font-size: 10px; font-weight: bold; color: #1E88E5;'>{current_shop_name}</div>
            <div style='font-size: 12px; font-weight: bold; color: #000; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;'>{target_prod['name']}</div>
            <svg id='barcode_{i}' style='max-width: 165px; height: 45px;'></svg>
            {price_display}
        </div>
        """ for i, _ in enumerate(selected_serials_to_print)])

        print_sheet_script = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
        </head>
        <body style="margin:0; padding:0;">
            <button onclick="printLabels()" style="background-color:#1E88E5; color:white; padding:12px 24px; font-size:16px; font-weight:bold; border:none; border-radius:6px; cursor:pointer; width:100%;">🖨️ ये सभी {len(selected_serials_to_print)} अलग-अलग बारकोड स्टिकर प्रिंट करें</button>
            <script>
            function printLabels() {{
                var win = window.open('', '', 'height=650,width=850');
                win.document.write(`
                    <html>
                    <head>
                        <title>Print Barcode Stickers</title>
                        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"><\/script>
                        <style> body {{ margin: 10px; font-family: Arial, sans-serif; }} .print-grid {{ display: flex; flex-wrap: wrap; justify-content: flex-start; }} @media print {{ button {{ display: none; }} }} </style>
                    </head>
                    <body>
                        <div class="print-grid">{tags_divs_loop}</div>
                        <script> {tags_script_loop} setTimeout(function() {{ window.print(); window.close(); }}, 500); <\/script>
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
        conn.close()
        st.info("दुकान में कोई सामान नहीं है।")

# ==========================================
# 6. GSTR-1 टैक्स रिपोर्ट
# ==========================================
elif mode == "📄 GSTR-1 टैक्स रिपोर्ट":
    st.subheader("📄 GSTR-1 एवं सरकारी टैक्स रिटर्न रिपोर्ट")
    conn = sqlite3.connect(DB_NAME)
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    conn.close()

    if not sales_df.empty:
        sales_df["sale_date"] = pd.to_datetime(sales_df["sale_date"])
        sales_df["month_str"] = sales_df["sale_date"].dt.strftime("%m-%Y")
        all_months = sorted(sales_df["month_str"].unique().tolist(), reverse=True)
        sel_gst_month = st.selectbox("📅 टैक्स फाइलिंग महीना चुनें:", all_months)
        monthly_sales = sales_df[sales_df["month_str"] == sel_gst_month]

        if not monthly_sales.empty:
            gstr1_df = pd.DataFrame({
                "Invoice Number": monthly_sales["bill_no"],
                "Invoice Date": monthly_sales["sale_date"].dt.strftime("%d-%b-%Y"),
                "Customer Name": monthly_sales["customer_name"],
                "Item Description": monthly_sales["product_name"],
                "Quantity": monthly_sales["quantity"],
                "Taxable Value (Rs)": (monthly_sales["sell_price"] * monthly_sales["quantity"]).round(2),
                "GST Rate (%)": monthly_sales["gst_percent"],
                "Total GST (Rs)": monthly_sales["gst_amount"].round(2),
                "Total Invoice Value (Rs)": monthly_sales["total_amount"].round(2)
            })
            st.dataframe(gstr1_df, use_container_width=True)
            csv_data = gstr1_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 GSTR-1 CSV डाउनलोड करें", data=csv_data, file_name=f"GSTR1_{sel_gst_month}.csv", mime="text/csv", type="primary")
    else:
        st.info("अभी कोई बिक्री रिकॉर्ड नहीं है।")

# ==========================================
# 7. नया स्टॉक जोड़ें (सही क्रम: नाम -> मात्रा -> अलग-अलग सीरियल -> दर)
# ==========================================
elif mode == "➕ नया स्टॉक / प्रोडक्ट जोड़ें":
    st.subheader("➕ नया सामान स्टॉक एवं प्रत्येक पीस का सीरियल नंबर जोड़ें")
    
    with st.form("add_item_form", clear_on_submit=False):
        st.markdown("#### 1. सामान एवं मात्रा विवरण")
        c1, c2 = st.columns([3, 1])
        name = c1.text_input("1. सामान का नाम (Item Name) *", placeholder="उदा. Fast Mobile Charger / 65W Data Cable")
        stock_qty = c2.number_input("2. कितने पीस हैं? (Total Qty) *", min_value=1, max_value=200, value=10, step=1)
        
        st.markdown("---")
        st.markdown(f"#### 2. इन सभी {stock_qty} पीसों के अलग-अलग सीरियल नंबर:")
        
        sn_mode = st.radio("सीरियल नंबर भरने का तरीका चुनें:", [
            "🎲 सॉफ्टवेयर से सभी पीस के लिए यूनिक सीरियल ऑटो-जनरेट करें (Auto Gen Unique)",
            "✍️ हाथ से टाइप करें या स्कैनर से एक-एक करके स्कैन करें (Custom Input per Piece)"
        ], horizontal=True)

        serial_numbers_list = []
        
        if sn_mode.startswith("🎲"):
            rand_prefix = f"SN{random.randint(1000, 9999)}"
            auto_serials = [f"{rand_prefix}-{i+1:03d}" for i in range(int(stock_qty))]
            st.info(f"💡 जनरेट किए गए {stock_qty} यूनिक सीरियल कोड: `{auto_serials[0]}` ... से ... `{auto_serials[-1]}`")
            serial_numbers_list = auto_serials
        else:
            st.caption(f"नीचे दिए गए बॉक्स में पूरे {stock_qty} सीरियल नंबर लिखें (हर लाइन में एक सीरियल नंबर):")
            default_placeholder = "\n".join([f"SN-{random.randint(10000, 99999)}-{i+1:02d}" for i in range(int(stock_qty))])
            sn_text_bulk = st.text_area("सीरियल नंबर लिस्ट (1 लाइन = 1 पीस):", value=default_placeholder, height=140)
            serial_numbers_list = [line.strip() for line in sn_text_bulk.strip().split("\n") if line.strip()]

        st.markdown("---")
        st.markdown("#### 3. कीमत एवं टैक्स विवरण")
        c3, c4, c5, c6 = st.columns(4)
        buy_p = c3.number_input("3. खरीद लागत मूल्य प्रति पीस (₹) *", min_value=0.0, step=1.0)
        sell_p = c4.number_input("4. निर्धारित बिक्री मूल्य प्रति पीस (₹) *", min_value=0.0, step=1.0)
        gst_slab = c5.selectbox("GST दर (%) *", [0, 5, 12, 18, 28], index=3)
        category = c6.text_input("कैटेगरी *", value="General")

        desc = st.text_input("सामान का विवरण / वारंटी नोट", placeholder="उदा. 1 साल की गारंटी")
        is_on = st.checkbox("🌐 इस सामान को ऑनलाइन डिजिटल कैटलॉग पर लाइव दिखाएं", value=True)

        if st.form_submit_button("💾 नया स्टॉक और सभी यूनिक सीरियल नंबर सुरक्षित करें", type="primary", use_container_width=True):
            if not name.strip():
                st.warning("⚠️ कृपया सामान का नाम दर्ज करें!")
            elif len(serial_numbers_list) != int(stock_qty):
                st.error(f"⚠️ स्टॉक मात्रा {stock_qty} है, लेकिन आपने {len(serial_numbers_list)} सीरियल नंबर दर्ज किए हैं!")
            else:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO products (name, category, hsn_code, buy_price, sell_price, gst_percent, stock, min_alert, description, image_url, is_online)
                    VALUES (?, ?, '8504', ?, ?, ?, ?, 3, ?, '', ?)
                """, (name.strip(), category.strip(), buy_p, sell_p, float(gst_slab), int(stock_qty), desc.strip(), 1 if is_on else 0))
                new_prod_id = cursor.lastrowid

                for sn in serial_numbers_list:
                    cursor.execute("""
                        INSERT OR REPLACE INTO item_units (product_id, serial_no, status)
                        VALUES (?, ?, 'IN_STOCK')
                    """, (new_prod_id, sn))

                conn.commit()
                conn.close()
                st.success(f"🎉 '{name}' के सभी {stock_qty} पीस अलग-अलग यूनिक सीरियल नंबर के साथ सफलतापूर्वक स्टॉक में जुड़ गए!")

# ==========================================
# 8. स्टॉक व ऑनलाइन शो
# ==========================================
elif mode == "📦 स्टॉक व ऑनलाइन शो":
    st.subheader("📦 दुकान का लाइव स्टॉक एवं यूनिट सीरियल लिस्टिंग")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, name, category, buy_price, sell_price, gst_percent, stock FROM products", conn)
    
    st.markdown("#### 📋 प्रोडक्ट स्टॉक समरी")
    st.dataframe(df.rename(columns={'name': 'सामान', 'category': 'कैटेगरी', 'buy_price': 'खरीद (₹)', 'sell_price': 'बिक्री (₹)', 'gst_percent': 'GST %', 'stock': 'उपलब्ध पीस'}), use_container_width=True)

    st.markdown("#### 🔍 किसी प्रोडक्ट के सभी यूनिक पीस और सीरियल नंबर देखें:")
    if not df.empty:
        sel_p = st.selectbox("प्रोडक्ट चुनें:", df["name"].tolist())
        target_id = df[df["name"] == sel_p].iloc[0]["id"]
        units_df = pd.read_sql_query("SELECT id, serial_no, status, created_at FROM item_units WHERE product_id = ?", conn, params=(int(target_id),))
        st.dataframe(units_df.rename(columns={'serial_no': 'यूनिक सीरियल नंबर / बारकोड', 'status': 'स्थिति (IN_STOCK / SOLD)', 'created_at': 'तारीख'}), use_container_width=True)
    conn.close()

# ==========================================
# 9. उधारी/खाता अलर्ट
# ==========================================
elif mode == "📒 उधारी/खाता अलर्ट":
    st.subheader("📒 ग्राहक उधारी रजिस्टर एवं WhatsApp पेमेंट रिमाइंडर")
    conn = sqlite3.connect(DB_NAME)
    udhar_df = pd.read_sql_query("SELECT id, bill_no, customer_name, customer_phone, total_amount, paid_amount, due_date, status FROM udhar_ledger WHERE status='PENDING'", conn)
    
    if not udhar_df.empty:
        udhar_df["baki_amount"] = udhar_df["total_amount"] - udhar_df["paid_amount"]
        for idx, row in udhar_df.iterrows():
            c_u1, c_u2, c_u3, c_u4 = st.columns([3, 2, 2, 3])
            c_u1.write(f"**{row['customer_name']}** ({row['customer_phone']})\n\nबिल: `{row['bill_no']}`")
            c_u2.write(f"बकाया: **₹{row['baki_amount']:.2f}**")
            c_u3.write(f"तारीख: **{row['due_date']}**")
            
            wa_text = f"नमस्ते {row['customer_name']} जी, आपकी बकाया उधारी ₹{row['baki_amount']:.2f} है। कृपया भुगतान करें।"
            wa_url = f"https://wa.me/91{row['customer_phone']}?text={urllib.parse.quote(wa_text)}"
            
            with c_u4:
                st.link_button("📲 WhatsApp तगादा भेजें", wa_url)
                if st.button("💰 भुगतान मिला", key=f"pay_{row['id']}"):
                    c = conn.cursor()
                    c.execute("UPDATE udhar_ledger SET paid_amount = total_amount, status = 'PAID' WHERE id = ?", (int(row['id']),))
                    conn.commit()
                    st.success("खाता चुकता हुआ!")
                    st.rerun()
            st.divider()
    else:
        st.success("दुकान में किसी ग्राहक की कोई उधारी नहीं है।")
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
        st.dataframe(sales_df[["bill_no", "sale_date", "sold_by", "customer_name", "product_name", "serial_no", "total_amount", "profit"]], use_container_width=True)
    else:
        st.info("कोई बिक्री डेटा नहीं है।")

# ==========================================
# 11. ऑपरेटर मासिक कमीशन
# ==========================================
elif mode == "💵 ऑपरेटर मासिक कमीशन":
    st.subheader("💵 ऑपरेटर मासिक कमीशन व पे-आउट रजिस्टर")
    conn = sqlite3.connect(DB_NAME)
    sales_df = pd.read_sql_query("SELECT * FROM sales WHERE sold_by != 'admin'", conn)
    users_df = pd.read_sql_query("SELECT username, commission_percent FROM users WHERE role='operator'", conn)
    conn.close()

    if not users_df.empty and not sales_df.empty:
        sel_op = st.selectbox("ऑपरेटर चुनें:", users_df["username"].tolist())
        op_sales = sales_df[sales_df["sold_by"] == sel_op]
        st.dataframe(op_sales[["bill_no", "product_name", "serial_no", "total_amount", "profit", "operator_commission"]], use_container_width=True)
    else:
        st.info("डेटा उपलब्ध नहीं है।")

# ==========================================
# 12. एडमिन डैशबोर्ड
# ==========================================
elif mode == "📊 एडमिन डैशबोर्ड":
    st.markdown("<h2>📊 एंटरप्राइज बिज़नेस इंटेलिजेंस व एनालिटिक्स</h2>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()

    if not sales_df.empty:
        k1, k2, k3 = st.columns(3)
        k1.metric("कुल बिक्री", f"₹{sales_df['total_amount'].sum():.2f}")
        k2.metric("कुल मुनाफ़ा", f"₹{sales_df['profit'].sum():.2f}")
        k3.metric("कुल कटे बिल", f"{sales_df['bill_no'].nunique()} बिल")
        
        st.divider()
        fig = px.bar(sales_df.groupby("product_name")["quantity"].sum().reset_index(), x="product_name", y="quantity", title="टॉप सेलिंग आइटम्स")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("डैशबोर्ड डेटा देखने के लिए पहले बिलिंग करें।")

# ==========================================
# 13. ऑपरेटर मैनेजमेंट
# ==========================================
elif mode == "👥 ऑपरेटर मैनेजमेंट":
    st.subheader("👥 ऑपरेटर मैनेजमेंट")
    with st.form("add_user_form"):
        u_name = st.text_input("यूज़रनेम:")
        u_phone = st.text_input("मोबाइल नंबर:")
        u_comm = st.number_input("कमीशन (%):", min_value=0.0, max_value=100.0, value=5.0)
        u_pass = st.text_input("पासवर्ड:", type="password")
        if st.form_submit_button("ऑपरेटर बनाएं"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, phone, commission_percent, role, permissions) VALUES (?, ?, ?, ?, 'operator', ?)", (u_name, u_pass, u_phone, u_comm, json.dumps(ALL_PERMISSIONS)))
            conn.commit()
            conn.close()
            st.success(f"ऑपरेटर {u_name} बन गया!")

# ==========================================
# 14. स्टोर सेटिंग्स (फिक्स रेट लॉक स्विच सहित)
# ==========================================
elif mode == "🎨 स्टोर बैनर व सेटिंग्स":
    st.subheader("🎨 ऑनलाइन स्टोर ब्रांडिंग, UPI एवं फिक्स रेट लॉक सेटिंग्स")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT shop_title, shop_phone, upi_id, lock_operator_price FROM shop_settings WHERE id=1")
    s_row = c.fetchone()
    conn.close()

    cur_lock = bool(s_row[3]) if s_row and s_row[3] is not None else True

    with st.form("settings_form"):
        s_title = st.text_input("दुकान का नाम:", value=s_row[0] if s_row else "Raju Bhaiya Store")
        s_phone = st.text_input("मोबाइल नंबर:", value=s_row[1] if s_row else "8349596263")
        s_upi = st.text_input("UPI ID:", value=s_row[2] if s_row else "8349596263@upi")
        
        st.markdown("---")
        st.markdown("#### 🔒 ऑपरेटर सुरक्षा व मूल्य नियंत्रण:")
        lock_switch = st.checkbox("🔒 ऑपरेटर के लिए फिक्स रेट लॉक करें (दर में कोई कमी या बदलाव नहीं कर सकेंगे)", value=cur_lock)

        if st.form_submit_button("💾 सेटिंग्स सुरक्षित करें", type="primary", use_container_width=True):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE shop_settings SET shop_title=?, shop_phone=?, upi_id=?, lock_operator_price=? WHERE id=1", (s_title, s_phone, s_upi, 1 if lock_switch else 0))
            conn.commit()
            conn.close()
            st.success("✅ सेटिंग्स सफलतापूर्वक अपडेट हो गई!")
            st.rerun()