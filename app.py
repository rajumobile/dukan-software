import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

def get_db_connection():
    return sqlite3.connect("shop.db")

# नया स्टॉक जोड़ना
def add_product():
    name = entry_name.get().strip()
    buy_p = entry_buy_price.get().strip()
    sell_p = entry_sell_price.get().strip()
    stock_qty = entry_stock.get().strip()
    alert_qty = entry_alert.get().strip()

    if not name or not buy_p or not sell_p or not stock_qty:
        messagebox.showwarning("चेतावनी", "कृपया सभी ज़रूरी फ़ील्ड भरें!")
        return

    try:
        b_p = round(float(buy_p), 2)
        s_p = round(float(sell_p), 2)
        stk = int(stock_qty)
        alt = int(alert_qty) if alert_qty else 3

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (name, buy_price, sell_price, stock, min_alert) 
            VALUES (?, ?, ?, ?, ?)
        """, (name, b_p, s_p, stk, alt))
        conn.commit()
        conn.close()
        
        messagebox.showinfo("सफलता", f"'{name}' स्टॉक में जुड़ गया!")
        entry_name.delete(0, tk.END)
        entry_buy_price.delete(0, tk.END)
        entry_sell_price.delete(0, tk.END)
        entry_stock.delete(0, tk.END)
        entry_alert.delete(0, tk.END)
        entry_alert.insert(0, "3")
        
        refresh_all()
    except ValueError:
        messagebox.showerror("Error", "कृपया केवल सही नंबर दर्ज करें!")

# टेबल में क्लिक करते ही रेट लोड होना
def on_product_select(event):
    selected = tree.selection()
    if not selected:
        return
    item = tree.item(selected[0])["values"]
    p_id = item[0]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT sell_price FROM products WHERE id = ?", (p_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        entry_custom_rate.delete(0, tk.END)
        entry_custom_rate.insert(0, str(row[0]))
        entry_sell_qty.focus()

# ग्राहक को सामान बेचना
def sell_product():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("चेतावनी", "कृपया टेबल में से वह सामान चुनें जिसे बेचना है!")
        return

    qty_str = entry_sell_qty.get().strip()
    rate_str = entry_custom_rate.get().strip()

    if not qty_str or not qty_str.isdigit() or int(qty_str) <= 0:
        messagebox.showwarning("चेतावनी", "कृपया सही बिक्री मात्रा दर्ज करें!")
        return

    try:
        actual_rate = round(float(rate_str), 2)
    except ValueError:
        messagebox.showwarning("चेतावनी", "कृपया सही बिक्री रेट दर्ज करें!")
        return

    sell_qty = int(qty_str)
    p_id = tree.item(selected[0])["values"][0]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, buy_price, sell_price, stock FROM products WHERE id = ?", (p_id,))
    prod = cursor.fetchone()

    if not prod:
        messagebox.showerror("Error", "सामान नहीं मिला!")
        conn.close()
        return

    p_name, buy_price, default_sell_price, current_stock = prod

    if sell_qty > current_stock:
        messagebox.showerror("स्टॉक कम है", f"दुकान में केवल {current_stock} पीस उपलब्ध हैं!")
        conn.close()
        return

    # 1. घाटा (Loss) अलर्ट
    if actual_rate < buy_price:
        loss_per_pc = buy_price - actual_rate
        total_loss = loss_per_pc * sell_qty
        allow_loss = messagebox.askyesno(
            "⚠️ नुकसान की चेतावनी (Loss Alert)",
            f"यह सामान आपकी खरीद लागत से भी कम में जा रहा है!\n\n"
            f"खरीद मूल्य: ₹{buy_price:.2f}\n"
            f"बिक्री मूल्य: ₹{actual_rate:.2f}\n"
            f"कुल घाटा: ₹{total_loss:.2f}\n\n"
            f"क्या आप वाकई इस नुकसान में बेचना चाहते हैं?"
        )
        if not allow_loss:
            conn.close()
            return

    # 2. डिस्काउंट अलर्ट
    elif actual_rate < default_sell_price:
        allow_discount = messagebox.askyesno(
            "कम रेट कन्फर्मेशन (Discount Alert)",
            f"तय बिक्री रेट: ₹{default_sell_price:.2f}\n"
            f"आप बेच रहे हैं: ₹{actual_rate:.2f}\n\n"
            f"क्या आप कम रेट में सामान देने की अनुमति देते हैं?"
        )
        if not allow_discount:
            conn.close()
            return

    new_stock = current_stock - sell_qty
    total_bill = actual_rate * sell_qty
    total_profit = (actual_rate - buy_price) * sell_qty

    cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, p_id))
    cursor.execute("""
        INSERT INTO sales (product_id, product_name, quantity, sell_price, total_amount, profit)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (p_id, p_name, sell_qty, actual_rate, total_bill, total_profit))

    conn.commit()
    conn.close()

    status_text = f"मुनाफ़ा: ₹{total_profit:.2f}" if total_profit >= 0 else f"घाटा: ₹{abs(total_profit):.2f}"
    messagebox.showinfo("बिक्री सफल", f"बिल: ₹{total_bill:.2f}\n{status_text}\nबचा स्टॉक: {new_stock} पीस")
    
    entry_sell_qty.delete(0, tk.END)
    entry_custom_rate.delete(0, tk.END)
    refresh_all()

