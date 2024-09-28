# app.py

from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import os

app = Flask(__name__)

# Configuration
app.config['DATABASE'] = os.path.join(app.root_path, 'data', 'cars.db')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'data', 'videos')

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    return conn

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/cars')
def get_cars():
    # Fetch filter parameters from request.args
    make = request.args.get('make')
    model = request.args.get('model')
    year = request.args.get('year')
    license_plate = request.args.get('license_plate')
    color = request.args.get('color')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Build the SQL query with filters
    query = 'SELECT * FROM cars WHERE 1=1'
    params = []

    if make:
        query += ' AND make LIKE ?'
        params.append(f'%{make}%')
    if model:
        query += ' AND model LIKE ?'
        params.append(f'%{model}%')
    if year:
        query += ' AND year = ?'
        params.append(year)
    if license_plate:
        query += ' AND license_plate LIKE ?'
        params.append(f'%{license_plate}%')
    if color:
        query += ' AND color LIKE ?'
        params.append(f'%{color}%')
    if start_date:
        query += ' AND date_time >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date_time <= ?'
        params.append(end_date)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Convert rows to dictionaries
    cars = []
    for row in rows:
        car = {
            'id': row['id'],
            'date_time': row['date_time'],
            'year': row['year'],
            'make': row['make'],
            'model': row['model'],
            'license_plate': row['license_plate'],
            'color': row['color'],
            'vin': row['vin'],
            'latitude': row['latitude'],
            'longitude': row['longitude'],
            'video_path': row['video_path']
        }
        cars.append(car)

    return jsonify(cars)

@app.route('/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
