# app.py

from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import os
from utils import kbb

app = Flask(__name__)

# Configuration
app.config['DATABASE'] = os.path.join(app.root_path, 'data', 'cars.db')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'data', 'videos')


# Database helper functions
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
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
    state = request.args.get('state')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Build the SQL query with filters
    query = 'SELECT * FROM cars WHERE 1=1'
    params = []

    if make:
        if make == 'Unknown':
            query += ' AND make IS NULL'
        else:
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
    if state:
        query += ' AND state = ?'
        params.append(state)
    if start_date:
        query += " AND date(date_time) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(date_time) <= date(?)"
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
            'video_path': row['video_path'],
            'state': row['state']
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
    cursor.execute('''
        SELECT make, COUNT(*) as count
        FROM cars
        WHERE make IS NOT NULL AND make != ''
        GROUP BY make
        ORDER BY make ASC
    ''')
    rows = cursor.fetchall()
    conn.close()

    makes_with_counts = [{'make': row['make'], 'count': row['count']} for row in rows]

    return jsonify(makes_with_counts)

@app.route('/api/models')
def get_models():
    make = request.args.get('make')
    conn = get_db_connection()
    cursor = conn.cursor()
    if make:
        if make == 'Unknown':
            cursor.execute('SELECT DISTINCT model FROM cars WHERE make IS NULL AND model IS NOT NULL ORDER BY model')
        else:
            cursor.execute('SELECT DISTINCT model FROM cars WHERE make = ? AND model IS NOT NULL ORDER BY model',
                           (make,))
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


@app.route('/api/states')
def get_states():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT state FROM cars WHERE state IS NOT NULL ORDER BY state')
    rows = cursor.fetchall()
    conn.close()
    states = [row['state'] for row in rows]
    return jsonify(states)


@app.route('/api/update_car', methods=['POST'])
def update_car():
    data = request.get_json()
    car_id = data.get('id')
    year = data.get('year')
    make = data.get('make')
    model = data.get('model')
    license_plate = data.get('license_plate')
    state = data.get('state')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE cars
        SET year = ?, make = ?, model = ?, license_plate = ?, state = ?
        WHERE id = ?
    ''', (
        year, make, model, license_plate, state, car_id
    ))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})



@app.route('/api/refresh_car', methods=['POST'])
def refresh_car():
    data = request.get_json()
    car_id = data.get('id')
    license_plate = data.get('license_plate')
    state = data.get('state')

    if not (license_plate and state):
        return jsonify({'status': 'error', 'message': 'License plate and state are required'}), 400

    # Use KBB to get updated car info
    try:
        r = kbb.KBB(license_plate, state).lookup()
        if 'data' in r and 'vehicleUrlByLicense' in r['data'] and r['data']['vehicleUrlByLicense']['make']:
            vehicle_data = r['data']['vehicleUrlByLicense']
            year = vehicle_data.get('year')
            make = vehicle_data.get('make')
            model = vehicle_data.get('model')
            vin = vehicle_data.get('vin')

            # Update the car record in the database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                      UPDATE cars
                      SET year = ?, make = ?, model = ?, license_plate = ?, vin = ?, state = ?
                      WHERE id = ?
                  ''', (year, make, model, license_plate, vin, state, car_id))
            conn.commit()
            conn.close()

            return jsonify({
                'status': 'success',
                'year': year,
                'make': make,
                'model': model,
                'license_plate': license_plate,
                'vin': vin,
                'state': state
            })
        else:
            return jsonify({'status': 'error', 'message': 'Vehicle data not found in KBB response'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/unknown_cars')
def get_unknown_cars():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cars WHERE make IS NULL OR make = ""')
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
            'video_path': row['video_path'],
            'state': row['state']
        }
        cars.append(car)

    return jsonify(cars)

@app.route('/api/delete_car', methods=['POST'])
def delete_car():
    data = request.get_json()
    car_id = data.get('id')
    video_path = data.get('video_path')

    if not car_id:
        return jsonify({'status': 'error', 'message': 'No car ID provided'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete the car from the database
    cursor.execute('DELETE FROM cars WHERE id = ?', (car_id,))
    conn.commit()
    conn.close()

    # Delete the video file from the filesystem
    if video_path:
        video_full_path = os.path.join(app.config['UPLOAD_FOLDER'], video_path)
        try:
            if os.path.exists(video_full_path):
                os.remove(video_full_path)
        except Exception as e:
            # Handle exception if needed
            print(f"Error deleting video file: {e}")

    return jsonify({'status': 'success'})

@app.route('/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True)
