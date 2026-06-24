"""
Simple Flask server to serve PMF data to the React dashboard
Includes authentication middleware
"""

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import pandas as pd
import json
from pathlib import Path
from auth import authenticate_user, validate_token, logout_user
from functools import wraps

app = Flask(__name__)
CORS(app)

OUTPUT_DIR = Path(__file__).parent / 'output'

def require_auth(f):
    """Decorator to require authentication on endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'error': 'Missing authorization header'}), 401

        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            return jsonify({'error': 'Invalid authorization header'}), 401

        session = validate_token(token)
        if not session:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Store user info in request context for use in the endpoint
        request.user_id = session['user_id']
        return f(*args, **kwargs)

    return decorated_function

@app.route('/api/pmf/scores', methods=['GET'])
@require_auth
def get_pmf_scores():
    """Load PMF matrix CSV and return as JSON"""
    csv_path = OUTPUT_DIR / 'agent4_pmf_matrix.csv'

    if not csv_path.exists():
        return jsonify({'error': 'No PMF data available. Run agent4.py first.'}), 404

    try:
        df = pd.read_csv(csv_path)
        # Rename columns to match dashboard expectations
        df = df.rename(columns={
            'Market': 'market',
            'Technology': 'technology',
            'PMF_Score': 'pmf',
            'Confidence_Score': 'confidence',
            'Desirability': 'desirability',
            'Feasibility': 'feasibility',
            'Viability': 'viability',
            'Risk_Penalty': 'risk'
        })

        data = df.to_dict(orient='records')
        return jsonify({
            'status': 'success',
            'data': data,
            'count': len(data)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pmf/summary', methods=['GET'])
@require_auth
def get_pmf_summary():
    """Get scoring summary statistics"""
    json_path = OUTPUT_DIR / 'agent4_summary.json'

    if not json_path.exists():
        return jsonify({'error': 'No summary available'}), 404

    try:
        with open(json_path) as f:
            summary = json.load(f)
        return jsonify({'status': 'success', 'data': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pmf/audit/<cell_id>', methods=['GET'])
@require_auth
def get_audit_trail(cell_id):
    """Get audit trail for a specific cell"""
    json_path = OUTPUT_DIR / 'agent4_audit_trail.json'

    if not json_path.exists():
        return jsonify({'error': 'No audit trail available'}), 404

    try:
        with open(json_path) as f:
            audit_data = json.load(f)

        cell_audit = audit_data.get('cells', {}).get(cell_id)
        if cell_audit:
            return jsonify({'status': 'success', 'data': cell_audit})
        else:
            return jsonify({'error': 'Cell not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

# ═══════════════════════════════════════════════════════════════════════════
# AUTHENTICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint - authenticate user and return token"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user_id = data.get('user_id', '').strip()
    password = data.get('password', '')

    if not user_id or not password:
        return jsonify({'error': 'User ID and password are required'}), 400

    success, result = authenticate_user(user_id, password)

    if success:
        return jsonify({
            'status': 'success',
            'token': result,
            'user_id': user_id,
            'message': 'Authentication successful'
        }), 200
    else:
        return jsonify({'error': result}), 401

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout endpoint - invalidate token"""
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1]

    logout_user(token)

    return jsonify({
        'status': 'success',
        'message': 'Logged out successfully'
    }), 200

@app.route('/api/auth/verify', methods=['GET'])
@require_auth
def verify_token():
    """Verify token validity"""
    return jsonify({
        'status': 'success',
        'user_id': request.user_id,
        'message': 'Token is valid'
    }), 200

if __name__ == '__main__':
    print("PMF Dashboard Backend Server")
    print("Running on http://localhost:5001")
    print(f"Serving data from: {OUTPUT_DIR}")
    app.run(debug=True, port=5001)
