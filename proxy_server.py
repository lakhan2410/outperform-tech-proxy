# Affiliate Proxy Server for RechargeFox Lead Submission
# This Python Flask application securely proxies user data from your landing page
# to the RechargeFox campaign endpoint (server-to-server) to ensure reliable tracking,
# then redirects the user to the task page.

import os
import requests
from flask import Flask, request, jsonify, send_file, redirect, url_for

# --- CRITICAL CONFIGURATION VALUES (MUST BE CORRECT) ---

# 1. The final destination URL the user is redirected to after successful submission.
TASK_PAGE_URL = "https://customer.credilio.in/v2/sbm-credilio-rupay-credit-card-on-upi?advisor_code=CRD0183543&utm_org_code=ORG03477&utm_source=Affiliate&utm_campaign=RechargeFox_5wij8mfkla220saf_331464__D-21556697-1762673335-34G70G153G255-AFLWE8130_"

# 2. Your unique affiliate ID (the key in the RechargeFox URL path).
AFFILIATE_KEY = "ro6kn0i0"

# 3. The complex Livewire security token found in the page snapshot. 
#    If the server keeps rejecting the POST, this is the most likely value to have changed and must be updated.
LIVEWIRE_CHECKSUM = "e6d7681b9182ea528cabf2533741901a76d0923968d80ed54f4caa215dee18e5"

# The target URL for the hidden POST submission (RechargeFox endpoint)
RECHARGEFOX_URL = f"https://rechargefox.com/camp/{AFFILIATE_KEY}"

# --- FLASK SETUP ---
# Configure Flask to serve the index.html from the root directory
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

@app.route('/')
def serve_index():
    """Serves the index.html landing page."""
    # This serves the index.html file located in the same directory.
    return send_file('index.html')

@app.route('/submit-proxy', methods=['POST'])
def submit_proxy():
    """Receives data from the frontend and proxies it to RechargeFox."""
    try:
        # Get JSON data sent from the frontend (index.html fetch request)
        data = request.get_json()
        mobile = data.get('mobile')
        upi = data.get('upi')

        if not mobile or not upi:
            print("Error: Missing mobile or UPI data in request.")
            return jsonify({"status": "error", "message": "Missing required data."}), 400

        # --- CORRECT LIVEWIRE PAYLOAD STRUCTURE ---
        # Livewire requires the security tokens and data fields to be submitted 
        # as a flat JSON object in the request body.
        payload = {
            # Mobile Number field (extra_input_1)
            'extra_input_1': mobile,
            # UPI ID field
            'upi': upi,
            # Affiliate tracking field
            'refer': AFFILIATE_KEY,
            
            # Livewire Security Tokens (Mandatory for validation)
            'memo': {
                'id': 'HqMKGTy2ehZGxgd3nJ84',       # Component ID (static from inspection)
                'name': 'campaign.show',            # Component name
                'path': f'camp/{AFFILIATE_KEY}',    # Component path
                'method': 'POST',                   # Request method
                'locale': 'en'
            },
            'checksum': LIVEWIRE_CHECKSUM,         # The complex security token
            
            # Additional Livewire fields (to ensure POST consistency)
            'components': [],
            'assets': []
        }

        # Set headers for the server-to-server request
        headers = {
            # Must be JSON content type for Livewire endpoint
            'Content-Type': 'application/json',
            'User-Agent': 'Python/Flask Affiliate Proxy Server'
        }
        
        # --- SERVER-TO-SERVER POST TO RECHARGEFOX ---
        proxy_response = requests.post(
            RECHARGEFOX_URL, 
            json=payload, 
            headers=headers, 
            timeout=10 # Set a timeout for safety
        )

        # Check the status code from the RechargeFox server
        if proxy_response.status_code in [200, 202]:
            print(f"Proxy POST successful. Status: {proxy_response.status_code}")
            # Success response to the frontend, which will trigger the client-side redirect
            return jsonify({
                "status": "success",
                "message": "Data proxied successfully.",
                "redirect_url": TASK_PAGE_URL
            }), 200
        else:
            # RechargeFox server rejected the data
            print(f"Proxy POST failed. Status: {proxy_response.status_code}, Response: {proxy_response.text}")
            return jsonify({
                "status": "error",
                "message": f"Server rejected data (Status: {proxy_response.status_code}). Please check proxy_server.py logs."
            }), 502

    except Exception as e:
        # Catch any unexpected errors (e.g., network failure, timeout)
        print(f"*** CRITICAL UNEXPECTED ERROR: {e} ***")
        return jsonify({"status": "error", "message": "Internal server error. Check logs."}), 500

# The rest of the setup is for Gunicorn deployment
if __name__ == '__main__':
    # This block only runs when you run 'python proxy_server.py' locally
    print(f"Starting development server. Access at http://127.0.0.1:5000/")
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000), debug=True)
