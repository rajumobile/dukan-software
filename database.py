import sqlite3

def init_db():
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute("DROP TABLE IF EXISTS sales")
    
    # स्टॉक टेबल (min_alert कॉलम के साथ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            buy_price REAL NOT NULL,
            sell_price REAL NOT NULL,
            stock INTEGER NOT NULL,
            min_alert INTEGER DEFAULT 3
        )
    """)

    # बिक्री/बिलिंग टेबल
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            sell_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            profit REAL NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("डेटाबेस अपडेट हो गया!")

if __name__ == "__main__":
    init_db()