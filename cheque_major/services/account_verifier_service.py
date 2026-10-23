#!/usr/bin/env python3
"""Account Number Verification Service - Manual verification with UI."""

import json
import csv
import os
import re
from pathlib import Path
from flask import Flask, jsonify, request, send_file, render_template_string
import cv2
import base64

app = Flask(__name__)

# HTML interface
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Account Number Verifier</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .content { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; padding: 30px; min-height: 600px; }
        @media (max-width: 768px) { .content { grid-template-columns: 1fr; } }
        .cheque-display { display: flex; flex-direction: column; gap: 15px; }
        .cheque-image { width: 100%; border: 2px solid #ddd; border-radius: 8px; background: #f9f9f9; display: flex; align-items: center; justify-content: center; min-height: 400px; font-size: 18px; color: #999; }
        .cheque-image img { max-width: 100%; max-height: 100%; border-radius: 6px; }
        .cheque-info { background: #f0f0f0; padding: 15px; border-radius: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .info-item { display: flex; flex-direction: column; }
        .info-label { font-size: 12px; color: #666; font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }
        .info-value { font-size: 16px; color: #333; font-weight: 500; }
        .form-section { display: flex; flex-direction: column; gap: 20px; }
        .form-group { display: flex; flex-direction: column; gap: 8px; }
        .form-group label { font-size: 14px; font-weight: 600; color: #333; }
        .form-group input { padding: 12px 15px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; transition: all 0.3s; }
        .form-group input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .button-group { display: flex; gap: 10px; }
        button { flex: 1; padding: 12px 20px; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
        .btn-save { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-save:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }
        .btn-skip { background: #f0f0f0; color: #333; border: 2px solid #ddd; }
        .progress { width: 100%; height: 6px; background: #e0e0e0; border-radius: 3px; overflow: hidden; margin-top: 10px; }
        .progress-bar { height: 100%; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); width: 0%; transition: width 0.3s; }
        .status-box { padding: 15px; border-radius: 8px; font-size: 14px; margin-top: 10px; }
        .status-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .statistics { background: #f9f9f9; padding: 20px; border-radius: 8px; margin-top: 20px; }
        .stat-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
        .stat-row:last-child { border-bottom: none; }
        .export-btn { width: 100%; background: #28a745; color: white; margin-top: 20px; }
        .export-btn:hover:not(:disabled) { background: #218838; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(40, 167, 69, 0.4); }
        .export-btn:disabled { opacity: 0.5; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Account Number Verifier</h1>
            <p>Manually verify and enter account numbers for signature files</p>
        </div>

        <div class="content">
            <div class="cheque-display">
                <h3>Cheque Image</h3>
                <div class="cheque-image" id="chequeImage">Loading cheque...</div>
                <div class="cheque-info">
                    <div class="info-item">
                        <div class="info-label">Cheque Number</div>
                        <div class="info-value" id="chequeNum">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Bank</div>
                        <div class="info-value" id="bankName">-</div>
                    </div>
                </div>
                <div class="statistics">
                    <h4>Progress</h4>
                    <div class="progress"><div class="progress-bar" id="progressBar"></div></div>
                    <p style="margin-top: 10px; font-size: 12px; color: #666;" id="progressText">0 / 0</p>
                    <div style="margin-top: 15px;">
                        <div class="stat-row"><span>Verified:</span><span id="statVerified">0</span></div>
                        <div class="stat-row"><span>Remaining:</span><span id="statRemaining">0</span></div>
                        <div class="stat-row"><span>Success Rate:</span><span id="statRate">0%</span></div>
                    </div>
                    <button class="export-btn" id="exportBtn" disabled>Export & Rename Files</button>
                </div>
            </div>

            <div class="form-section">
                <h3>Verify Account Number</h3>
                <div class="form-group">
                    <label for="accountInput">Account Number (12-18 digits)</label>
                    <input type="text" id="accountInput" placeholder="Enter account number..." inputmode="numeric">
                </div>
                <div id="statusBox"></div>
                <div class="button-group">
                    <button class="btn-save" id="saveBtn">Save</button>
                    <button class="btn-skip" id="skipBtn">Skip</button>
                </div>
                <div style="margin-top: 30px; padding: 20px; background: #f0f7ff; border-radius: 8px;">
                    <h4 style="margin-bottom: 10px; color: #0066cc;">Instructions:</h4>
                    <ol style="margin-left: 20px; color: #333; line-height: 1.6;">
                        <li>View the cheque image on the left</li>
                        <li>Find the account number (A/C NO. field)</li>
                        <li>Enter the 12-18 digit account number</li>
                        <li>Click "Save" to confirm</li>
                        <li>Signature will be renamed: cheque_number_account_number.jpg</li>
                    </ol>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentIndex = 0;
        let cheques = [];
        let verifiedCount = 0;

        async function loadCheques() {
            try {
                const res = await fetch('/api/cheques');
                const data = await res.json();
                cheques = data.cheques;
                updateProgress();
                loadCheque(0);
            } catch (e) {
                document.getElementById('statusBox').innerHTML = '<div class="status-box status-error">Error loading cheques: ' + e.message + '</div>';
            }
        }

        async function loadCheque(index) {
            if (index >= cheques.length) {
                document.getElementById('statusBox').innerHTML = '<div class="status-box status-success">All cheques reviewed!</div>';
                document.getElementById('accountInput').disabled = true;
                document.getElementById('saveBtn').disabled = true;
                document.getElementById('skipBtn').disabled = true;
                return;
            }

            const chequeId = cheques[index];
            try {
                const res = await fetch('/api/cheque/' + chequeId);
                const data = await res.json();

                document.getElementById('chequeNum').textContent = data.cheque_id;
                document.getElementById('bankName').textContent = data.bank;
                document.getElementById('chequeImage').innerHTML = data.image ?
                    '<img src="' + data.image + '">' :
                    'Could not load image';
                document.getElementById('accountInput').value = '';
                document.getElementById('statusBox').innerHTML = '';

                if (data.verified) {
                    document.getElementById('statusBox').innerHTML = '<div class="status-box status-success">Already verified: ' + data.account_number + '</div>';
                }
            } catch (e) {
                document.getElementById('statusBox').innerHTML = '<div class="status-box status-error">Error loading cheque</div>';
            }
        }

        document.getElementById('saveBtn').addEventListener('click', async () => {
            const chequeId = cheques[currentIndex];
            const account = document.getElementById('accountInput').value.trim();

            if (!account) {
                document.getElementById('statusBox').innerHTML = '<div class="status-box status-error">Please enter an account number</div>';
                return;
            }

            const digits = account.replace(/\\D/g, '');
            if (digits.length < 12 || digits.length > 18) {
                document.getElementById('statusBox').innerHTML = '<div class="status-box status-error">Invalid length: ' + digits.length + ' (must be 12-18)</div>';
                return;
            }

            try {
                const res = await fetch('/api/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cheque_id: chequeId, account_number: digits })
                });
                const data = await res.json();

                document.getElementById('statusBox').innerHTML = '<div class="status-box status-success">Saved: ' + chequeId + ' → ' + digits + '</div>';
                verifiedCount++;
                updateProgress();

                setTimeout(() => nextCheque(), 500);
            } catch (e) {
                document.getElementById('statusBox').innerHTML = '<div class="status-box status-error">Error saving</div>';
            }
        });

        document.getElementById('skipBtn').addEventListener('click', () => {
            nextCheque();
        });

        function nextCheque() {
            currentIndex++;
            loadCheque(currentIndex);
        }

        function updateProgress() {
            const total = cheques.length;
            const percentage = total > 0 ? Math.round((verifiedCount / total) * 100) : 0;
            document.getElementById('progressBar').style.width = percentage + '%';
            document.getElementById('progressText').textContent = verifiedCount + ' / ' + total;
            document.getElementById('statVerified').textContent = verifiedCount;
            document.getElementById('statRemaining').textContent = total - verifiedCount;
            document.getElementById('statRate').textContent = percentage + '%';

            if (verifiedCount > 0) {
                document.getElementById('exportBtn').disabled = false;
            }
        }

        document.getElementById('exportBtn').addEventListener('click', async () => {
            document.getElementById('exportBtn').disabled = true;
            document.getElementById('exportBtn').textContent = 'Exporting...';

            try {
                const res = await fetch('/api/export', { method: 'POST' });
                const data = await res.json();

                if (data.success) {
                    document.getElementById('statusBox').innerHTML = '<div class="status-box status-success">Exported! ' + data.renamed + ' files renamed. Manifest updated.</div>';
                    document.getElementById('exportBtn').textContent = 'Exported Successfully!';
                } else {
                    document.getElementById('statusBox').innerHTML = '<div class="status-box status-error">Export error: ' + data.error + '</div>';
                    document.getElementById('exportBtn').disabled = false;
                    document.getElementById('exportBtn').textContent = 'Export & Rename Files';
                }
            } catch (e) {
                document.getElementById('statusBox').innerHTML = '<div class="status-box status-error">Error: ' + e.message + '</div>';
                document.getElementById('exportBtn').disabled = false;
                document.getElementById('exportBtn').textContent = 'Export & Rename Files';
            }
        });

        loadCheques();
    </script>
</body>
</html>"""

# Configuration
BASE_DIR = Path(r'C:\Users\Rushmitha\OneDrive\Desktop\cheque')
SIGNATURES_DIR = BASE_DIR / 'datasets/signatures/train'
METADATA_PATH = BASE_DIR / 'phase3/data/annotations/metadata.json'
SPLITS_DIR = BASE_DIR / 'datasets/splits'
VERIFICATION_FILE = BASE_DIR / 'datasets/signatures/verified_accounts.json'

# Load data
with open(METADATA_PATH) as f:
    metadata = json.load(f)

# Load image paths
image_paths = {}
for split in ['train', 'test', 'validation']:
    with open(SPLITS_DIR / f'{split}.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            image_paths[row['parent_id']] = row['image_path']

# Load verified accounts
verified_accounts = {}
if VERIFICATION_FILE.exists():
    with open(VERIFICATION_FILE) as f:
        verified_accounts = json.load(f)

# Get all cheques with signatures
all_cheques = sorted([
    f.name.split('_')[0]
    for f in SIGNATURES_DIR.glob('*_unknown.jpg')
])

@app.route('/', methods=['GET'])
def index():
    """Serve the HTML interface."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/cheques', methods=['GET'])
def get_cheques():
    """Get list of cheques to verify."""
    return jsonify({
        'total': len(all_cheques),
        'verified': len(verified_accounts),
        'remaining': len(all_cheques) - len(verified_accounts),
        'cheques': all_cheques
    })

@app.route('/api/cheque/<cheque_id>', methods=['GET'])
def get_cheque_data(cheque_id):
    """Get cheque image and metadata."""
    meta_key = f"{cheque_id}_reference"

    if meta_key not in metadata:
        return jsonify({'error': 'Cheque not found'}), 404

    meta = metadata[meta_key]

    # Get image
    image_path = BASE_DIR / meta.get('image_path', '')

    image_data = None
    if image_path.exists():
        img = cv2.imread(str(image_path))
        if img is not None:
            # Encode to base64
            ret, buffer = cv2.imencode('.jpg', img)
            image_data = 'data:image/jpeg;base64,' + base64.b64encode(buffer).decode()

    return jsonify({
        'cheque_id': cheque_id,
        'bank': meta.get('bank', 'Unknown'),
        'image': image_data,
        'verified': cheque_id in verified_accounts,
        'account_number': verified_accounts.get(cheque_id)
    })

@app.route('/api/verify', methods=['POST'])
def verify_account():
    """Verify and save account number."""
    data = request.get_json()
    cheque_id = data.get('cheque_id')
    account_number = data.get('account_number', '').strip()

    if not cheque_id or not account_number:
        return jsonify({'error': 'Missing cheque_id or account_number'}), 400

    # Validate account number
    digits = re.sub(r'\D', '', account_number)
    if len(digits) < 12 or len(digits) > 18:
        return jsonify({
            'error': f'Invalid account number length: {len(digits)} (must be 12-18 digits)'
        }), 400

    # Save verified account
    verified_accounts[cheque_id] = digits

    # Save to file
    with open(VERIFICATION_FILE, 'w') as f:
        json.dump(verified_accounts, f, indent=2)

    return jsonify({
        'success': True,
        'message': f'Saved: {cheque_id} → {digits}',
        'verified_count': len(verified_accounts)
    })

@app.route('/api/export', methods=['POST'])
def export_and_rename():
    """Export verified accounts and rename signature files."""
    try:
        renamed_count = 0
        errors = []

        # Rename files
        for sig_file in SIGNATURES_DIR.glob('*_unknown.jpg'):
            cheque_id = sig_file.name.split('_')[0]

            if cheque_id in verified_accounts:
                account = verified_accounts[cheque_id]
                new_name = f"{cheque_id}_{account}.jpg"
                new_path = sig_file.parent / new_name

                try:
                    sig_file.rename(new_path)
                    renamed_count += 1
                except Exception as e:
                    errors.append(f"{cheque_id}: {str(e)}")

        # Create manifest
        manifest = []
        for sig_file in SIGNATURES_DIR.glob('*.jpg'):
            filename = sig_file.name
            parts = filename.replace('.jpg', '').rsplit('_', 1)
            cheque_id = parts[0]
            account = parts[1] if len(parts) > 1 else 'unknown'

            manifest.append({
                'split': 'train',
                'cheque_id': cheque_id,
                'account_number': account,
                'filename': filename
            })

        # Save manifest
        manifest_path = SIGNATURES_DIR.parent / 'manifest.csv'
        with open(manifest_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['split', 'cheque_id', 'account_number', 'filename'])
            writer.writeheader()
            writer.writerows(sorted(manifest, key=lambda x: int(x['cheque_id'])))

        return jsonify({
            'success': True,
            'renamed': renamed_count,
            'total': len(all_cheques),
            'errors': errors,
            'message': f'Renamed {renamed_count} files. Manifest updated.'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress', methods=['GET'])
def get_progress():
    """Get progress statistics."""
    total = len(all_cheques)
    verified = len(verified_accounts)

    return jsonify({
        'total': total,
        'verified': verified,
        'remaining': total - verified,
        'percentage': round((verified / total * 100) if total > 0 else 0)
    })

if __name__ == '__main__':
    print(f"Starting Account Verifier Service...")
    print(f"Signatures directory: {SIGNATURES_DIR}")
    print(f"Total cheques to verify: {len(all_cheques)}")
    print(f"Already verified: {len(verified_accounts)}")
    print(f"\nRunning on http://127.0.0.1:8003")

    app.run(host='127.0.0.1', port=8003, debug=False)
