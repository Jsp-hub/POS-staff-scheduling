import sqlite3
import pandas as pd

# Load your actual CSV
df = pd.read_csv("Staff_Availability_Data.csv")

# Connect to (or create) SQLite database
conn = sqlite3.connect("staff.db")
cursor = conn.cursor()

# Create table (auto-generates ID, so we skip the 'id' column from CSV)
cursor.execute("""
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    role TEXT NOT NULL,
    available_start TEXT NOT NULL,
    available_end TEXT NOT NULL
)
""")

# Insert data into staff table
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO staff (name, phone, role, available_start, available_end)
        VALUES (?, ?, ?, ?, ?)
    """, (
        row["name"],
        str(row["phone"]),
        row["role"],
        row["available_start"],
        row["available_end"]
    ))

# Save and close
conn.commit()
conn.close()

print("✅ staff.db created successfully from Staff_Availability_Data.csv")
