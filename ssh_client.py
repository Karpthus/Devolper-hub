# ssh_client.py
import paramiko
import threading
import time
import logging
import io
from flask_socketio import SocketIO, emit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ssh_client")

class SSHClient:
    def __init__(self, socketio):
        self.socketio = socketio
        self.sessions = {}  # Store active sessions
        
    def create_session(self, session_id, hostname, port, username, password=None, key_file=None):
        """Create a new SSH session"""
        try:
            # Initialize SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect using either password or key file
            if key_file:
                client.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    key_filename=key_file,
                    timeout=10
                )
            else:
                client.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    password=password,
                    timeout=10
                )
            
            # Create shell channel
            channel = client.invoke_shell()
            channel.settimeout(0.0)  # Non-blocking
            
            # Store session
            self.sessions[session_id] = {
                'client': client,
                'channel': channel,
                'hostname': hostname,
                'username': username,
                'buffer': io.StringIO(),
                'last_activity': time.time()
            }
            
            # Start session watcher thread
            threading.Thread(
                target=self._watch_session,
                args=(session_id,),
                daemon=True
            ).start()
            
            return True, "SSH connection established"
            
        except paramiko.AuthenticationException:
            return False, "Authentication failed. Check username and password/key."
        except paramiko.SSHException as e:
            return False, f"SSH error: {str(e)}"
        except Exception as e:
            logger.error(f"Error creating SSH session: {str(e)}")
            return False, f"Connection error: {str(e)}"
            
    def send_command(self, session_id, command):
        """Send a command to an active SSH session"""
        if session_id not in self.sessions:
            return False, "Session not found"
            
        try:
            session = self.sessions[session_id]
            channel = session['channel']
            
            # Send command with newline
            if not command.endswith('\n'):
                command += '\n'
                
            channel.send(command)
            session['last_activity'] = time.time()
            
            # Give a short time for command to execute
            time.sleep(0.1)
            
            # Return success status
            return True, "Command sent"
            
        except Exception as e:
            logger.error(f"Error sending command: {str(e)}")
            return False, f"Error: {str(e)}"
            
    def close_session(self, session_id):
        """Close and clean up an SSH session"""
        if session_id not in self.sessions:
            return False, "Session not found"
            
        try:
            session = self.sessions[session_id]
            if session['channel']:
                session['channel'].close()
            if session['client']:
                session['client'].close()
                
            # Remove from active sessions
            del self.sessions[session_id]
            return True, "Session closed"
            
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")
            return False, f"Error: {str(e)}"
            
    def get_active_sessions(self):
        """Return a list of active session IDs with metadata"""
        active_sessions = {}
        for session_id, session in self.sessions.items():
            active_sessions[session_id] = {
                'hostname': session['hostname'],
                'username': session['username'],
                'last_activity': session['last_activity']
            }
        return active_sessions
            
    def _watch_session(self, session_id):
        """Watch for output on the SSH channel and emit via SocketIO"""
        if session_id not in self.sessions:
            return
            
        session = self.sessions[session_id]
        channel = session['channel']
        
        try:
            while session_id in self.sessions and not channel.closed:
                # Check if data is available to read
                if channel.recv_ready():
                    data = channel.recv(4096).decode('utf-8', errors='replace')
                    if data:
                        # Emit data via SocketIO
                        self.socketio.emit('ssh_output', {
                            'session_id': session_id,
                            'data': data
                        }, namespace='/ssh')
                        
                        # Also store in buffer
                        session['buffer'].write(data)
                        session['last_activity'] = time.time()
                
                # Check for inactivity timeout (30 min)
                if time.time() - session['last_activity'] > 1800:  # 30 minutes
                    self.socketio.emit('ssh_timeout', {
                        'session_id': session_id,
                        'message': 'Session timed out due to inactivity'
                    }, namespace='/ssh')
                    self.close_session(session_id)
                    break
                    
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in session watcher: {str(e)}")
            self.socketio.emit('ssh_error', {
                'session_id': session_id,
                'error': str(e)
            }, namespace='/ssh')
            
            # Try to close the session
            self.close_session(session_id)