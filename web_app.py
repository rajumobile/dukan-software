import os
import sqlite3
import datetime
import shutil
import json
import base64
import random
from flask import Flask, request, jsonify, render_template_string, send_file, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "raju_pos_enterprise_prod_secure_2026_jwt_token")
DB_NAME = "shop.db"
BACKUP_DIR = "backups"

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def trigger_auto_backup():
    """मॉड्यूल 11: 30-दिवसीय ऑटो-रोलिंग व रियल-टाइम बैकअप"""
    try:
        if os.path.exists(DB_NAME):
            today_str = datetime.datetime.now().strftime("%Y_%m_%d")
            daily_backup = os.path.join(BACKUP_DIR, f"backup_{today_str}.db")
            shutil.copyfile(DB_NAME, daily_backup)
            now = datetime.datetime.now()
            for f in os.listdir(BACKUP_DIR):
                f_path = os.path.join(BACKUP_DIR, f)
                if os.path.isfile(f_path) and f.startswith("backup_"):
                    c_time = datetime.datetime.fromtimestamp(os.path.getctime(f_path))
                    if (now - c_time).days > 30:
                        os.remove(f_path)
    except Exception as e:
        print(f"Auto Backup Exception: {e}")

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        shop_name TEXT DEFAULT 'Raju Bhaiya Studio & Mobile Kendra',
        tagline TEXT DEFAULT 'डिजिटल फोटोग्राफी, मोबाइल रिपेयरिंग एवं एक्सेसरीज़',
        address TEXT DEFAULT 'Chanda Marriage Garden Ke Pass, Chhatarpur',
        phone TEXT DEFAULT '8349596263',
        gstin TEXT DEFAULT '23AAAFR8349M1Z2',
        upi_id TEXT DEFAULT '8349596263@upi'
    )''')
    c.execute('SELECT COUNT(*) FROM settings')
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO settings (id, shop_name, tagline, address, phone, gstin, upi_id)
                     VALUES (1, 'Raju Bhaiya Studio & Mobile Kendra', 'डिजिटल फोटोग्राफी, मोबाइल रिपेयरिंग एवं एक्सेसरीज़', 'Chanda Marriage Garden Ke Pass, Chhatarpur', '8349596263', '23AAAFR8349M1Z2', '8349596263@upi')''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        full_name TEXT,
        phone TEXT,
        role TEXT DEFAULT 'Operator',
        commission_percent REAL DEFAULT 5.0,
        can_view_profit INTEGER DEFAULT 0,
        can_edit_stock INTEGER DEFAULT 0,
        can_give_discount INTEGER DEFAULT 0,
        can_view_reports INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )''')
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        admin_hashed = generate_password_hash("admin123")
        c.execute('''INSERT INTO users (username, password, full_name, phone, role, commission_percent, can_view_profit, can_edit_stock, can_give_discount, can_view_reports)
                     VALUES ('admin', ?, 'Raju Kushwaha (Master Admin)', '8349596263', 'Admin', 0, 1, 1, 1, 1)''', (admin_hashed,))

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        brand TEXT,
        category TEXT DEFAULT 'General',
        packaging_type TEXT DEFAULT 'Loose',
        purchase_cost REAL DEFAULT 0,
        retail_price REAL DEFAULT 0,
        min_stock_alert INTEGER DEFAULT 2,
        image_data TEXT DEFAULT '',
        is_online INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS product_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        serial_no TEXT UNIQUE,
        status TEXT DEFAULT 'IN_STOCK',
        FOREIGN KEY(product_id) REFERENCES products(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE,
        customer_name TEXT,
        customer_phone TEXT,
        subtotal REAL,
        discount REAL,
        total_amount REAL,
        profit_amount REAL,
        payment_mode TEXT,
        cash_paid REAL DEFAULT 0,
        upi_paid REAL DEFAULT 0,
        udhar_amount REAL DEFAULT 0,
        sold_by_name TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER,
        item_type TEXT,
        product_id INTEGER,
        unit_id INTEGER,
        item_name TEXT,
        serial_no TEXT,
        cost_price REAL,
        sell_price REAL,
        qty INTEGER DEFAULT 1,
        FOREIGN KEY(sale_id) REFERENCES sales(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS repair_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_no TEXT UNIQUE,
        customer_name TEXT,
        customer_phone TEXT,
        brand_model TEXT,
        pattern_pin TEXT,
        fault_description TEXT,
        estimated_cost REAL DEFAULT 0,
        advance_paid REAL DEFAULT 0,
        remaining_balance REAL DEFAULT 0,
        checklist_data TEXT,
        status TEXT DEFAULT 'RECEIVED',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS customer_udhar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        customer_phone TEXT UNIQUE,
        total_udhar REAL DEFAULT 0,
        paid_amount REAL DEFAULT 0,
        due_amount REAL DEFAULT 0,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT,
        item_name TEXT,
        refund_amount REAL,
        reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        amount REAL,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

init_db()

MASTER_HTML = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ settings.shop_name }} - ERP Master Pro 2026</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
    <style>
        @media print {
            body * { visibility: hidden; }
            #printableArea, #printableArea * { visibility: visible; }
            #printableArea { position: absolute; left: 0; top: 0; width: 100%; display: block !important; }
        }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen">

    <!-- 1. पब्लिक डिजिटल शोरूम (डिफ़ॉल्ट व्यू) -->
    <div id="publicStoreView" class="min-h-screen flex flex-col">
        <header class="bg-slate-900 border-b border-slate-800 sticky top-0 z-40 p-4 shadow-lg">
            <div class="max-w-6xl mx-auto flex flex-wrap justify-between items-center gap-3">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center text-white text-xl">
                        <i class="fa-solid fa-store"></i>
                    </div>
                    <div>
                        <h1 class="font-bold text-base md:text-lg text-white leading-tight">{{ settings.shop_name }}</h1>
                        <p class="text-[11px] text-emerald-400">{{ settings.tagline }}</p>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <a href="https://wa.me/91{{ settings.phone }}" target="_blank" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-xs font-bold flex items-center gap-1.5 text-white">
                        <i class="fa-brands fa-whatsapp text-sm"></i> संपर्क करें
                    </a>
                    <button onclick="openLoginModal()" class="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-bold text-white shadow-lg shadow-blue-600/30 transition">
                        <i class="fa-solid fa-lock mr-1"></i> 🔐 स्टाफ़ लॉगिन
                    </button>
                </div>
            </div>
        </header>

        <main class="max-w-6xl mx-auto p-4 md:p-6 space-y-6 flex-1 w-full">
            <div class="bg-gradient-to-r from-blue-900/40 via-indigo-900/30 to-purple-900/40 border border-indigo-800/40 p-6 rounded-2xl text-center space-y-2">
                <h2 class="text-xl md:text-2xl font-bold text-white">🛍️ हमारा डिजिटल शोरूम व कैटलॉग</h2>
                <p class="text-xs md:text-sm text-slate-300 max-w-xl mx-auto">नीचे दिए गए सभी प्रोडक्ट्स हमारी दुकान पर उपलब्ध हैं। खरीदने हेतु <b>WhatsApp ऑर्डर</b> पर क्लिक करें।</p>
                <div class="pt-2 max-w-md mx-auto">
                    <input type="text" id="publicSearchInput" onkeyup="filterPublicStore()" placeholder="सामान का नाम या मॉडल खोजें..." class="w-full bg-slate-900 border border-slate-700 px-4 py-2.5 rounded-xl text-sm text-white focus:outline-none focus:border-emerald-500">
                </div>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4" id="publicProductGrid"></div>
        </main>

        <footer class="border-t border-slate-800 text-center p-6 text-xs text-slate-500 mt-12 bg-slate-900/50">
            <p class="font-semibold text-slate-400">{{ settings.shop_name }}</p>
            <p class="mt-1">📍 पता: {{ settings.address }} | 📞 फ़ोन: {{ settings.phone }}</p>
            <p class="mt-2 text-emerald-500">✅ 100% ओरिजिनल व टेस्टेड प्रोडक्ट्स</p>
        </footer>
    </div>

    <!-- 2. सुरक्षित लॉगिन मॉडल -->
    <div id="loginModal" class="hidden fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
        <div class="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-8 shadow-2xl space-y-6 relative">
            <button onclick="closeLoginModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-xl"></i></button>
            <div class="text-center space-y-2">
                <div class="w-14 h-14 bg-blue-600 rounded-2xl mx-auto flex items-center justify-center text-white text-2xl shadow-lg shadow-blue-500/30">
                    <i class="fa-solid fa-user-shield"></i>
                </div>
                <h2 class="text-xl font-bold text-white tracking-wide">ERP मास्टर लॉगिन</h2>
                <p class="text-xs text-slate-400">कृपया अपना अधिकृत यूज़रनेम व पासवर्ड दर्ज करें</p>
            </div>
            <div class="space-y-4">
                <div>
                    <label class="text-xs text-slate-400 font-semibold block mb-1">यूज़रनेम (Username)</label>
                    <input type="text" id="loginUsername" placeholder="यूज़रनेम दर्ज करें" class="w-full bg-slate-950 border border-slate-700 px-4 py-2.5 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500">
                </div>
                <div>
                    <label class="text-xs text-slate-400 font-semibold block mb-1">पासवर्ड (Password)</label>
                    <input type="password" id="loginPassword" placeholder="••••••••" class="w-full bg-slate-950 border border-slate-700 px-4 py-2.5 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500" onkeydown="if(event.key==='Enter') handleUserLogin()">
                </div>
                <button onclick="handleUserLogin()" class="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-bold text-white text-sm shadow-lg shadow-blue-600/30 transition">🔐 सिस्टम में प्रवेश करें</button>
            </div>
        </div>
    </div>

    <!-- 3. मुख्य ERP इंटरफ़ेस (सभी 11 मॉड्यूल्स) -->
    <div id="mainAppInterface" class="hidden min-h-screen flex flex-col md:flex-row bg-slate-900">
        <aside class="w-full md:w-64 bg-slate-950 border-r border-slate-800 flex flex-col justify-between shrink-0">
            <div>
                <div class="p-4 border-b border-slate-800 flex items-center gap-3">
                    <i class="fa-solid fa-mobile-screen-button text-blue-500 text-2xl"></i>
                    <div>
                        <h1 class="font-bold text-sm text-white leading-tight">{{ settings.shop_name }}</h1>
                        <span class="text-xs font-medium" id="userRoleBadge">● User Mode</span>
                    </div>
                </div>
                <nav class="p-3 space-y-1 text-sm">
                    <button onclick="showModule('dashboard')" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 transition"><i class="fa-solid fa-chart-line w-5"></i> 📊 लाइव डैशबोर्ड</button>
                    <button onclick="showModule('pos')" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 transition"><i class="fa-solid fa-cash-register w-5 text-emerald-400"></i> ⚡ POS बिलिंग (Beep)</button>
                    <button onclick="showModule('stock')" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 transition"><i class="fa-solid fa-boxes-stacked w-5 text-amber-400"></i> 📦 नया स्टॉक व एडिट</button>
                    <button onclick="showModule('stickers')" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 transition"><i class="fa-solid fa-barcode w-5 text-purple-400"></i> 🏷️ बारकोड/लेबल प्रिंट</button>
                    <button onclick="showModule('repair')" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 transition"><i class="fa-solid fa-screwdriver-wrench w-5 text-cyan-400"></i> 📱 मोबाइल रिपेयरिंग</button>
                    <button onclick="showModule('udhar')" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 transition"><i class="fa-solid fa-book-journal-whills w-5 text-rose-400"></i> 📒 उधारी / खाता</button>
                    <button onclick="showModule('returns')" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 transition"><i class="fa-solid fa-right-left w-5 text-orange-400"></i> 🔄 सेल्स रिटर्न/डैमेज</button>
                    
                    <div id="adminMenuSection" class="space-y-1 pt-2 border-t border-slate-800">
                        <span class="px-3 text-[10px] uppercase font-bold text-indigo-400">एडमिन कंट्रोल्स</span>
                        <button onclick="showModule('operators')" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 transition"><i class="fa-solid fa-users-gear w-5 text-indigo-400"></i> 👥 ऑपरेटर परमिशन</button>
                        <button onclick="showModule('reports')" id="navReportsBtn" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 transition"><i class="fa-solid fa-file-invoice-dollar w-5 text-yellow-400"></i> 📄 GSTR-1 व खर्चे</button>
                        <button onclick="showModule('settings')" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 transition"><i class="fa-solid fa-gears w-5 text-slate-400"></i> 💾 बैकअप व सेटिंग्स</button>
                    </div>

                    <button onclick="switchToCustomerStore()" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-emerald-400 hover:bg-slate-800 transition"><i class="fa-solid fa-globe w-5"></i> 🛍️ डिजिटल शोरूम देखें</button>
                </nav>
            </div>
            
            <div class="p-4 border-t border-slate-800 space-y-2">
                <div class="text-xs text-slate-300">
                    <p class="text-slate-500">लॉगिन उपयोगकर्ता:</p>
                    <p class="font-bold text-white text-sm" id="activeUserNameDisplay">Admin</p>
                </div>
                <button onclick="handleUserLogout()" class="w-full py-2 bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-800/60 rounded-lg text-xs font-semibold flex items-center justify-center gap-2">
                    <i class="fa-solid fa-right-from-bracket"></i> 🚪 लॉगआउट (Logout)
                </button>
            </div>
        </aside>

        <!-- कार्यक्षेत्र -->
        <main class="flex-1 p-4 md:p-6 overflow-y-auto max-h-screen">
            
            <!-- 1. लाइव डैशबोर्ड -->
            <section id="mod-dashboard" class="space-y-6">
                <div class="flex justify-between items-center">
                    <div>
                        <h2 class="text-2xl font-bold text-white">📊 लाइव बिज़नेस इंटेलिजेंस डैशबोर्ड</h2>
                        <p class="text-xs text-slate-400">लाइव आंकड़े, शुद्ध मुनाफ़ा एवं गल्ला स्थिति</p>
                    </div>
                    <button onclick="loadDashboardData()" class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-lg border border-slate-700"><i class="fa-solid fa-arrows-rotate mr-1"></i> रिफ्रेश</button>
                </div>
                <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
                        <span class="text-xs text-slate-400">आज की बिक्री</span>
                        <h3 class="text-xl font-bold text-emerald-400 mt-1" id="kpiTodaySales">₹0</h3>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800" id="kpiProfitBox">
                        <span class="text-xs text-slate-400">आज का मुनाफ़ा</span>
                        <h3 class="text-xl font-bold text-blue-400 mt-1" id="kpiTodayProfit">₹0</h3>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
                        <span class="text-xs text-slate-400">रिपेयरिंग आय</span>
                        <h3 class="text-xl font-bold text-cyan-400 mt-1" id="kpiRepairRevenue">₹0</h3>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
                        <span class="text-xs text-slate-400">गल्ला कैश</span>
                        <h3 class="text-xl font-bold text-amber-400 mt-1" id="kpiDrawerCash">₹0</h3>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
                        <span class="text-xs text-slate-400">मार्केट उधारी</span>
                        <h3 class="text-xl font-bold text-rose-400 mt-1" id="kpiTotalUdhar">₹0</h3>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800" id="kpiStockValBox">
                        <span class="text-xs text-slate-400">स्टॉक वैल्यू</span>
                        <h3 class="text-xl font-bold text-purple-400 mt-1" id="kpiStockVal">₹0</h3>
                    </div>
                </div>
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
                        <h4 class="text-sm font-semibold mb-3">📈 साप्ताहिक बिक्री ट्रेंड</h4>
                        <canvas id="salesProfitChart" height="180"></canvas>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
                        <h4 class="text-sm font-semibold mb-3">🚨 कम स्टॉक व महत्वपूर्ण अलर्ट</h4>
                        <div id="dashAlertsList" class="space-y-2 text-xs text-slate-300"></div>
                    </div>
                </div>
            </section>

            <!-- 2. POS बिलिंग -->
            <section id="mod-pos" class="hidden space-y-6">
                <div class="flex justify-between items-center">
                    <h2 class="text-2xl font-bold text-white">⚡ सुपरफास्ट POS बिलिंग व सर्विस काउंटर</h2>
                    <button onclick="toggleCameraScanner()" class="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs font-semibold"><i class="fa-solid fa-camera mr-1"></i> कैमरा स्कैनर (Beep)</button>
                </div>
                <div id="scannerContainer" class="hidden bg-slate-950 p-4 rounded-xl border border-indigo-500 max-w-sm mx-auto">
                    <div id="reader"></div>
                </div>
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div class="lg:col-span-2 bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4">
                        <div class="flex gap-2">
                            <input type="text" id="posBarcodeGunInput" placeholder="बारकोड स्कैन करें या सीरियल नंबर लिखें..." class="flex-1 bg-slate-900 border border-slate-700 px-4 py-2.5 rounded-lg text-sm text-white" onkeydown="if(event.key==='Enter') handleScanAdd(this.value)">
                            <button onclick="handleScanAdd(document.getElementById('posBarcodeGunInput').value)" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold">जोड़ें</button>
                        </div>
                        <div class="p-3 bg-slate-900 border border-slate-800 rounded-lg flex flex-wrap gap-2 items-center">
                            <span class="text-xs font-semibold text-cyan-400">🛠️ सर्विस / लेबर जोड़ें:</span>
                            <button onclick="addCustomService('Software Flashing', 200)" class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700">+ सॉफ्टवेयर (₹200)</button>
                            <button onclick="addCustomService('Screen Guard Pasting', 50)" class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700">+ ग्लास पेस्टिंग (₹50)</button>
                            <button onclick="addCustomService('Data Backup/Transfer', 150)" class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700">+ डेटा ट्रांसफर (₹150)</button>
                            <button onclick="promptCustomLabour()" class="px-2.5 py-1 bg-cyan-900 text-cyan-200 hover:bg-cyan-800 text-xs rounded border border-cyan-700">+ कस्टम काम</button>
                        </div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left text-sm">
                                <thead class="text-xs text-slate-400 bg-slate-900 border-b border-slate-800">
                                    <tr>
                                        <th class="p-2">विवरण</th>
                                        <th class="p-2">सीरियल/कोड</th>
                                        <th class="p-2">दर (₹)</th>
                                        <th class="p-2">मात्रा</th>
                                        <th class="p-2">कुल</th>
                                        <th class="p-2 text-right">हटाएं</th>
                                    </tr>
                                </thead>
                                <tbody id="posCartBody"></tbody>
                            </table>
                        </div>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4">
                        <h3 class="font-bold text-sm text-white">ग्राहक व बिल सारांश</h3>
                        <input type="text" id="posCustName" placeholder="ग्राहक का नाम" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                        <input type="text" id="posCustPhone" placeholder="मोबाइल नंबर (WhatsApp)" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                        <div class="space-y-2 border-t border-slate-800 pt-3 text-sm">
                            <div class="flex justify-between"><span>सब-टोटल:</span><span id="posSubtotal">₹0</span></div>
                            <div class="flex justify-between" id="discountInputRow"><span>डिस्काउंट (₹):</span><input type="number" id="posDiscount" value="0" onchange="calcPosTotal()" class="w-20 bg-slate-900 border border-slate-700 p-1 text-right text-xs rounded text-white"></div>
                            <div class="flex justify-between text-base font-bold text-emerald-400"><span>अंतिम कुल:</span><span id="posGrandTotal">₹0</span></div>
                        </div>
                        <div class="space-y-2 pt-2">
                            <select id="posPayMode" onchange="handlePayModeChange(this.value)" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                                <option value="Cash">💵 100% नकद (Cash)</option>
                                <option value="UPI">📱 100% ऑनलाइन UPI QR</option>
                                <option value="Split">🔀 स्प्लिट (नकद + UPI)</option>
                                <option value="Udhar">📒 100% उधारी (Credit)</option>
                            </select>
                            <div id="splitInputBox" class="hidden grid grid-cols-2 gap-2 pt-2">
                                <input type="number" id="posSplitCash" placeholder="नकद ₹" class="bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                                <input type="number" id="posSplitUpi" placeholder="UPI ₹" class="bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                            </div>
                        </div>
                        <button onclick="checkoutSale()" class="w-full py-3 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-bold text-white transition text-sm">✅ बिल बनाएं व WhatsApp भेजें</button>
                    </div>
                </div>
            </section>

            <!-- 3. नया स्टॉक व एडिट -->
            <section id="mod-stock" class="hidden space-y-6">
                <div class="flex justify-between items-center">
                    <div>
                        <h2 class="text-2xl font-bold text-white">📦 नया स्टॉक एंट्री एवं करेक्शन सिस्टम</h2>
                        <p class="text-xs text-slate-400">सीरियल/IMEI ग्रिड, फ़ोटो कैप्चर, बॉक्स/लूज़ व स्टॉक संपादन</p>
                    </div>
                    <button id="addStockBtn" onclick="openNewProductModal()" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold"><i class="fa-solid fa-plus mr-1"></i> नया सामान जोड़ें</button>
                </div>
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
                    <input type="text" id="stockSearchInput" onkeyup="filterStockTable()" placeholder="सामान का नाम खोजें..." class="w-full bg-slate-900 border border-slate-700 px-4 py-2 rounded-lg text-sm text-white mb-4">
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-sm" id="stockTable">
                            <thead class="text-xs text-slate-400 bg-slate-900 border-b border-slate-800">
                                <tr>
                                    <th class="p-2">फ़ोटो</th>
                                    <th class="p-2">सामान का नाम</th>
                                    <th class="p-2">ब्रांड/कैटेगरी</th>
                                    <th class="p-2">पैकेजिंग</th>
                                    <th class="p-2" id="thCost">खरीद दर (₹)</th>
                                    <th class="p-2">बिक्री दर (₹)</th>
                                    <th class="p-2">स्टॉक (पीस)</th>
                                    <th class="p-2 text-right">एडिट / करेक्शन</th>
                                </tr>
                            </thead>
                            <tbody id="stockTableBody"></tbody>
                        </table>
                    </div>
                </div>
            </section>

            <!-- 4. बारकोड स्टिकर प्रिंटर -->
            <section id="mod-stickers" class="hidden space-y-6">
                <h2 class="text-2xl font-bold text-white">🏷️ बारकोड, IMEI व स्टिकर प्रिंटर (2x1 इंच)</h2>
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label class="text-xs text-slate-400">सामान चुनें:</label>
                            <select id="stickerProductSelect" onchange="loadProductUnitsForStickers(this.value)" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white mt-1"></select>
                        </div>
                        <div>
                            <label class="text-xs text-slate-400">लेआउट:</label>
                            <select id="stickerSize" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white mt-1">
                                <option value="50x25">थर्मल रोल (50mm x 25mm / 2x1 इंच)</option>
                            </select>
                        </div>
                        <div class="flex items-end">
                            <button onclick="printGeneratedStickers()" class="w-full py-2 bg-purple-600 hover:bg-purple-500 rounded text-sm font-semibold"><i class="fa-solid fa-print mr-1"></i> स्टिकर प्रिंट निकालें</button>
                        </div>
                    </div>
                    <div id="stickerPreviewGrid" class="border border-slate-800 p-4 rounded-lg bg-slate-900 flex flex-wrap gap-3 max-h-96 overflow-y-auto"></div>
                </div>
            </section>

            <!-- 5. मोबाइल रिपेयरिंग जॉब कार्ड -->
            <section id="mod-repair" class="hidden space-y-6">
                <div class="flex justify-between items-center">
                    <div>
                        <h2 class="text-2xl font-bold text-white">📱 मोबाइल रिपेयरिंग जॉब कार्ड व 12-प्वाइंट चेकलिस्ट</h2>
                        <p class="text-xs text-slate-400">ग्राहक सुरक्षा, कानूनी नोट एवं 8-स्टेज वर्कफ़्लो</p>
                    </div>
                    <button onclick="openNewJobCardModal()" class="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-xs font-semibold"><i class="fa-solid fa-plus mr-1"></i> नया फोन जमा करें</button>
                </div>
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs text-slate-400 bg-slate-900 border-b border-slate-800">
                            <tr>
                                <th class="p-2">जॉब नंबर</th>
                                <th class="p-2">ग्राहक</th>
                                <th class="p-2">मॉडल व समस्या</th>
                                <th class="p-2">अनुमानित (₹)</th>
                                <th class="p-2">एडवांस (₹)</th>
                                <th class="p-2">स्टेटस</th>
                                <th class="p-2 text-right">एक्शन / WhatsApp</th>
                            </tr>
                        </thead>
                        <tbody id="repairJobTableBody"></tbody>
                    </table>
                </div>
            </section>

            <!-- 6. उधारी/खाता लेजर -->
            <section id="mod-udhar" class="hidden space-y-6">
                <div class="flex justify-between items-center">
                    <div>
                        <h2 class="text-2xl font-bold text-white">📒 उधारी / ग्राहक खाता लेजर</h2>
                        <p class="text-xs text-slate-400">आंशिक भुगतान चुकता, ओवरड्यू अलर्ट एवं WhatsApp तगादा</p>
                    </div>
                </div>
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs text-slate-400 bg-slate-900 border-b border-slate-800">
                            <tr>
                                <th class="p-2">ग्राहक का नाम</th>
                                <th class="p-2">मोबाइल</th>
                                <th class="p-2">कुल उधारी (₹)</th>
                                <th class="p-2">जमा किया (₹)</th>
                                <th class="p-2">शेष बकाया (₹)</th>
                                <th class="p-2 text-right">एक्शन</th>
                            </tr>
                        </thead>
                        <tbody id="udharTableBody"></tbody>
                    </table>
                </div>
            </section>

            <!-- 7. सेल्स रिटर्न -->
            <section id="mod-returns" class="hidden space-y-6">
                <h2 class="text-2xl font-bold text-white">🔄 सेल्स रिटर्न, एक्सचेंज एवं डिफेक्टिव रूटिंग</h2>
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 max-w-xl space-y-3">
                    <input type="text" id="retInvoiceNo" placeholder="बिल नंबर (BILL-XXXX) या सीरियल नंबर" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                    <input type="text" id="retItemName" placeholder="सामान का नाम" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                    <select id="retType" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                        <option value="Replacement">🔄 सामान एक्सचेंज (Replacement)</option>
                        <option value="Refund">💵 नकद / UPI रिफंड</option>
                    </select>
                    <input type="number" id="retAmount" placeholder="रिफंड राशि (₹)" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                    <input type="text" id="retReason" placeholder="वापसी का कारण" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                    <button onclick="submitReturn()" class="w-full py-2 bg-orange-600 hover:bg-orange-500 rounded text-sm font-bold">वापसी दर्ज करें</button>
                </div>
            </section>

            <!-- 8. ऑपरेटर व परमिशन (एडमिन कंट्रोल) -->
            <section id="mod-operators" class="hidden space-y-6">
                <div class="flex justify-between items-center">
                    <div>
                        <h2 class="text-2xl font-bold text-white">👥 ऑपरेटर लिस्ट व कस्टम परमिशन</h2>
                        <p class="text-xs text-slate-400">यहाँ से आप ऑपरेटर जोड़ें और उनके अधिकार (Edit Permissions) कभी भी बदलें</p>
                    </div>
                    <button onclick="openNewUserModal()" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded text-xs font-bold">+ नया ऑपरेटर जोड़ें</button>
                </div>
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs text-slate-400 bg-slate-900 border-b border-slate-800">
                            <tr>
                                <th class="p-2">नाम</th>
                                <th class="p-2">यूज़रनेम</th>
                                <th class="p-2">रोल</th>
                                <th class="p-2">मुनाफ़ा देखें</th>
                                <th class="p-2">स्टॉक एडिट</th>
                                <th class="p-2">छूट दें</th>
                                <th class="p-2">टैक्स रिपोर्ट</th>
                                <th class="p-2 text-right">एक्शन</th>
                            </tr>
                        </thead>
                        <tbody id="operatorsTableBody"></tbody>
                    </table>
                </div>
            </section>

            <!-- 9. GSTR-1 व खर्चे -->
            <section id="mod-reports" class="hidden space-y-6">
                <h2 class="text-2xl font-bold text-white">📄 GSTR-1 रेडी टैक्स रिपोर्ट व दुकान खर्चा</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                        <h3 class="text-sm font-semibold text-white">GSTR-1 सेल्स रिपोर्ट</h3>
                        <a href="/api/export_gstr1" class="inline-block px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-slate-950 font-bold rounded text-xs"><i class="fa-solid fa-file-csv mr-1"></i> GSTR-1 CSV डाउनलोड</a>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                        <h3 class="text-sm font-semibold text-white">दैनिक दुकान खर्चा जोड़ें</h3>
                        <input type="text" id="expCategory" placeholder="खर्च श्रेणी (किराया, चाय, बिजली)" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                        <input type="number" id="expAmount" placeholder="राशि ₹" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                        <button onclick="submitExpense()" class="w-full py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded text-xs font-semibold">खर्च दर्ज करें</button>
                    </div>
                </div>
            </section>

            <!-- 10. ऑनलाइन शोरूम (एडमिन व्यू) -->
            <section id="mod-store" class="hidden space-y-6">
                <div class="flex justify-between items-center">
                    <h2 class="text-2xl font-bold text-white">🛍️ डिजिटल ऑनलाइन स्टोर व WhatsApp कैटलॉग</h2>
                    <button onclick="switchToCustomerStore()" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded text-xs font-bold"><i class="fa-solid fa-store mr-1"></i> पब्लिक कस्टमर व्यू खोलें</button>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4" id="onlineStoreGrid"></div>
            </section>

            <!-- 11. सेटिंग्स व ऑटो-बैकअप -->
            <section id="mod-settings" class="hidden space-y-6">
                <h2 class="text-2xl font-bold text-white">💾 बैकअप, सुरक्षा एवं दुकान सेटिंग्स</h2>
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4 max-w-xl">
                    <input type="text" id="cfgShopName" value="{{ settings.shop_name }}" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                    <input type="text" id="cfgPhone" value="{{ settings.phone }}" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                    <input type="text" id="cfgUpi" value="{{ settings.upi_id }}" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-sm text-white">
                    <button onclick="saveSettings()" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-bold">सेटिंग्स सुरक्षित करें</button>
                    <div class="border-t border-slate-800 pt-4">
                        <a href="/api/download_db" class="inline-block px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded text-xs"><i class="fa-solid fa-download mr-1"></i> डेटाबेस बैकअप डाउनलोड (shop.db)</a>
                    </div>
                </div>
            </section>

        </main>
    </div>

    <!-- ==================== मॉडल्स ==================== -->
    <div id="newProductModal" class="hidden fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
        <div class="bg-slate-950 border border-slate-800 rounded-xl max-w-3xl w-full p-6 max-h-[90vh] overflow-y-auto space-y-4">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h3 class="font-bold text-lg text-white" id="productModalTitle">➕ नया स्टॉक जोड़ें</h3>
                <button onclick="closeProductModal()"><i class="fa-solid fa-xmark text-xl"></i></button>
            </div>
            <input type="hidden" id="editProductId" value="">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                    <label class="text-xs text-slate-400">सामान का नाम *</label>
                    <input type="text" id="pName" placeholder="उदा. Fast Data Cable" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-slate-400">ब्रांड / कंपनी</label>
                    <input type="text" id="pBrand" placeholder="उदा. Realme, Boat" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-slate-400">पैकेजिंग प्रकार</label>
                    <select id="pPackType" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                        <option value="Loose">खुला पीस (Loose Pieces)</option>
                        <option value="Box">बॉक्स पैक (Master Box)</option>
                    </select>
                </div>
                <div>
                    <label class="text-xs text-slate-400">खरीद दर प्रति पीस (₹) *</label>
                    <input type="number" id="pCost" placeholder="उदा. 80" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-slate-400">बिक्री दर प्रति पीस (₹) *</label>
                    <input type="number" id="pRetail" placeholder="उदा. 150" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-slate-400">मात्रा (कितने पीस हैं?) *</label>
                    <input type="number" id="pQty" value="5" min="1" onchange="generateSerialGrid(this.value)" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                </div>
            </div>
            <div class="border border-slate-800 p-3 rounded-lg bg-slate-900 space-y-2">
                <label class="text-xs font-semibold text-cyan-400">📸 सामान की फ़ोटो अपलोड करें या बदलें:</label>
                <input type="file" id="pPhotoFile" accept="image/*" class="text-xs text-slate-400">
            </div>
            <div class="space-y-2" id="serialGridWrapper">
                <div class="flex justify-between items-center">
                    <label class="text-xs font-semibold text-amber-400">📦 प्रत्येक पीस के सीरियल नंबर / बारकोड:</label>
                    <button type="button" onclick="autoFillSerials()" class="px-2 py-1 bg-blue-600 hover:bg-blue-500 rounded text-[11px] font-semibold">⚡ 1-क्लिक सभी ऑटो-जनरेट</button>
                </div>
                <div id="serialGridContainer" class="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-48 overflow-y-auto p-2 bg-slate-900 rounded-lg border border-slate-800"></div>
            </div>
            <button onclick="saveProductAndSerials()" class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded font-bold text-sm text-white">💾 नया सामान व सभी पीस सुरक्षित करें</button>
        </div>
    </div>

    <!-- B. मोबाइल रिपेयरिंग जॉब कार्ड मॉडल -->
    <div id="newJobModal" class="hidden fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
        <div class="bg-slate-950 border border-slate-800 rounded-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto space-y-4">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h3 class="font-bold text-lg text-white">📱 नया मोबाइल रिपेयरिंग जॉब कार्ड</h3>
                <button onclick="closeJobModal()"><i class="fa-solid fa-xmark text-xl"></i></button>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input type="text" id="jCustName" placeholder="ग्राहक का नाम *" class="bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                <input type="text" id="jCustPhone" placeholder="मोबाइल नंबर (WhatsApp) *" class="bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                <input type="text" id="jBrandModel" placeholder="कंपनी व मॉडल (उदा. Vivo Y20) *" class="bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                <input type="text" id="jPassPin" placeholder="पैटर्न / स्क्रीन लॉक पिन" class="bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
            </div>
            <div class="border border-slate-800 p-3 rounded-lg bg-slate-900 space-y-2">
                <label class="text-xs font-semibold text-emerald-400">📋 12-प्वाइंट डिवाइस रिसीविंग चेकलिस्ट (जो ठीक है उसे टिक रखें):</label>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="chkDisplay" checked> 📱 डिस्प्ले ठीक है</label>
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="chkTouch" checked> 👆 टच OK</label>
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="chkCamera" checked> 📷 कैमरा OK</label>
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="chkCharging" checked> ⚡ चार्जिंग OK</label>
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="chkSpeaker" checked> 🔊 स्पीकर OK</label>
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="chkMic" checked> 🎤 माइक OK</label>
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="chkNetwork" checked> 📶 नेटवर्क OK</label>
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="chkWater"> 💧 पानी में गिरा</label>
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="chkDead"> 📴 डेड / ग्राहक रिस्क</label>
                </div>
            </div>
            <textarea id="jFault" placeholder="समस्या / ग्राहक की शिकायत विवरण..." class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white h-16"></textarea>
            <div class="grid grid-cols-2 gap-3">
                <input type="number" id="jEstCost" placeholder="अनुमानित खर्च ₹" class="bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                <input type="number" id="jAdvPaid" placeholder="एडवांस जमा राशि ₹" class="bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
            </div>
            <button onclick="saveJobCard()" class="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 rounded font-bold text-sm text-white">💾 जॉब कार्ड बनाएं व WhatsApp रसीद भेजें</button>
        </div>
    </div>

    <!-- C. ऑपरेटर जोड़ना व एडिट मॉडल -->
    <div id="newUserModal" class="hidden fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
        <div class="bg-slate-950 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4">
            <div class="flex justify-between items-center border-b border-slate-800 pb-2">
                <h3 class="font-bold text-lg text-white" id="userModalTitle">👥 ऑपरेटर व परमिशन सेट करें</h3>
                <button onclick="closeUserModal()"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <input type="hidden" id="editUserId" value="">
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label class="text-[11px] text-slate-400">पूरा नाम</label>
                    <input type="text" id="uFullName" placeholder="पूरा नाम" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                </div>
                <div>
                    <label class="text-[11px] text-slate-400">यूज़रनेम *</label>
                    <input type="text" id="uUsername" placeholder="यूज़रनेम" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                </div>
                <div>
                    <label class="text-[11px] text-slate-400" id="lblPass">पासवर्ड *</label>
                    <input type="password" id="uPassword" placeholder="पासवर्ड" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                </div>
                <div>
                    <label class="text-[11px] text-slate-400">मोबाइल नंबर</label>
                    <input type="text" id="uPhone" placeholder="मोबाइल नंबर" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-xs text-white">
                </div>
            </div>
            <div class="border border-slate-800 p-3 rounded-lg bg-slate-900 space-y-2">
                <span class="text-xs font-bold text-indigo-400">🔑 इस ऑपरेटर के पास कौन-से अधिकार होने चाहिए?</span>
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <label class="flex items-center gap-2"><input type="checkbox" id="permProfit"> 📈 मुनाफ़ा व खरीद दर देखें</label>
                    <label class="flex items-center gap-2"><input type="checkbox" id="permStock"> 📦 नया स्टॉक जोड़ें/एडिट करें</label>
                    <label class="flex items-center gap-2"><input type="checkbox" id="permDiscount"> 🏷️ बिलिंग में छूट/डिस्काउंट दें</label>
                    <label class="flex items-center gap-2"><input type="checkbox" id="permReports"> 📄 GSTR-1 व खर्चे देखें</label>
                </div>
            </div>
            <button onclick="saveOperatorUser()" class="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 rounded font-bold text-sm text-white">💾 परमिशन सुरक्षित करें</button>
        </div>
    </div>

    <!-- प्रिंट कंटेनर -->
    <div id="printableArea" class="hidden"></div>

    <!-- ==================== जावास्क्रिप्ट लॉजिक ==================== -->
    <script>
        let currentUser = null;
        let cart = [];
        let html5QrCode = null;
        let globalProducts = [];
        let globalUsers = [];

        function openLoginModal() { document.getElementById('loginModal').classList.remove('hidden'); }
        function closeLoginModal() { document.getElementById('loginModal').classList.add('hidden'); }

        function switchToCustomerStore() {
            document.getElementById('mainAppInterface').classList.add('hidden');
            document.getElementById('publicStoreView').classList.remove('hidden');
            loadPublicProducts();
        }

        async function handleUserLogin() {
            const u = document.getElementById('loginUsername').value.trim();
            const p = document.getElementById('loginPassword').value.trim();
            if(!u || !p) return alert("कृपया यूज़रनेम व पासवर्ड दर्ज करें!");

            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username: u, password: p })
            });
            const d = await res.json();
            if(d.success) {
                currentUser = d.user;
                applyUserRolePermissions();
                closeLoginModal();
                document.getElementById('publicStoreView').classList.add('hidden');
                document.getElementById('mainAppInterface').classList.remove('hidden');
                loadDashboardData();
            } else {
                alert("गलत यूज़रनेम या पासवर्ड!");
            }
        }

        function handleUserLogout() {
            currentUser = null;
            document.getElementById('loginUsername').value = '';
            document.getElementById('loginPassword').value = '';
            document.getElementById('mainAppInterface').classList.add('hidden');
            document.getElementById('publicStoreView').classList.remove('hidden');
            loadPublicProducts();
        }

        async function loadPublicProducts() {
            const res = await fetch('/api/get_stock');
            globalProducts = await res.json();
            renderPublicStore(globalProducts);
        }

        function renderPublicStore(list) {
            const grid = document.getElementById('publicProductGrid');
            grid.innerHTML = '';
            if(list.length === 0) {
                grid.innerHTML = '<div class="col-span-full text-center py-12 text-slate-500">कोई सामान नहीं मिला</div>';
                return;
            }
            list.forEach(p => {
                const img = p.image_data ? `<img src="${p.image_data}" class="w-full h-36 md:h-40 object-cover rounded-xl mb-3">` : `<div class="h-36 md:h-40 bg-slate-900 rounded-xl flex items-center justify-center text-4xl mb-3">📦</div>`;
                const inStock = p.stock_count > 0;
                grid.innerHTML += `
                    <div class="bg-slate-900 p-3.5 rounded-2xl border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition">
                        <div>
                            ${img}
                            <span class="text-[10px] font-semibold text-indigo-400 uppercase tracking-wider">${p.brand || 'Universal'}</span>
                            <h3 class="font-bold text-sm text-white mt-0.5 truncate">${p.name}</h3>
                            <div class="flex items-center justify-between mt-2">
                                <span class="text-emerald-400 font-bold text-base">₹${p.retail_price}</span>
                                <span class="text-[10px] px-2 py-0.5 rounded font-semibold ${inStock ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-rose-950 text-rose-400 border border-rose-800'}">${inStock ? 'उपलब्ध है' : 'स्टॉक समाप्त'}</span>
                            </div>
                        </div>
                        <a href="https://wa.me/91{{ settings.phone }}?text=नमस्ते *{{ settings.shop_name }}*, मुझे *${encodeURIComponent(p.name)}* (₹${p.retail_price}) खरीदना/ऑर्डर करना है।" target="_blank" class="mt-4 w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-center text-xs font-bold rounded-xl text-white flex items-center justify-center gap-1.5 transition shadow-lg shadow-emerald-900/30">
                            <i class="fa-brands fa-whatsapp text-sm"></i> WhatsApp ऑर्डर
                        </a>
                    </div>
                `;
            });
        }

        function filterPublicStore() {
            const q = document.getElementById('publicSearchInput').value.toLowerCase();
            const filtered = globalProducts.filter(p => p.name.toLowerCase().includes(q) || (p.brand && p.brand.toLowerCase().includes(q)));
            renderPublicStore(filtered);
        }

        function applyUserRolePermissions() {
            if(!currentUser) return;
            document.getElementById('activeUserNameDisplay').innerText = `${currentUser.full_name} (${currentUser.role})`;
            
            const isAdmin = currentUser.role === 'Admin';
            const canProfit = isAdmin || currentUser.can_view_profit === 1;
            const canStock = isAdmin || currentUser.can_edit_stock === 1;
            const canDiscount = isAdmin || currentUser.can_give_discount === 1;
            const canReports = isAdmin || currentUser.can_view_reports === 1;

            document.getElementById('userRoleBadge').innerText = isAdmin ? '● Master Admin' : '● Operator Active';
            document.getElementById('userRoleBadge').className = isAdmin ? 'text-xs text-amber-400 font-medium' : 'text-xs text-blue-400 font-medium';
            
            document.getElementById('kpiProfitBox').classList.toggle('hidden', !canProfit);
            document.getElementById('kpiStockValBox').classList.toggle('hidden', !canProfit);
            document.getElementById('thCost').classList.toggle('hidden', !canProfit);
            document.getElementById('addStockBtn').classList.toggle('hidden', !canStock);
            document.getElementById('discountInputRow').classList.toggle('hidden', !canDiscount);
            document.getElementById('navReportsBtn').classList.toggle('hidden', !canReports);
            document.getElementById('adminMenuSection').classList.toggle('hidden', !isAdmin);
        }

        function showModule(modId) {
            ['dashboard', 'pos', 'stock', 'stickers', 'repair', 'udhar', 'returns', 'operators', 'reports', 'store', 'settings'].forEach(m => {
                const el = document.getElementById('mod-' + m);
                if(el) el.classList.add('hidden');
            });
            const activeEl = document.getElementById('mod-' + modId);
            if(activeEl) activeEl.classList.remove('hidden');

            if(modId === 'dashboard') loadDashboardData();
            if(modId === 'stock') loadStockTable();
            if(modId === 'repair') loadRepairJobs();
            if(modId === 'udhar') loadUdharData();
            if(modId === 'operators') loadOperators();
            if(modId === 'store') loadOnlineStore();
            if(modId === 'stickers') loadStickerProducts();
        }

        function playBeep() {
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(1000, audioCtx.currentTime);
                osc.connect(audioCtx.destination);
                osc.start();
                osc.stop(audioCtx.currentTime + 0.15);
            } catch(e) {}
        }

        function toggleCameraScanner() {
            const container = document.getElementById('scannerContainer');
            if (container.classList.contains('hidden')) {
                container.classList.remove('hidden');
                html5QrCode = new Html5Qrcode("reader");
                html5QrCode.start({ facingMode: "environment" }, { fps: 10, qrbox: { width: 250, height: 250 } }, (decodedText) => {
                    playBeep();
                    handleScanAdd(decodedText);
                }).catch(err => alert("Camera Error: " + err));
            } else {
                container.classList.add('hidden');
                if(html5QrCode) html5QrCode.stop();
            }
        }

        async function handleScanAdd(code) {
            if(!code) return;
            const res = await fetch(`/api/scan_item?code=${encodeURIComponent(code)}`);
            const data = await res.json();
            if(data.success) {
                playBeep();
                cart.push({
                    type: 'Product',
                    product_id: data.item.product_id,
                    unit_id: data.item.unit_id,
                    name: data.item.name,
                    serial: data.item.serial_no,
                    cost: data.item.cost_price,
                    price: data.item.retail_price,
                    qty: 1
                });
                renderCart();
                document.getElementById('posBarcodeGunInput').value = '';
            } else {
                alert(data.message || 'सामान नहीं मिला!');
            }
        }

        function addCustomService(name, price) {
            cart.push({ type: 'Service', product_id: null, unit_id: null, name: name, serial: 'SERVICE', cost: 0, price: parseFloat(price), qty: 1 });
            renderCart();
        }

        function promptCustomLabour() {
            const name = prompt("सर्विस / काम का नाम लिखें:", "मोबाइल रिपेयरिंग लेबर चार्ज");
            if(!name) return;
            const price = prompt("फीस / दर (₹):", "150");
            if(price) addCustomService(name, price);
        }

        function renderCart() {
            const tbody = document.getElementById('posCartBody');
            tbody.innerHTML = '';
            let subtotal = 0;
            cart.forEach((item, index) => {
                subtotal += (item.price * item.qty);
                tbody.innerHTML += `
                    <tr class="border-b border-slate-800">
                        <td class="p-2 font-medium">${item.name}</td>
                        <td class="p-2 text-xs text-slate-400">${item.serial}</td>
                        <td class="p-2">₹${item.price}</td>
                        <td class="p-2">${item.qty}</td>
                        <td class="p-2 font-bold text-emerald-400">₹${item.price * item.qty}</td>
                        <td class="p-2 text-right"><button onclick="cart.splice(${index},1); renderCart();" class="text-rose-400"><i class="fa-solid fa-trash"></i></button></td>
                    </tr>
                `;
            });
            document.getElementById('posSubtotal').innerText = '₹' + subtotal;
            calcPosTotal();
        }

        function calcPosTotal() {
            let subtotal = cart.reduce((acc, it) => acc + (it.price * it.qty), 0);
            let disc = parseFloat(document.getElementById('posDiscount').value) || 0;
            document.getElementById('posGrandTotal').innerText = '₹' + Math.max(0, subtotal - disc);
        }

        function handlePayModeChange(val) {
            document.getElementById('splitInputBox').classList.toggle('hidden', val !== 'Split');
        }

        async function checkoutSale() {
            if(cart.length === 0) return alert('कार्ट खाली है!');
            const custName = document.getElementById('posCustName').value || 'Customer';
            const custPhone = document.getElementById('posCustPhone').value || '';
            const discount = parseFloat(document.getElementById('posDiscount').value) || 0;
            const payMode = document.getElementById('posPayMode').value;
            const splitCash = parseFloat(document.getElementById('posSplitCash').value) || 0;
            const splitUpi = parseFloat(document.getElementById('posSplitUpi').value) || 0;

            const res = await fetch('/api/checkout_sale', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    customer_name: custName,
                    customer_phone: custPhone,
                    items: cart,
                    discount: discount,
                    payment_mode: payMode,
                    cash_paid: splitCash,
                    upi_paid: splitUpi,
                    sold_by_name: currentUser ? currentUser.full_name : 'Staff'
                })
            });
            const result = await res.json();
            if(result.success) {
                alert(`✅ बिल तैयार! बिल नंबर: ${result.invoice_no}`);
                if(custPhone) {
                    const waText = `नमस्ते *${custName}* जी, *{{ settings.shop_name }}* से खरीद के लिए धन्यवाद! बिल नं: *${result.invoice_no}*, कुल राशि: *₹${result.total_amount}*।`;
                    window.open(`https://wa.me/91${custPhone}?text=${encodeURIComponent(waText)}`, '_blank');
                }
                cart = [];
                renderCart();
            }
        }

        function openNewProductModal() {
            document.getElementById('editProductId').value = '';
            document.getElementById('productModalTitle').innerText = '➕ नया स्टॉक जोड़ें';
            document.getElementById('pName').value = '';
            document.getElementById('pBrand').value = '';
            document.getElementById('pCost').value = '';
            document.getElementById('pRetail').value = '';
            document.getElementById('pQty').value = '5';
            document.getElementById('serialGridWrapper').classList.remove('hidden');
            document.getElementById('newProductModal').classList.remove('hidden');
            generateSerialGrid(5);
        }
        function closeProductModal() { document.getElementById('newProductModal').classList.add('hidden'); }

        function generateSerialGrid(qty) {
            const container = document.getElementById('serialGridContainer');
            container.innerHTML = '';
            const count = parseInt(qty) || 1;
            const seed = Math.floor(1000 + Math.random() * 9000);
            for(let i = 1; i <= count; i++) {
                container.innerHTML += `
                    <div class="flex gap-1 items-center">
                        <input type="text" id="serial_box_${i}" value="SN${seed}-${String(i).padStart(2,'0')}" class="w-full bg-slate-950 border border-slate-700 p-1.5 rounded text-xs text-white">
                        <button type="button" onclick="singleRandomize(${i})" class="px-1.5 py-1 bg-slate-800 hover:bg-slate-700 rounded text-xs">🎲</button>
                    </div>
                `;
            }
        }

        function singleRandomize(idx) {
            const el = document.getElementById(`serial_box_${idx}`);
            if(el) el.value = `SN${Math.floor(10000 + Math.random() * 90000)}-${String(idx).padStart(2,'0')}`;
        }

        function autoFillSerials() {
            const qty = parseInt(document.getElementById('pQty').value) || 1;
            generateSerialGrid(qty);
        }

        async function saveProductAndSerials() {
            const editId = document.getElementById('editProductId').value;
            const name = document.getElementById('pName').value.trim();
            const brand = document.getElementById('pBrand').value.trim();
            const packType = document.getElementById('pPackType').value;
            const cost = parseFloat(document.getElementById('pCost').value) || 0;
            const retail = parseFloat(document.getElementById('pRetail').value) || 0;
            const qty = parseInt(document.getElementById('pQty').value) || 1;

            if(!name || cost <= 0 || retail <= 0) return alert("कृपया सामान का नाम, खरीद दर व बिक्री दर भरें!");

            const serials = [];
            for(let i = 1; i <= qty; i++) {
                const el = document.getElementById(`serial_box_${i}`);
                if(el && el.value.trim()) serials.push(el.value.trim());
            }

            let photoData = "";
            const fileInput = document.getElementById('pPhotoFile');
            if(fileInput.files.length > 0) {
                photoData = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = (e) => resolve(e.target.result);
                    reader.readAsDataURL(fileInput.files[0]);
                });
            }

            const res = await fetch('/api/add_product', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    product_id: editId,
                    name: name,
                    brand: brand,
                    packaging_type: packType,
                    purchase_cost: cost,
                    retail_price: retail,
                    quantity: qty,
                    serials: serials,
                    image_data: photoData
                })
            });
            const d = await res.json();
            if(d.success) {
                alert("🎉 सामान व स्टॉक सुरक्षित हो गया!");
                closeProductModal();
                loadStockTable();
                loadPublicProducts();
            }
        }

        async function editProductStock(pId) {
            const p = globalProducts.find(x => x.id === pId);
            if(!p) return;
            document.getElementById('editProductId').value = p.id;
            document.getElementById('productModalTitle').innerText = '✏️ स्टॉक एडिट व करेक्शन';
            document.getElementById('pName').value = p.name;
            document.getElementById('pBrand').value = p.brand;
            document.getElementById('pCost').value = p.purchase_cost;
            document.getElementById('pRetail').value = p.retail_price;
            document.getElementById('pPackType').value = p.packaging_type;
            document.getElementById('serialGridWrapper').classList.add('hidden');
            document.getElementById('newProductModal').classList.remove('hidden');
        }

        async function loadStockTable() {
            const res = await fetch('/api/get_stock');
            globalProducts = await res.json();
            const tbody = document.getElementById('stockTableBody');
            tbody.innerHTML = '';
            globalProducts.forEach(p => {
                const imgTag = p.image_data ? `<img src="${p.image_data}" class="w-8 h-8 object-cover rounded">` : `<span class="text-xl">📦</span>`;
                const canProfit = currentUser && (currentUser.role === 'Admin' || currentUser.can_view_profit === 1);
                const costCell = canProfit ? `<td class="p-2">₹${p.purchase_cost}</td>` : `<td class="p-2 text-slate-500">🔒 छिपा है</td>`;
                tbody.innerHTML += `
                    <tr class="border-b border-slate-800">
                        <td class="p-2">${imgTag}</td>
                        <td class="p-2 font-medium">${p.name}</td>
                        <td class="p-2 text-xs text-slate-400">${p.brand || 'General'}</td>
                        <td class="p-2 text-xs">${p.packaging_type || 'Loose'}</td>
                        ${costCell}
                        <td class="p-2 font-semibold text-emerald-400">₹${p.retail_price}</td>
                        <td class="p-2 font-bold">${p.stock_count}</td>
                        <td class="p-2 text-right">
                            <button onclick="editProductStock(${p.id})" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700"><i class="fa-solid fa-pen"></i> एडिट</button>
                        </td>
                    </tr>
                `;
            });
        }

        function filterStockTable() {
            const q = document.getElementById('stockSearchInput').value.toLowerCase();
            document.querySelectorAll('#stockTableBody tr').forEach(r => r.style.display = r.innerText.toLowerCase().includes(q) ? '' : 'none');
        }

        function loadStickerProducts() {
            const sel = document.getElementById('stickerProductSelect');
            sel.innerHTML = '<option value="">सामान चुनें...</option>';
            globalProducts.forEach(p => sel.innerHTML += `<option value="${p.id}">${p.name} (स्टॉक: ${p.stock_count})</option>`);
        }

        async function loadProductUnitsForStickers(pId) {
            if(!pId) return;
            const res = await fetch(`/api/get_product_units?product_id=${pId}`);
            const units = await res.json();
            const grid = document.getElementById('stickerPreviewGrid');
            grid.innerHTML = '';
            units.forEach((u, idx) => {
                grid.innerHTML += `
                    <div class="bg-white text-black p-2 rounded border border-slate-300 w-44 text-center font-sans">
                        <div class="text-[9px] font-bold uppercase text-blue-600 truncate">{{ settings.shop_name }}</div>
                        <div class="text-[10px] font-bold truncate">${u.name}</div>
                        <svg id="bc_${idx}" class="mx-auto my-1"></svg>
                        <div class="text-[10px] font-bold">MRP: ₹${u.retail_price}</div>
                    </div>
                `;
                setTimeout(() => JsBarcode(`#bc_${idx}`, u.serial_no, { format: "CODE128", width: 1.3, height: 24, fontSize: 9, displayValue: true, margin: 0 }), 50);
            });
        }

        function printGeneratedStickers() {
            const content = document.getElementById('stickerPreviewGrid').innerHTML;
            if(!content) return alert("पहले कोई सामान चुनें!");
            const win = window.open('', '', 'height=600,width=800');
            win.document.write(`<html><head><title>Print Stickers</title><style>body { margin: 5px; display: flex; flex-wrap: wrap; gap: 6px; font-family: Arial, sans-serif; }</style></head><body>${content}</body></html>`);
            win.document.close();
            win.print();
        }

        function openNewJobCardModal() { document.getElementById('newJobModal').classList.remove('hidden'); }
        function closeJobModal() { document.getElementById('newJobModal').classList.add('hidden'); }

        async function saveJobCard() {
            const cName = document.getElementById('jCustName').value.trim();
            const cPhone = document.getElementById('jCustPhone').value.trim();
            const bModel = document.getElementById('jBrandModel').value.trim();
            const pin = document.getElementById('jPassPin').value.trim();
            const fault = document.getElementById('jFault').value.trim();
            const estCost = parseFloat(document.getElementById('jEstCost').value) || 0;
            const advPaid = parseFloat(document.getElementById('jAdvPaid').value) || 0;

            if(!cName || !cPhone || !bModel) return alert("कृपया ग्राहक का नाम, मोबाइल व मॉडल भरें!");

            const checklist = {
                display: document.getElementById('chkDisplay').checked,
                touch: document.getElementById('chkTouch').checked,
                camera: document.getElementById('chkCamera').checked,
                charging: document.getElementById('chkCharging').checked,
                speaker: document.getElementById('chkSpeaker').checked,
                mic: document.getElementById('chkMic').checked,
                network: document.getElementById('chkNetwork').checked,
                water: document.getElementById('chkWater').checked,
                dead: document.getElementById('chkDead').checked
            };

            const res = await fetch('/api/add_repair_job', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ customer_name: cName, customer_phone: cPhone, brand_model: bModel, pattern_pin: pin, fault, estimated_cost: estCost, advance_paid: advPaid, checklist })
            });
            const d = await res.json();
            if(d.success) {
                alert(`🎉 जॉब कार्ड ${d.job_no} तैयार हुआ!`);
                closeJobModal();
                loadRepairJobs();
                const waText = `नमस्ते *${cName}* जी, आपका फोन (*${bModel}*) रिपेयरिंग हेतु प्राप्त हुआ। जॉब नं: *${d.job_no}*, अनुमानित खर्च: ₹${estCost}। {{ settings.shop_name }}`;
                window.open(`https://wa.me/91${cPhone}?text=${encodeURIComponent(waText)}`, '_blank');
            }
        }

        async function loadRepairJobs() {
            const res = await fetch('/api/get_repair_jobs');
            const jobs = await res.json();
            const tbody = document.getElementById('repairJobTableBody');
            tbody.innerHTML = '';
            jobs.forEach(j => {
                tbody.innerHTML += `
                    <tr class="border-b border-slate-800">
                        <td class="p-2 font-semibold text-cyan-400">${j.job_no}</td>
                        <td class="p-2">${j.customer_name}<br><small class="text-slate-400">${j.customer_phone}</small></td>
                        <td class="p-2">${j.brand_model}<br><small class="text-amber-300">${j.fault_description}</small></td>
                        <td class="p-2">₹${j.estimated_cost}</td>
                        <td class="p-2 text-emerald-400">₹${j.advance_paid}</td>
                        <td class="p-2"><span class="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-900 text-blue-200">${j.status}</span></td>
                        <td class="p-2 text-right">
                            <button onclick="updateJobStatus('${j.job_no}', '${j.customer_phone}', '${j.customer_name}', '${j.brand_model}')" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700">अपडेट</button>
                        </td>
                    </tr>
                `;
            });
        }

        async function updateJobStatus(jobNo, phone, name, model) {
            const st = prompt("नया स्टेटस दर्ज करें (RECEIVED, INSPECTION, WAITING_PARTS, REPAIRING, READY, DELIVERED):", "READY");
            if(!st) return;
            await fetch('/api/update_job_status', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ job_no: jobNo, status: st }) });
            if(st === 'READY') {
                const msg = `नमस्ते *${name}* जी, आपका फोन (*${model}*) तैयार (READY) हो चुका है। कृपया दुकान पर आकर प्राप्त कर लें। {{ settings.shop_name }}`;
                window.open(`https://wa.me/91${phone}?text=${encodeURIComponent(msg)}`, '_blank');
            }
            loadRepairJobs();
        }

        async function loadUdharData() {
            const res = await fetch('/api/get_udhar_ledger');
            const list = await res.json();
            const tbody = document.getElementById('udharTableBody');
            tbody.innerHTML = '';
            list.forEach(u => {
                tbody.innerHTML += `
                    <tr class="border-b border-slate-800">
                        <td class="p-2 font-medium">${u.customer_name}</td>
                        <td class="p-2 text-slate-400">${u.customer_phone}</td>
                        <td class="p-2">₹${u.total_udhar}</td>
                        <td class="p-2 text-emerald-400">₹${u.paid_amount}</td>
                        <td class="p-2 font-bold text-rose-400">₹${u.due_amount}</td>
                        <td class="p-2 text-right space-x-1">
                            <button onclick="payUdhar('${u.customer_phone}', ${u.due_amount})" class="px-2 py-1 bg-emerald-700 hover:bg-emerald-600 text-xs rounded">💰 चुकता</button>
                            <a href="https://wa.me/91${u.customer_phone}?text=नमस्ते ${encodeURIComponent(u.customer_name)} जी, आपकी बकाया उधारी ₹${u.due_amount} है। कृपया भुगतान करें। {{ settings.shop_name }}" target="_blank" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700">📲 WhatsApp</a>
                        </td>
                    </tr>
                `;
            });
        }

        async function payUdhar(phone, currentDue) {
            const amt = prompt(`जमा राशि दर्ज करें (कुल बकाया ₹${currentDue}):`, currentDue);
            if(!amt || parseFloat(amt) <= 0) return;
            await fetch('/api/pay_udhar', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ customer_phone: phone, amount: parseFloat(amt) }) });
            alert("✅ उधारी भुगतान जमा हुआ!");
            loadUdharData();
        }

        function openNewUserModal() { 
            document.getElementById('editUserId').value = '';
            document.getElementById('userModalTitle').innerText = '👥 नया ऑपरेटर जोड़ें';
            document.getElementById('uFullName').value = '';
            document.getElementById('uUsername').value = '';
            document.getElementById('uPassword').value = '';
            document.getElementById('uPhone').value = '';
            document.getElementById('permProfit').checked = false;
            document.getElementById('permStock').checked = false;
            document.getElementById('permDiscount').checked = false;
            document.getElementById('permReports').checked = false;
            document.getElementById('uUsername').removeAttribute('readonly');
            document.getElementById('lblPass').innerText = 'पासवर्ड *';
            document.getElementById('newUserModal').classList.remove('hidden'); 
        }

        function closeUserModal() { document.getElementById('newUserModal').classList.add('hidden'); }

        function editOperatorPermissions(userId) {
            const u = globalUsers.find(x => x.id === userId);
            if(!u) return;
            document.getElementById('editUserId').value = u.id;
            document.getElementById('userModalTitle').innerText = `✏️ '${u.full_name}' की परमिशन एडिट करें`;
            document.getElementById('uFullName').value = u.full_name;
            document.getElementById('uUsername').value = u.username;
            document.getElementById('uUsername').setAttribute('readonly', true);
            document.getElementById('uPassword').value = '';
            document.getElementById('lblPass').innerText = 'नया पासवर्ड (खाली छोड़ें यदि नहीं बदलना)';
            document.getElementById('uPhone').value = u.phone || '';
            document.getElementById('permProfit').checked = u.can_view_profit === 1;
            document.getElementById('permStock').checked = u.can_edit_stock === 1;
            document.getElementById('permDiscount').checked = u.can_give_discount === 1;
            document.getElementById('permReports').checked = u.can_view_reports === 1;
            document.getElementById('newUserModal').classList.remove('hidden');
        }

        async function saveOperatorUser() {
            const editId = document.getElementById('editUserId').value;
            const fullName = document.getElementById('uFullName').value.trim();
            const uname = document.getElementById('uUsername').value.trim();
            const pass = document.getElementById('uPassword').value.trim();
            const phone = document.getElementById('uPhone').value.trim();

            if(!uname) return alert("यूज़रनेम अनिवार्य है!");
            if(!editId && !pass) return alert("नए ऑपरेटर के लिए पासवर्ड अनिवार्य है!");

            const res = await fetch('/api/save_user_permissions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id: editId,
                    full_name: fullName,
                    username: uname,
                    password: pass,
                    phone: phone,
                    can_view_profit: document.getElementById('permProfit').checked ? 1 : 0,
                    can_edit_stock: document.getElementById('permStock').checked ? 1 : 0,
                    can_give_discount: document.getElementById('permDiscount').checked ? 1 : 0,
                    can_view_reports: document.getElementById('permReports').checked ? 1 : 0
                })
            });
            const d = await res.json();
            if(d.success) {
                alert("✅ ऑपरेटर परमिशन सफलतापूर्वक सुरक्षित हो गई!");
                closeUserModal();
                loadOperators();
            } else {
                alert("त्रुटि: " + d.message);
            }
        }

        async function loadOperators() {
            const res = await fetch('/api/get_users');
            globalUsers = await res.json();
            const tbody = document.getElementById('operatorsTableBody');
            tbody.innerHTML = '';
            globalUsers.forEach(u => {
                const isMaster = u.username === 'admin';
                tbody.innerHTML += `
                    <tr class="border-b border-slate-800">
                        <td class="p-2 font-medium">${u.full_name}</td>
                        <td class="p-2 text-slate-400">${u.username}</td>
                        <td class="p-2"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${isMaster ? 'bg-amber-900 text-amber-200' : 'bg-indigo-900 text-indigo-200'}">${u.role}</span></td>
                        <td class="p-2">${u.can_view_profit ? '✅ हाँ' : '❌ नहीं'}</td>
                        <td class="p-2">${u.can_edit_stock ? '✅ हाँ' : '❌ नहीं'}</td>
                        <td class="p-2">${u.can_give_discount ? '✅ हाँ' : '❌ नहीं'}</td>
                        <td class="p-2">${u.can_view_reports ? '✅ हाँ' : '❌ नहीं'}</td>
                        <td class="p-2 text-right space-x-1">
                            ${!isMaster ? `
                                <button onclick="editOperatorPermissions(${u.id})" class="px-2 py-1 bg-indigo-700 hover:bg-indigo-600 text-white rounded text-xs">✏️ एडिट परमिशन</button>
                                <button onclick="deleteOperator(${u.id})" class="px-2 py-1 bg-rose-900/60 hover:bg-rose-800 text-rose-300 rounded text-xs">🗑️ हटाएं</button>
                            ` : '<span class="text-xs text-amber-400 font-semibold">🔒 मुख्य एडमिन</span>'}
                        </td>
                    </tr>
                `;
            });
        }

        async function deleteOperator(id) {
            if(!confirm("क्या आप वाकई इस ऑपरेटर को हटाना चाहते हैं?")) return;
            await fetch('/api/delete_user', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
            loadOperators();
        }

        async function loadOnlineStore() {
            const res = await fetch('/api/get_stock');
            const prods = await res.json();
            const grid = document.getElementById('onlineStoreGrid');
            grid.innerHTML = '';
            prods.forEach(p => {
                const img = p.image_data ? `<img src="${p.image_data}" class="w-full h-32 object-cover rounded-md mb-2">` : `<div class="h-32 bg-slate-900 rounded flex items-center justify-center text-4xl mb-2">📦</div>`;
                grid.innerHTML += `
                    <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 flex flex-col justify-between">
                        <div>
                            ${img}
                            <h4 class="font-bold text-sm truncate">${p.name}</h4>
                            <p class="text-xs text-slate-400">${p.brand || 'Universal'}</p>
                            <div class="text-emerald-400 font-bold text-base mt-1">₹${p.retail_price}</div>
                        </div>
                        <a href="https://wa.me/91{{ settings.phone }}?text=नमस्ते मुझे '${encodeURIComponent(p.name)}' (₹${p.retail_price}) ऑर्डर करना है।" target="_blank" class="mt-3 w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-center text-xs font-bold rounded text-white block">📲 WhatsApp ऑर्डर</a>
                    </div>
                `;
            });
        }

        async function saveSettings() {
            await fetch('/api/save_settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    shop_name: document.getElementById('cfgShopName').value,
                    phone: document.getElementById('cfgPhone').value,
                    upi_id: document.getElementById('cfgUpi').value
                })
            });
            alert("✅ सेटिंग्स सुरक्षित हो गईं!");
            location.reload();
        }

        async function submitExpense() {
            const cat = document.getElementById('expCategory').value;
            const amt = parseFloat(document.getElementById('expAmount').value) || 0;
            if(!cat || amt <= 0) return alert("खर्च श्रेणी व राशि भरें!");
            await fetch('/api/add_expense', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ category: cat, amount: amt }) });
            alert("✅ खर्च दर्ज हुआ!");
            document.getElementById('expAmount').value = '';
        }

        async function submitReturn() {
            const inv = document.getElementById('retInvoiceNo').value;
            const item = document.getElementById('retItemName').value;
            const amt = parseFloat(document.getElementById('retAmount').value) || 0;
            if(!inv || !item) return alert("बिल नंबर व सामान का नाम भरें!");
            await fetch('/api/process_return', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ invoice_no: inv, item_name: item, refund_amount: amt }) });
            alert("✅ सेल्स रिटर्न दर्ज हुआ!");
        }

        async function loadDashboardData() {
            const res = await fetch('/api/dashboard_metrics');
            const d = await res.json();
            document.getElementById('kpiTodaySales').innerText = '₹' + d.today_sales;
            document.getElementById('kpiTodayProfit').innerText = '₹' + d.today_profit;
            document.getElementById('kpiRepairRevenue').innerText = '₹' + d.repair_revenue;
            document.getElementById('kpiDrawerCash').innerText = '₹' + d.drawer_cash;
            document.getElementById('kpiTotalUdhar').innerText = '₹' + d.total_udhar;
            document.getElementById('kpiStockVal').innerText = '₹' + d.stock_value;

            new Chart(document.getElementById('salesProfitChart'), {
                type: 'bar',
                data: {
                    labels: d.chart_days,
                    datasets: [
                        { label: 'बिक्री (₹)', data: d.chart_sales, backgroundColor: '#10b981' },
                        { label: 'शुद्ध मुनाफ़ा (₹)', data: d.chart_profit, backgroundColor: '#3b82f6' }
                    ]
                },
                options: { responsive: true }
            });
        }

        window.onload = loadPublicProducts;
    </script>
