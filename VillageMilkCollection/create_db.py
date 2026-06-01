import sqlite3

conn = sqlite3.connect('milk.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
phone TEXT UNIQUE,
password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS customers(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
name TEXT,
mobile TEXT,
address TEXT,
rate REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS milk_entries(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
customer_id INTEGER,
entry_date TEXT,
session TEXT,
litre REAL
)
""")

conn.commit()
conn.close()

print("Database Created Successfully")