# सर्च और रिफ्रेश फंक्शन
def refresh_all(search_query=""):
    for row in tree.get_children():
        tree.delete(row)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # सर्च फ़िल्टर
    if search_query:
        cursor.execute("SELECT id, name, buy_price, sell_price, stock, min_alert FROM products WHERE name LIKE ?", (f"%{search_query}%",))
    else:
        cursor.execute("SELECT id, name, buy_price, sell_price, stock, min_alert FROM products")
    
    rows = cursor.fetchall()

    for row in rows:
        p_id, name, buy_p, sell_p, stock_qty, alert_limit = row

        if stock_qty == 0:
            status = "❌ ख़त्म (Out of Stock)"
            tag = "danger"
        elif stock_qty <= alert_limit:
            status = f"⚠️ कम स्टॉक (<= {alert_limit})"
            tag = "warning"
        else:
            status = "✅ पर्याप्त"
            tag = "normal"

        tree.insert("", tk.END, values=(p_id, name, f"₹{buy_p:.2f}", f"₹{sell_p:.2f}", stock_qty, status), tags=(tag,))

    # कुल समरी
    cursor.execute("SELECT SUM(stock), SUM(buy_price * stock) FROM products")
    stock_data = cursor.fetchone()
    total_items = stock_data[0] if stock_data[0] else 0
    total_stock_value = stock_data[1] if stock_data[1] else 0.0

    cursor.execute("SELECT SUM(total_amount), SUM(profit) FROM sales")
    sales_data = cursor.fetchone()
    total_sales = sales_data[0] if sales_data[0] else 0.0
    total_profit = sales_data[1] if sales_data[1] else 0.0

    conn.close()

    lbl_summary.config(
        text=f"कुल सामान: {total_items} पीस | कुल लागत: ₹{total_stock_value:.2f} | कुल बिक्री: ₹{total_sales:.2f} | कुल मुनाफ़ा: ₹{total_profit:.2f}"
    )

def on_search(event):
    query = entry_search.get().strip()
    refresh_all(query)

def clear_search():
    entry_search.delete(0, tk.END)
    refresh_all()

# ----------------- मुख्य विंडो (UI) -----------------
root = tk.Tk()
root.title("व्यापार बिलिंग एवं स्टॉक मैनेजमेंट सिस्टम")
root.geometry("1020x700")
root.configure(bg="#f1f2f6")

# हेडर
tk.Label(root, text="🏬 दुकान व्यापार डैशबोर्ड एवं स्मार्ट बिलिंग", font=("Arial", 16, "bold"), bg="#2f3542", fg="white", pady=10).pack(fill=tk.X)

# समरी बार
lbl_summary = tk.Label(root, text="", font=("Arial", 10, "bold"), bg="#57606f", fg="white", pady=6)
lbl_summary.pack(fill=tk.X)

# 1. स्टॉक जोड़ना
frame_add = tk.LabelFrame(root, text="1. नया सामान जोड़ें (ख़रीद)", font=("Arial", 10, "bold"), bg="#ffffff", padx=10, pady=8)
frame_add.pack(fill=tk.X, padx=15, pady=6)

tk.Label(frame_add, text="नाम:", bg="#fff").grid(row=0, column=0, padx=3)
entry_name = tk.Entry(frame_add, width=16)
entry_name.grid(row=0, column=1, padx=3)

tk.Label(frame_add, text="खरीद ₹:", bg="#fff").grid(row=0, column=2, padx=3)
entry_buy_price = tk.Entry(frame_add, width=8)
entry_buy_price.grid(row=0, column=3, padx=3)

