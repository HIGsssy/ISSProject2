#!/usr/bin/env python
"""
Standalone web-based setup wizard for ISS Portal
Runs before the main application to collect configuration
"""
import os
import secrets
from pathlib import Path
from cryptography.fernet import Fernet
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>ISS Portal - Setup Wizard</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        h1 { color: #2c3e50; }
        .form-group { margin-bottom: 20px; }
        label { display: block; font-weight: bold; margin-bottom: 5px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .help-text { font-size: 12px; color: #666; margin-top: 3px; }
        button { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #2980b9; }
        .warning { background: #fff3cd; border: 1px solid #ffc107; padding: 10px; border-radius: 4px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>🚀 ISS Portal Setup</h1>
    <p>Welcome! Please provide the following configuration to complete setup.</p>
    
    <div class="warning">
        <strong>⚠️ Important:</strong> After setup, default admin login is <strong>admin / admin123</strong><br>
        Change this password immediately after first login!
    </div>
    
    <form method="POST">
        <div class="form-group">
            <label>Allowed Hosts (optional)</label>
            <input type="text" name="allowed_hosts" placeholder="localhost,your-domain.com">
            <div class="help-text">Comma-separated list of domains. Leave blank to allow all (*)</div>
        </div>
        
        <div class="form-group">
            <label>Time Zone (optional)</label>
            <input type="text" name="timezone" placeholder="America/Toronto">
            <div class="help-text">Leave blank for America/Toronto</div>
        </div>
        
        <button type="submit">Complete Setup</button>
    </form>
    
    <p style="margin-top: 30px; font-size: 12px; color: #666;">
        Security keys will be automatically generated.<br>
        Database credentials are pre-configured.
    </p>
</body>
</html>
"""

SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Setup Complete</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
        .success { background: #d4edda; border: 1px solid #c3e6cb; padding: 20px; border-radius: 4px; margin: 20px 0; }
        h1 { color: #28a745; }
        .info { text-align: left; background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>✅ Setup Complete!</h1>
    
    <div class="success">
        <p><strong>ISS Portal is now configured and starting...</strong></p>
        <p>This will take about 30-60 seconds for database initialization.</p>
    </div>
    
    <div class="info">
        <h3>Next Steps:</h3>
        <ol>
            <li>Wait for the application to start (watch container logs)</li>
            <li>Visit: <a href="/">http://your-server/</a></li>
            <li>Login with: <strong>admin / admin123</strong></li>
            <li><strong>Change the admin password immediately!</strong></li>
        </ol>
    </div>
    
    <p style="font-size: 12px; color: #666; margin-top: 30px;">
        This page will refresh automatically in 10 seconds...<br>
        <span id="countdown">10</span>
    </p>
    
    <script>
        let count = 10;
        setInterval(() => {
            count--;
            document.getElementById('countdown').textContent = count;
            if (count <= 0) window.location.href = '/';
        }, 1000);
    </script>
</body>
</html>
"""


class SetupHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML_FORM.encode())
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode()
        params = parse_qs(post_data)
        
        # Extract values
        allowed_hosts = params.get('allowed_hosts', ['*'])[0].strip() or '*'
        timezone = params.get('timezone', ['America/Toronto'])[0].strip() or 'America/Toronto'
        
        # Generate keys
        secret_key = secrets.token_urlsafe(50)
        fernet_key = Fernet.generate_key().decode()
        
        # Fixed database credentials (must match docker-compose.hub.yml)
        db_name = 'iss_portal_db'
        db_user = 'iss_user'
        db_password = 'kN8mP4xR9vL2wQ7jT5nC6hB3fY1sD0aE'
        
        # Create .env file
        env_content = f"""SECRET_KEY={secret_key}
DEBUG=False
ALLOWED_HOSTS={allowed_hosts}
POSTGRES_DB={db_name}
POSTGRES_USER={db_user}
POSTGRES_PASSWORD={db_password}
DATABASE_URL=postgresql://{db_user}:{db_password}@db:5432/{db_name}
FIELD_ENCRYPTION_KEY={fernet_key}
TIME_ZONE={timezone}
"""
        
        env_path = Path('/app/.env')
        env_path.write_text(env_content)
        env_path.chmod(0o600)
        
        print("✓ Configuration saved to /app/.env")
        print("✓ Setup complete!")
        
        # Return success page
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(SUCCESS_HTML.encode())
        
        # Signal to stop server
        self.server.setup_complete = True
    
    def log_message(self, format, *args):
        # Suppress access logs
        pass


def run_setup_server(port=8000):
    server = HTTPServer(('0.0.0.0', port), SetupHandler)
    server.setup_complete = False
    
    print("=" * 80)
    print("ISS Portal - Web Setup Wizard")
    print("=" * 80)
    print(f"\n👉 Open your browser and visit: http://your-server-ip:{port}\n")
    print("Waiting for configuration...")
    
    # Handle requests until setup is complete
    while not server.setup_complete:
        server.handle_request()
    
    print("\nSetup wizard completed. Starting main application...")


if __name__ == '__main__':
    run_setup_server()
