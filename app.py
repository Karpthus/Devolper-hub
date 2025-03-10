import uuid
from flask import Flask, render_template, request, jsonify
import wakeonlan
import os
from database import get_device, init_db, add_device, get_devices, remove_device, update_device
from WoL_function import ping, scan_network
from flask_socketio import SocketIO
from ssh_client import SSHClient

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
socketio = SocketIO(app)

# Initialize SSH client with SocketIO
ssh_manager = SSHClient(socketio)



# Initialize the database
init_db()

# Updated routes for tile-based navigation
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/devices")
def devices_page():
    devices = get_devices()
    return render_template("devices.html", devices=devices)

@app.route("/wake", methods=["POST"])
def wake():
    mac_address = request.form.get("mac")
    if mac_address:
        wakeonlan.send_magic_packet(mac_address)
        return jsonify({"message": f"Magic packet sent to {mac_address}!"})
    return jsonify({"error": "No MAC address provided"}), 400


@app.route("/wake-dashboard")
def wake_dashboard():
    devices = get_devices()
    return render_template("wake-dashboard.html", devices=devices)


@app.route("/ping", methods=["POST"])
def check_status():
    host = request.form.get("host")
    if host:
        online = ping(host)
        return jsonify({"status": "Online" if online else "Offline"})
    return jsonify({"error": "No host provided"}), 400

@app.route("/add_device", methods=["POST"])
def add_new_device():
    data = request.get_json()
    name = data.get("name")
    mac_address = data.get("mac_address")
    
    if not name or not mac_address:
        return jsonify({"error": "Name and MAC address are required"}), 400
    
    if add_device(name, mac_address):
        return jsonify({"message": f"Device '{name}' added successfully!"})
    else:
        return jsonify({"error": "MAC address already exists"}), 400

@app.route("/remove_device", methods=["POST"])
def delete_device():
    data = request.get_json()
    mac_address = data.get("mac_address")

    if not mac_address:
        return jsonify({"error": "MAC address required"}), 400
    
    remove_device(mac_address)
    return jsonify({"message": "Device removed successfully!"})

@app.route("/scan", methods=["GET"])
def scan_page():
    return render_template("scan.html")

@app.route("/api/scan", methods=["POST"])
def scan_api():
    try:
        # This may take some time
        devices = scan_network()
        return jsonify({"devices": devices})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/ssh")
def ssh_page():
    """Render the SSH client page"""
    devices = get_devices()
    return render_template("ssh_client.html", devices=devices)

@app.route("/api/ssh/connect", methods=["POST"])
def ssh_connect():
    """Connect to a device via SSH"""
    data = request.json
    host = data.get('host')
    port = int(data.get('port', 22))
    username = data.get('username')
    password = data.get('password')
    key_file = data.get('key_file')
    
    if not host or not username:
        return jsonify({"error": "Host and username are required"}), 400
        
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # Try to establish connection
    success, message = ssh_manager.create_session(
        session_id=session_id,
        hostname=host,
        port=port,
        username=username,
        password=password,
        key_file=key_file
    )
    
    if success:
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": message
        })
    else:
        return jsonify({
            "success": False,
            "message": message
        }), 500

@app.route("/api/ssh/command", methods=["POST"])
def ssh_command():
    """Send a command to an SSH session"""
    data = request.json
    session_id = data.get('session_id')
    command = data.get('command')
    
    if not session_id or not command:
        return jsonify({"error": "Session ID and command are required"}), 400
        
    success, message = ssh_manager.send_command(session_id, command)
    
    return jsonify({
        "success": success,
        "message": message
    })

@app.route("/api/ssh/disconnect", methods=["POST"])
def ssh_disconnect():
    """Close an SSH session"""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
        
    success, message = ssh_manager.close_session(session_id)
    
    return jsonify({
        "success": success,
        "message": message
    })

@app.route("/api/ssh/sessions", methods=["GET"])
def ssh_sessions():
    """Get all active SSH sessions"""
    active_sessions = ssh_manager.get_active_sessions()
    
    return jsonify({
        "sessions": active_sessions
    })

# Handle Socket.IO events
@socketio.on('connect', namespace='/ssh')
def handle_ssh_connect():
    print("Client connected to SSH namespace")

@socketio.on('disconnect', namespace='/ssh')
def handle_ssh_disconnect():
    print("Client disconnected from SSH namespace")

@app.route("/api/device/<mac_address>")
def get_device_api(mac_address):
    """API endpoint to get device details"""
    device = get_device(mac_address)
    if device:
        return jsonify(device)
    return jsonify({"error": "Device not found"}), 404

@app.route("/api/device/<mac_address>", methods=["PUT"])
def update_device_api(mac_address):
    """API endpoint to update device details"""
    data = request.json
    
    # Update device with provided data
    success = update_device(
        mac_address,
        name=data.get('name'),
        ip_address=data.get('ip_address'),
        ssh_username=data.get('ssh_username'),
        ssh_port=data.get('ssh_port')
    )
    
    if success:
        return jsonify({"message": "Device updated successfully"})
    return jsonify({"error": "Failed to update device"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080,debug=True)
