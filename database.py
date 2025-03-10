import sqlite3

DB_FILE = "devices.db"

def init_db():
    """Initialize the database and create the devices table if not exists."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mac_address TEXT NOT NULL UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

def add_device(name, mac_address):
    """Add a new device to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO devices (name, mac_address) VALUES (?, ?)", (name, mac_address))
        conn.commit()
    except sqlite3.IntegrityError:
        return False  # MAC Address already exists
    finally:
        conn.close()
    return True

def get_devices():
    """Fetch all devices from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, mac_address FROM devices")
    devices = cursor.fetchall()
    conn.close()
    return devices

def remove_device(mac_address):
    """Remove a device from the database by MAC address."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM devices WHERE mac_address = ?", (mac_address,))
    conn.commit()
    conn.close()
