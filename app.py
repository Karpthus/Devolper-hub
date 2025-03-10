from flask import Flask, render_template, request, jsonify
import wakeonlan
import os
from database import init_db, add_device, get_devices, remove_device
from WoL_function import ping, scan_network

app = Flask(__name__)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080,debug=True)