tk.Label(frame_add, text="तय बिक्री ₹:", bg="#fff").grid(row=0, column=4, padx=3)
entry_sell_price = tk.Entry(frame_add, width=8)
entry_sell_price.grid(row=0, column=5, padx=3)

tk.Label(frame_add, text="मात्रा:", bg="#fff").grid(row=0, column=6, padx=3)
entry_stock = tk.Entry(frame_add, width=6)
entry_stock.grid(row=0, column=7, padx=3)

tk.Label(frame_add, text="अलर्ट सीमा:", bg="#fff").grid(row=0, column=8, padx=3)
entry_alert = tk.Entry(frame_add, width=6)
entry_alert.insert(0, "3")
entry_alert.grid(row=0, column=9, padx=3)

tk.Button(frame_add, text="+ स्टॉक जोड़ें", bg="#2ed573", fg="white", font=("Arial", 9, "bold"), command=add_product).grid(row=0, column=10, padx=8)

# 2. स्मार्ट बिलिंग
frame_sell = tk.LabelFrame(root, text="2. ग्राहक को बिक्री (स्मार्ट रेट और अलर्ट कंट्रोल)", font=("Arial", 10, "bold"), bg="#e4f0ec", padx=10, pady=8)
frame_sell.pack(fill=tk.X, padx=15, pady=4)

tk.Label(frame_sell, text="बेचने की मात्रा (Qty):", bg="#e4f0ec", font=("Arial", 9, "bold")).grid(row=0, column=0, padx=5)
entry_sell_qty = tk.Entry(frame_sell, width=8, font=("Arial", 10, "bold"))
entry_sell_qty.grid(row=0, column=1, padx=5)

tk.Label(frame_sell, text="फाइनल बिक्री रेट (₹):", bg="#e4f0ec", font=("Arial", 9, "bold")).grid(row=0, column=2, padx=5)
entry_custom_rate = tk.Entry(frame_sell, width=10, font=("Arial", 10, "bold"))
entry_custom_rate.grid(row=0, column=3, padx=5)

tk.Button(frame_sell, text="💰 सामान बेचें (Confirm Sale)", bg="#ff4757", fg="white", font=("Arial", 10, "bold"), padx=10, command=sell_product).grid(row=0, column=4, padx=15)

# 3. सर्च बार सेक्शन
frame_search = tk.Frame(root, bg="#f1f2f6", padx=15, pady=4)
frame_search.pack(fill=tk.X)

tk.Label(frame_search, text="🔍 सामान खोजें (Search Item):", font=("Arial", 10, "bold"), bg="#f1f2f6").pack(side=tk.LEFT, padx=(0, 8))
entry_search = tk.Entry(frame_search, font=("Arial", 10), width=28)
entry_search.pack(side=tk.LEFT, padx=5)
entry_search.bind("<KeyRelease>", on_search)

btn_clear = tk.Button(frame_search, text="साफ़ करें (Clear)", font=("Arial", 8, "bold"), bg="#a4b0be", command=clear_search)
btn_clear.pack(side=tk.LEFT, padx=5)

# 4. टेबल
frame_table = tk.Frame(root, padx=15, pady=5)
frame_table.pack(fill=tk.BOTH, expand=True)

columns = ("ID", "सामान का नाम", "खरीद मूल्य", "तय बिक्री मूल्य", "उपलब्ध स्टॉक", "स्टॉक स्टेटस")
tree = ttk.Treeview(frame_table, columns=columns, show="headings", height=11)

tree.column("ID", width=40, anchor=tk.CENTER)
tree.column("सामान का नाम", width=220, anchor=tk.W)
tree.column("खरीद मूल्य", width=100, anchor=tk.CENTER)
tree.column("तय बिक्री मूल्य", width=100, anchor=tk.CENTER)
tree.column("उपलब्ध स्टॉक", width=100, anchor=tk.CENTER)
tree.column("स्टॉक स्टेटस", width=160, anchor=tk.CENTER)

for col in columns:
    tree.heading(col, text=col)

tree.tag_configure("warning", background="#ffeaa7", foreground="#d63031")
tree.tag_configure("danger", background="#ff7675", foreground="white")
tree.tag_configure("normal", background="#ffffff")

tree.bind("<<TreeviewSelect>>", on_product_select)

tree.pack(fill=tk.BOTH, expand=True)

refresh_all()
root.mainloop()