import os
import json
import requests
from flask import Flask, request, jsonify, send_file

# --- CONFIGURATION (CRITICAL VALUES) ---
# The URL to which the user is redirected after a successful POST attempt.
TASK_PAGE_URL = "https://www.bajajfinserv.in/webform/emicard/login"

# Your unique affiliate ID found in the URL /camp/rihcy8kq
AFFILIATE_KEY = "rihcy8kq"

# The complex security token found in the Livewire snapshot. This MAY need updating if RechargeFox changes the page frequently.
LIVEWIRE_CHECKSUM = "bbebb48657033c7d9e0f6f65f5734ac69c15cd16ffa3c1d97abb6b7d1fe0b85b"

# The target URL for the hidden POST submission (rechargefox campaign link)
RECHARGEFOX_URL = f"https://rechargefox.com/camp/{AFFILIATE_KEY}"
# ----------------------------------------

app = Flask(__name__, static_folder='.', static_url_path='')
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

@app.route('/')
def serve_index():
    """Serves the index.html landing page."""
    return send_file('index.html')

@app.route('/submit-proxy', methods=['POST'])
def submit_proxy():
    """Receives data from the frontend and proxies it to RechargeFox."""
    try:
        data = request.get_json()
        mobile = data.get('mobile')
        upi = data.get('upi')

        if not mobile or not upi:
            return jsonify({"status": "error", "message": "Missing mobile or UPI data."}), 400

        # Data payload for RechargeFox (keys found via inspection)
        payload = {
            # Mobile Number field
            'extra_input_1': mobile,
            # UPI ID field
            'upi': upi,
            
            # Affiliate Tracking Fields (CRITICAL)
            'refer': AFFILIATE_KEY,

            # Livewire Security Tokens (Mandatory for Livewire forms)
            '_token': '', # Livewire typically handles this, but we include it.
            'checksum': LIVEWIRE_CHECKSUM,
            'memo[id]': 'HqMKGTy2ehZGxgd3nJ84', # Component ID found in the snapshot
            'memo[name]': 'campaign.show',
            'memo[path]': f'camp/{AFFILIATE_KEY}',
            'memo[method]': 'POST',
            'memo[locale]': 'en',
            
            # The actual form data structure
            'data': {
                'extra_input_1': mobile,
                'upi': upi,
                'refer': AFFILIATE_KEY
            },
        }

        # Set headers for the server-to-server request
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Python/Flask Proxy Server' # Identify our server
        }
        
        # --- SERVER-TO-SERVER POST TO RECHARGEFOX ---
        # The key to reliability: POSTing from your server to the target server.
        proxy_response = requests.post(RECHARGEFOX_URL, json=payload, headers=headers, timeout=10)

        # Check if RechargeFox accepted the data (usually 200 or 202)
        if proxy_response.status_code in [200, 202]:
            print(f"Proxy POST successful. Status: {proxy_response.status_code}")
            # Success response to the frontend, which will trigger the client-side redirect
            return jsonify({
                "status": "success",
                "message": "Data proxied successfully.",
                "redirect_url": TASK_PAGE_URL
            }), 200
        else:
            print(f"Proxy POST failed. Status: {proxy_response.status_code}, Response: {proxy_response.text}")
            return jsonify({
                "status": "error",
                "message": f"RechargeFox server rejected the data (Status: {proxy_response.status_code})."
            }), 502

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"status": "error", "message": "Internal server error. Check logs."}), 500

# The rest of the setup is for Gunicorn deployment
if __name__ == '__main__':
    # This block only runs when you run 'python proxy_server.py' locally
    print(f"Starting development server. Access at http://127.0.0.1:5000/")
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000), debug=True)