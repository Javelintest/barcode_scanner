from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS
import os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)  # Allow Cross-Origin Requests

# Load environment variables
load_dotenv()

# Database configuration (from .env file)
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

def get_db_connection():
    """Establish database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print("Database Connection Error:", err)
        return None

def create_table():
    """Ensure the dispatch_records table exists."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dispatch_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        tracking_id VARCHAR(255) UNIQUE,
                        panel_name VARCHAR(50),
                        status VARCHAR(50) DEFAULT 'Pending'
                    );
                """)
                conn.commit()
        finally:
            conn.close()

@app.route('/scan_item', methods=['POST'])
def scan_item():
    """API to insert scanned tracking ID with panel selection."""
    try:
        data = request.json
        tracking_id = data.get('tracking_id')
        panel = data.get('panel')

        if not tracking_id or not panel:
            return jsonify({'error': 'Tracking ID and Panel are required'}), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500

        with conn.cursor(dictionary=True) as cursor:
            # Check if tracking_id exists
            cursor.execute("SELECT tracking_id FROM dispatch_records WHERE tracking_id = %s", (tracking_id,))
            existing = cursor.fetchone()

            if existing:
                message = 'Tracking ID already exists. Flagging for review.'
                cursor.execute("UPDATE dispatch_records SET status='Flagged' WHERE tracking_id=%s", (tracking_id,))
            else:
                cursor.execute(
                    "INSERT INTO dispatch_records (tracking_id, Panel_Name, status) VALUES (%s, %s, 'Pending')",
                    (tracking_id, panel)
                )
                message = 'Item scanned and recorded successfully.'

            conn.commit()

        conn.close()
        return jsonify({'message': message})

    except mysql.connector.Error as db_err:
        return jsonify({'error': f'Database Error: {db_err}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    create_table()
    app.run(debug=True)
