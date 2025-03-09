from flask import Flask, render_template, request, jsonify
import wakeonlan
import os

app = Flask(__name__)

# Predefined devices (MAC Address, Name)
devices = {
    "PC1": "00:11:22:33:44:55",
    "PC2": "66:77:88:99:AA:BB",
}

def ping(host):
    """Check if a machine is online using ping."""
    response = os.system(f"ping -c 1 {host} > /dev/null 2>&1")
    return response == 0

@app.route("/")
def home():
    return render_template("index.html", devices=devices)

@app.route("/wake", methods=["POST"])
def wake():
    mac_address = request.form.get("mac")
    if mac_address:
        wakeonlan.send_magic_packet(mac_address)
        return jsonify({"message": f"Magic packet sent to {mac_address}!"})
    return jsonify({"error": "No MAC address provided"}), 400

@app.route("/ping", methods=["POST"])
def check_status():
    host = request.form.get("host")
    if host:
        online = ping(host)
        return jsonify({"status": "Online" if online else "Offline"})
    return jsonify({"error": "No host provided"}), 400

if __name__ == "__main__":
    app.run(debug=True)
