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

    
def update_device_schema():
    """Update the device schema to include IP address and SSH credentials"""
    conn = sqlite3.connect('wol.db')
    c = conn.cursor()
    
    # Check if the columns already exist
    cursor = c.execute('PRAGMA table_info(devices)')
    columns = [column[1] for column in cursor.fetchall()]
    
    # Add IP address column if it doesn't exist
    if 'ip_address' not in columns:
        c.execute('ALTER TABLE devices ADD COLUMN ip_address TEXT')
    
    # Add SSH username column if it doesn't exist
    if 'ssh_username' not in columns:
        c.execute('ALTER TABLE devices ADD COLUMN ssh_username TEXT')
    
    # Add SSH port column if it doesn't exist
    if 'ssh_port' not in columns:
        c.execute('ALTER TABLE devices ADD COLUMN ssh_port INTEGER DEFAULT 22')
    
    conn.commit()
    conn.close()

def add_device(name, mac_address, ip_address=None, ssh_username=None, ssh_port=22):
    """Add a new device with optional SSH info"""
    conn = sqlite3.connect('wol.db')
    c = conn.cursor()
    
    try:
        c.execute(
            'INSERT INTO devices (name, mac_address, ip_address, ssh_username, ssh_port) VALUES (?, ?, ?, ?, ?)',
            (name, mac_address, ip_address, ssh_username, ssh_port)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def update_device(mac_address, name=None, ip_address=None, ssh_username=None, ssh_port=None):
    """Update device information"""
    conn = sqlite3.connect('wol.db')
    c = conn.cursor()
    
    # Build update query based on provided parameters
    update_fields = []
    params = []
    
    if name is not None:
        update_fields.append('name = ?')
        params.append(name)
    
    if ip_address is not None:
        update_fields.append('ip_address = ?')
        params.append(ip_address)
    
    if ssh_username is not None:
        update_fields.append('ssh_username = ?')
        params.append(ssh_username)
    
    if ssh_port is not None:
        update_fields.append('ssh_port = ?')
        params.append(ssh_port)
    
    if not update_fields:
        conn.close()
        return False
    
    params.append(mac_address)
    
    # Execute update
    c.execute(
        f'UPDATE devices SET {", ".join(update_fields)} WHERE mac_address = ?',
        params
    )
    
    conn.commit()
    conn.close()
    return True

def get_device(mac_address):
    """Get a single device by MAC address"""
    conn = sqlite3.connect('wol.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT * FROM devices WHERE mac_address = ?', (mac_address,))
    device = c.fetchone()
    
    conn.close()
    
    if device:
        return dict(device)
    return None