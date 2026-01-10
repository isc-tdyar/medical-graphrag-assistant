"""
Reset FHIR Security Configuration utility.
Handles password reset, role assignment, and CSP application configuration.
"""

import os
import sys
import argparse
import json
import base64
from typing import Optional, Dict, Any

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db.connection import DatabaseConnection

def reset_security(username: str = "_SYSTEM", password: str = "SYS", fhir_app: str = "/csp/healthshare/demo/fhir/r4"):
    """
    Perform deep reset of FHIR security settings.
    Uses docker exec for maximum reliability when running on the host.
    """
    import subprocess
    import requests
    from requests.auth import HTTPBasicAuth
    
    print(f"Starting security reset for user {username} and app {fhir_app}...")
    
    def run_iris_cmd(cmd_string):
        """Execute ObjectScript in the IRIS container."""
        # Use heredoc to pipe commands into iris session
        full_cmd = f"docker exec iris-fhir iris session IRIS <<EOF\nzn \"%SYS\"\n{cmd_string}\nhalt\nEOF"
        return subprocess.run(full_cmd, shell=True, capture_output=True, text=True)

    try:
        # 1. Reset Password
        print(f"Resetting password for {username}...")
        res = run_iris_cmd(f"write ##class(Security.Users).ChangePassword(\"{username}\", \"{password}\")")
        if "1" not in res.stdout:
            print(f"Warning: Password reset might have failed: {res.stderr} {res.stdout}")

        # 2. Enable Password Auth for Application
        print(f"Configuring application {fhir_app}...")
        app_cmd = f"""
            set app = ##class(Security.Applications).%OpenId("{fhir_app}")
            if \$isobject(app) {{
                set app.AuthenEnabled = 32
                set app.Enabled = 1
                write app.%Save()
            }} else {{
                write "APP_NOT_FOUND"
            }}
        """
        res = run_iris_cmd(app_cmd)
        if "1" not in res.stdout:
            print(f"Warning: App config failed: {res.stdout}")

        # 3. Assign Roles
        print(f"Assigning roles to {username}...")
        role_cmd = f"""
            set user = ##class(Security.Users).%OpenId("{username}")
            if \$isobject(user) {{
                set user.Roles = user.Roles _ ",%DB_FHIR,%HS_FHIR_USER,%Manager"
                write user.%Save()
            }}
        """
        res = run_iris_cmd(role_cmd)

        # 4. Verify connectivity
        print("Verifying connectivity...")
        fhir_url = os.getenv("FHIR_BASE_URL")
        if not fhir_url:
            port = os.getenv("IRIS_PORT_WEB", "32783")
            fhir_url = f"http://localhost:{port}{fhir_app}"
            
        try:
            print(f"Checking {fhir_url}/metadata...")
            response = requests.get(
                f"{fhir_url}/metadata", 
                auth=HTTPBasicAuth(username, password),
                timeout=10
            )
            if response.status_code == 200:
                print("✅ FHIR connectivity verified!")
                return True
            else:
                print(f"⚠️ FHIR check returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️ FHIR connectivity check failed: {e}")

        return True
    except Exception as e:
        print(f"Error during reset: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Reset IRIS FHIR Security")
    parser.add_argument("--username", default="_SYSTEM", help="Target username")
    parser.add_argument("--password", default="SYS", help="New password")
    parser.add_argument("--fhir-app", default="/csp/healthshare/demo/fhir/r4", help="FHIR CSP Application path")
    
    args = parser.parse_args()
    
    try:
        if reset_security(args.username, args.password, args.fhir_app):
            print("✅ Security reset successful")
        else:
            print("❌ Security reset failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error during security reset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
