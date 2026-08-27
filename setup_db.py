import sqlite3

conn = sqlite3.connect("shop.db")
cursor = conn.cursor()

# सभी पुरानी अधूरी टेबल्स को रिसेट करना
cursor.execute("DROP TABLE IF EXISTS users")
cursor.execute("DROP TABLE IF EXISTS products")
cursor.execute("DROP TABLE IF EXISTS sales")

# 1. यूज़र्स
cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
""")
cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
cursor.execute("INSERT INTO users (username, password, role) VALUES ('operator', 'op123', 'operator')")

# 2. प्रोडक्ट्स
cursor.execute("""
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        buy_price REAL NOT NULL,
        sell_price REAL NOT NULL,
        stock INTEGER NOT NULL,
        min_alert INTEGER DEFAULT 3
    )
""")

# 3. सेल्स
cursor.execute("""
    CREATE TABLE sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        sell_price REAL NOT NULL,
        total_amount REAL NOT NULL,
        profit REAL NOT NULL,
        sold_by TEXT,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

conn.commit()
conn.close()
print("डेटाबेस पूरी तरह नया और दुरुस्त तैयार हो गया!")