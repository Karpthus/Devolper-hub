import scapy.all as scapy
import socket
import ipaddress
import threading
import time
import os

def ping(host):
    """Check if a machine is online using ping."""
    response = os.system(f"ping -c 1 {host} > /dev/null 2>&1")
    return response == 0

def get_mac(ip):
    """Get the MAC address of a device using the arp command."""
    try:
        # Run the arp command to get the MAC address
        result = os.popen(f"arp -n {ip}").read()
        
        # Parse the output to extract the MAC address
        # The output format varies by OS, but typically looks like:
        # Address         HWtype  HWaddress           Flags Mask    Iface
        # 192.168.1.1     ether   aa:bb:cc:dd:ee:ff   C              eth0
        
        lines = result.strip().split('\n')
        if len(lines) >= 2:  # Skip header line
            parts = lines[1].split()
            if len(parts) >= 3:
                mac = parts[2]
                if ":" in mac:  # Verify it looks like a MAC address
                    return mac
        return None
    except Exception as e:
        print(f"Error getting MAC for {ip}: {e}")
        return None
 
def get_hostname(ip):
    """Try to get the hostname of a device."""
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname
    except (socket.herror, socket.timeout):
        return None    

def scan_network():
    """Scan the local network for devices."""
    # Get the IP address of the server
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    
    # Get the network address
    network = '.'.join(ip.split('.')[:3]) + '.0/24'
    
    results = []
    active_threads = []
    
    def scan_ip(ip):
        if ping(ip):
            mac = get_mac(ip)
            hostname = get_hostname(ip)
            if mac:  # Only add devices with a valid MAC
                results.append({
                    'ip': ip,
                    'mac': mac,
                    'hostname': hostname or 'Unknown'
                })
    
    # Create threads for scanning
    for ip in ipaddress.IPv4Network(network):
        ip_str = str(ip)
        thread = threading.Thread(target=scan_ip, args=(ip_str,))
        thread.start()
        active_threads.append(thread)
        
        # Limit concurrent threads to avoid overwhelming the system
        if len(active_threads) >= 20:
            for t in active_threads:
                t.join(timeout=0.1)
            active_threads = [t for t in active_threads if t.is_alive()]
    
    # Wait for all threads to complete
    for thread in active_threads:
        thread.join()
        
    return results