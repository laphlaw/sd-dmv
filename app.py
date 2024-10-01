# app.py

from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import os

app = Flask(__name__)

# Configuration
app.config['DATABASE'] = os.path.join(app.root_path, 'data', 'cars.db')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'data', 'videos')

# Database helper function
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
    start_year = request.args.get('start_year')
    end_year = request.args.get('end_year')
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
        query += ' AND make = ?'
        params.append(make)
    if model:
        query += ' AND model = ?'
        params.append(model)
    if start_year:
        query += ' AND year >= ?'
        params.append(start_year)
    if end_year:
        query += ' AND year <= ?'
        params.append(end_year)
    if license_plate:
        query += ' AND license_plate LIKE ?'
        params.append(f'%{license_plate}%')
    if color:
        query += ' AND color = ?'
        params.append(color)
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

@app.route('/api/first_car_location')
def get_first_car_location():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT latitude, longitude FROM cars WHERE latitude IS NOT NULL AND longitude IS NOT NULL LIMIT 1')
    row = cursor.fetchone()
    conn.close()

    if row:
        location = {'latitude': row['latitude'], 'longitude': row['longitude']}
        return jsonify(location)
    else:
        return jsonify({'latitude': 0, 'longitude': 0})

@app.route('/api/makes')
def get_makes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT make FROM cars WHERE make IS NOT NULL ORDER BY make')
    rows = cursor.fetchall()
    conn.close()
    makes = [row['make'] for row in rows]
    return jsonify(makes)

@app.route('/api/models')
def get_models():
    make = request.args.get('make')
    conn = get_db_connection()
    cursor = conn.cursor()
    if make:
        cursor.execute('SELECT DISTINCT model FROM cars WHERE make = ? AND model IS NOT NULL ORDER BY model', (make,))
    else:
        cursor.execute('SELECT DISTINCT model FROM cars WHERE model IS NOT NULL ORDER BY model')
    rows = cursor.fetchall()
    conn.close()
    models = [row['model'] for row in rows]
    return jsonify(models)

@app.route('/api/years')
def get_years():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT year FROM cars WHERE year IS NOT NULL ORDER BY year')
    rows = cursor.fetchall()
    conn.close()
    years = [row['year'] for row in rows]
    return jsonify(years)

@app.route('/api/update_car', methods=['POST'])
def update_car():
    data = request.get_json()
    car_id = data.get('id')
    date_time = data.get('date_time')
    year = data.get('year')
    make = data.get('make')
    model = data.get('model')
    license_plate = data.get('license_plate')
    color = data.get('color')
    vin = data.get('vin')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE cars
        SET date_time = ?, year = ?, make = ?, model = ?, license_plate = ?, color = ?, vin = ?, latitude = ?, longitude = ?
        WHERE id = ?
    ''', (
        date_time, year, make, model, license_plate, color, vin, latitude, longitude, car_id
    ))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

@app.route('/api/delete_car', methods=['POST'])
def delete_car():
    data = request.get_json()
    car_id = data.get('id')

    if not car_id:
        return jsonify({'status': 'error', 'message': 'No car ID provided'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM cars WHERE id = ?', (car_id,))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

@app.route('/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