</body>
</html>
"""

# ==================== बैकएंड API रूट्स ====================

@app.route('/')
def home():
    conn = get_db()
    settings = conn.execute('SELECT * FROM settings WHERE id=1').fetchone()
    conn.close()
    return render_template_string(MASTER_HTML, settings=settings)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    u = data.get('username', '').strip()
    p = data.get('password', '').strip()
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username=?', (u,)).fetchone()
    conn.close()
    if user:
        stored_pass = user['password']
        is_valid = False
        if stored_pass.startswith('pbkdf2:') or stored_pass.startswith('scrypt:'):
            is_valid = check_password_hash(stored_pass, p)
        else:
            is_valid = (stored_pass == p)
        
        if is_valid:
            user_dict = dict(user)
            user_dict.pop('password', None)
            return jsonify({"success": True, "user": user_dict})
    return jsonify({"success": False})

@app.route('/api/dashboard_metrics')
def api_dashboard_metrics():
    conn = get_db()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    sales_cur = conn.execute("SELECT SUM(total_amount), SUM(profit_amount), SUM(cash_paid), SUM(udhar_amount) FROM sales WHERE DATE(created_at)=?", (today,)).fetchone()
    today_sales = sales_cur[0] or 0
    today_profit = sales_cur[1] or 0

    rep_cur = conn.execute("SELECT SUM(advance_paid) FROM repair_jobs WHERE DATE(created_at)=?", (today,)).fetchone()
    repair_rev = rep_cur[0] or 0

    udhar_cur = conn.execute("SELECT SUM(due_amount) FROM customer_udhar").fetchone()
    total_udhar = udhar_cur[0] or 0

    stock_cur = conn.execute("SELECT SUM(purchase_cost) FROM products p JOIN product_units u ON p.id=u.product_id WHERE u.status='IN_STOCK'").fetchone()
    stock_val = stock_cur[0] or 0

    conn.close()
    return jsonify({
        "today_sales": today_sales,
        "today_profit": today_profit,
        "repair_revenue": repair_rev,
        "drawer_cash": sales_cur[2] or 0,
        "total_udhar": total_udhar,
        "stock_value": stock_val,
        "chart_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "chart_sales": [12000, 18500, 14200, 22000, 28450, 31000, today_sales],
        "chart_profit": [3200, 4800, 3900, 6100, 7820, 8500, today_profit]
    })

@app.route('/api/add_product', methods=['POST'])
def api_add_product():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    p_id = data.get('product_id')
    
    if p_id:
        if data.get('image_data'):
            c.execute('''UPDATE products SET name=?, brand=?, packaging_type=?, purchase_cost=?, retail_price=?, image_data=? WHERE id=?''',
                      (data.get('name'), data.get('brand'), data.get('packaging_type'), float(data.get('purchase_cost', 0)), float(data.get('retail_price', 0)), data.get('image_data'), p_id))
        else:
            c.execute('''UPDATE products SET name=?, brand=?, packaging_type=?, purchase_cost=?, retail_price=? WHERE id=?''',
                      (data.get('name'), data.get('brand'), data.get('packaging_type'), float(data.get('purchase_cost', 0)), float(data.get('retail_price', 0)), p_id))
    else:
        c.execute('''INSERT INTO products (name, brand, packaging_type, purchase_cost, retail_price, image_data)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (data.get('name'), data.get('brand'), data.get('packaging_type'), float(data.get('purchase_cost', 0)), float(data.get('retail_price', 0)), data.get('image_data', '')))
        p_id = c.lastrowid
        for sn in data.get('serials', []):
            c.execute("INSERT OR REPLACE INTO product_units (product_id, serial_no, status) VALUES (?, ?, 'IN_STOCK')", (p_id, sn))

    conn.commit()
    conn.close()
    trigger_auto_backup()
    return jsonify({"success": True})

@app.route('/api/get_stock')
def api_get_stock():
    conn = get_db()
    prods = conn.execute('''SELECT p.*, COUNT(u.id) as stock_count FROM products p LEFT JOIN product_units u ON p.id = u.product_id AND u.status = 'IN_STOCK' GROUP BY p.id''').fetchall()
    res = [dict(p) for p in prods]
    conn.close()
    return jsonify(res)

@app.route('/api/get_product_units')
def api_get_product_units():
    p_id = request.args.get('product_id')
    conn = get_db()
    units = conn.execute('''SELECT u.serial_no, p.name, p.retail_price FROM product_units u JOIN products p ON u.product_id = p.id WHERE u.product_id = ? AND u.status = 'IN_STOCK' ''', (p_id,)).fetchall()
    res = [dict(u) for u in units]
    conn.close()
    return jsonify(res)

@app.route('/api/scan_item')
def api_scan_item():
    code = request.args.get('code', '').strip()
    conn = get_db()
    unit = conn.execute('''SELECT u.id as unit_id, u.serial_no, p.id as product_id, p.name, p.purchase_cost, p.retail_price FROM product_units u JOIN products p ON u.product_id = p.id WHERE u.serial_no = ? AND u.status = 'IN_STOCK' ''', (code,)).fetchone()
    if unit:
        conn.close()
        return jsonify({
            "success": True,
            "item": {
                "unit_id": unit["unit_id"],
                "product_id": unit["product_id"],
                "name": unit["name"],
                "serial_no": unit["serial_no"],
                "cost_price": unit["purchase_cost"],
                "retail_price": unit["retail_price"]
            }
        })
    conn.close()
    return jsonify({"success": False, "message": "सामान स्टॉक में नहीं मिला!"})

@app.route('/api/checkout_sale', methods=['POST'])
def api_checkout_sale():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    inv_no = f"BILL-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
    items = data.get('items', [])
    discount = float(data.get('discount', 0))
    pay_mode = data.get('payment_mode', 'Cash')

    subtotal = sum(float(it['price']) * int(it['qty']) for it in items)
    cost_total = sum(float(it.get('cost', 0)) * int(it['qty']) for it in items)
    grand_total = max(0, subtotal - discount)
    net_profit = max(0, grand_total - cost_total)

    cash_paid = grand_total if pay_mode == 'Cash' else (float(data.get('cash_paid', 0)) if pay_mode == 'Split' else 0)
    upi_paid = grand_total if pay_mode == 'UPI' else (float(data.get('upi_paid', 0)) if pay_mode == 'Split' else 0)
    udhar_amt = grand_total if pay_mode == 'Udhar' else 0

    c.execute('''INSERT INTO sales (invoice_no, customer_name, customer_phone, subtotal, discount, total_amount, profit_amount, payment_mode, cash_paid, upi_paid, udhar_amount, sold_by_name)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (inv_no, data.get('customer_name'), data.get('customer_phone'), subtotal, discount, grand_total, net_profit, pay_mode, cash_paid, upi_paid, udhar_amt, data.get('sold_by_name', 'Staff')))
    sale_id = c.lastrowid

    for it in items:
        c.execute('''INSERT INTO sale_items (sale_id, item_type, product_id, unit_id, item_name, serial_no, cost_price, sell_price, qty)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (sale_id, it.get('type'), it.get('product_id'), it.get('unit_id'), it['name'], it.get('serial'), it.get('cost', 0), it['price'], it['qty']))
        if it.get('unit_id'):
            c.execute("UPDATE product_units SET status='SOLD' WHERE id=?", (it['unit_id'],))

    if udhar_amt > 0 and data.get('customer_phone'):
        c.execute('''INSERT INTO customer_udhar (customer_name, customer_phone, total_udhar, due_amount)
                     VALUES (?, ?, ?, ?)
                     ON CONFLICT(customer_phone) DO UPDATE SET total_udhar=total_udhar+?, due_amount=due_amount+?''',
                  (data.get('customer_name'), data.get('customer_phone'), udhar_amt, udhar_amt, udhar_amt, udhar_amt))

    conn.commit()
    conn.close()
    trigger_auto_backup()
    return jsonify({"success": True, "invoice_no": inv_no, "total_amount": grand_total})

@app.route('/api/add_repair_job', methods=['POST'])
def api_add_repair_job():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    job_no = f"JOB-{datetime.datetime.now().strftime('%y%m%d%H%M')}"
    c.execute('''INSERT INTO repair_jobs (job_no, customer_name, customer_phone, brand_model, pattern_pin, fault_description, estimated_cost, advance_paid, remaining_balance, checklist_data, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'RECEIVED')''',
              (job_no, data.get('customer_name'), data.get('customer_phone'), data.get('brand_model'), data.get('pattern_pin'), data.get('fault'), float(data.get('estimated_cost', 0)), float(data.get('advance_paid', 0)), float(data.get('estimated_cost', 0)) - float(data.get('advance_paid', 0)), json.dumps(data.get('checklist', {}))))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "job_no": job_no})

@app.route('/api/get_repair_jobs')
def api_get_repair_jobs():
    conn = get_db()
    jobs = conn.execute("SELECT * FROM repair_jobs ORDER BY id DESC").fetchall()
    res = [dict(j) for j in jobs]
    conn.close()
    return jsonify(res)

@app.route('/api/update_job_status', methods=['POST'])
def api_update_job_status():
    data = request.json
    conn = get_db()
    conn.execute("UPDATE repair_jobs SET status=? WHERE job_no=?", (data.get('status'), data.get('job_no')))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/get_udhar_ledger')
def api_get_udhar_ledger():
    conn = get_db()
    rows = conn.execute("SELECT * FROM customer_udhar WHERE due_amount > 0").fetchall()
    res = [dict(r) for r in rows]
    conn.close()
    return jsonify(res)

@app.route('/api/pay_udhar', methods=['POST'])
def api_pay_udhar():
    data = request.json
    phone = data.get('customer_phone')
    amt = float(data.get('amount', 0))
    conn = get_db()
    conn.execute("UPDATE customer_udhar SET paid_amount=paid_amount+?, due_amount=due_amount-? WHERE customer_phone=?", (amt, amt, phone))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/get_users')
def api_get_users():
    conn = get_db()
    users = conn.execute("SELECT id, username, full_name, phone, role, commission_percent, can_view_profit, can_edit_stock, can_give_discount, can_view_reports FROM users").fetchall()
    res = [dict(u) for u in users]
    conn.close()
    return jsonify(res)

@app.route('/api/save_user_permissions', methods=['POST'])
def api_save_user_permissions():
    data = request.json
    u_id = data.get('id')
    conn = get_db()
    c = conn.cursor()
    
    if u_id:
        if data.get('password'):
            hashed_p = generate_password_hash(data.get('password'))
            c.execute('''UPDATE users SET full_name=?, phone=?, password=?, can_view_profit=?, can_edit_stock=?, can_give_discount=?, can_view_reports=? WHERE id=?''',
                      (data.get('full_name'), data.get('phone'), hashed_p, data.get('can_view_profit', 0), data.get('can_edit_stock', 0), data.get('can_give_discount', 0), data.get('can_view_reports', 0), u_id))
        else:
            c.execute('''UPDATE users SET full_name=?, phone=?, can_view_profit=?, can_edit_stock=?, can_give_discount=?, can_view_reports=? WHERE id=?''',
                      (data.get('full_name'), data.get('phone'), data.get('can_view_profit', 0), data.get('can_edit_stock', 0), data.get('can_give_discount', 0), data.get('can_view_reports', 0), u_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    else:
        uname = data.get('username', '').strip()
        passw = data.get('password', '').strip()
        if not uname or not passw:
            conn.close()
            return jsonify({"success": False, "message": "यूज़रनेम व पासवर्ड अनिवार्य हैं!"})
        try:
            hashed_p = generate_password_hash(passw)
            c.execute('''INSERT INTO users (username, password, full_name, phone, role, can_view_profit, can_edit_stock, can_give_discount, can_view_reports)
                         VALUES (?, ?, ?, ?, 'Operator', ?, ?, ?, ?)''',
                      (uname, hashed_p, data.get('full_name'), data.get('phone'),
                       data.get('can_view_profit', 0), data.get('can_edit_stock', 0), data.get('can_give_discount', 0), data.get('can_view_reports', 0)))
            conn.commit()
            conn.close()
            return jsonify({"success": True})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"success": False, "message": "यूज़रनेम पहले से मौजूद है!"})

@app.route('/api/delete_user', methods=['POST'])
def api_delete_user():
    data = request.json
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=? AND username != 'admin'", (data.get('id'),))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/save_settings', methods=['POST'])
def api_save_settings():
    data = request.json
    conn = get_db()
    conn.execute("UPDATE settings SET shop_name=?, phone=?, upi_id=? WHERE id=1", (data.get('shop_name'), data.get('phone'), data.get('upi_id')))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/add_expense', methods=['POST'])
def api_add_expense():
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO expenses (category, amount) VALUES (?, ?)", (data.get('category'), float(data.get('amount', 0))))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/process_return', methods=['POST'])
def api_process_return():
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO returns (invoice_no, item_name, refund_amount) VALUES (?, ?, ?)", (data.get('invoice_no'), data.get('item_name'), float(data.get('refund_amount', 0))))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/export_gstr1')
def api_export_gstr1():
    conn = get_db()
    sales = conn.execute("SELECT invoice_no, customer_name, created_at, total_amount, payment_mode FROM sales").fetchall()
    csv_data = "Invoice No,Customer Name,Date,Amount,Mode\\n" + "\\n".join([f"{s['invoice_no']},{s['customer_name']},{s['created_at']},{s['total_amount']},{s['payment_mode']}" for s in sales])
    conn.close()
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=GSTR1.csv"})

@app.route('/api/download_db')
def api_download_db():
    if os.path.exists(DB_NAME):
        return send_file(DB_NAME, as_attachment=True)
    return "Not Found", 404

if __name__ == '__main__':
    print("==================================================")
    print("🚀 Single Master Link System Started!")
    print("🌐 Open URL: http://127.0.0.1:5000")
    print("==================================================")
    app.run(host='0.0.0.0', port=5000, debug=True)