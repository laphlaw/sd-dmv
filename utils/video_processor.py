# utils/video_processor.py

import cv2
import easyocr
import kbb  # Assuming kbb.py is in the same directory
import re
import os
import sqlite3
from collections import Counter
from datetime import datetime
import exiftool
import time
import itertools
import shutil

# Path to the database
DATABASE = os.path.join('data', 'cars.db')

def logs(msg):
    current_time = datetime.now()
    print(current_time.strftime("%H:%M:%S") + f" {msg}")

def get_video_metadata(video_file):
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata(video_file)
        try:
            return metadata[0]
        except:
            logs("Unable to get metadata")
            return None

def generate_variations(input_string):
    mistaken_mapping = {
        '0': ['O', 'D'],
        'O': ['0'],
        'Q': ['O', '0'],
        '1': ['I', 'L'],
        'I': ['1'],
        '5': ['S'],
        'S': ['5'],
        '6': ['G'],
        'G': ['6'],
        '8': ['B'],
        'B': ['8'],
        'Z': ['2', '7'],
        '2': ['Z', '7'],
        '7': ['Z', '2'],
        '4': ['L'],
        'L': ['4'],
    }

    # Step 1: Assign priority to each substitution pair based on the order in mistaken_mapping
    substitution_priority = {}
    priority = 1
    for key, substitutions in mistaken_mapping.items():
        for sub in substitutions:
            substitution_priority[(key, sub)] = priority
            priority += 1

    # Step 2: Prepare substitution options for each character, including the original character
    substitution_options = []
    for char in input_string:
        options = [char]
        substitutions = mistaken_mapping.get(char, [])
        if substitutions:
            options.extend(substitutions)
        substitution_options.append(options)

    # Step 3: Generate all possible combinations using itertools.product
    all_combinations = itertools.product(*substitution_options)

    # Step 4: Define a function to calculate priority metrics for a given variation
    def calculate_priority_metrics(original, variant):
        substitution_scores = []
        for o, v in zip(original, variant):
            if o != v:
                pair = (o, v)
                # If the substitution pair exists in the priority mapping, add its priority
                score = substitution_priority.get(pair, float('inf'))  # Use a high score if not found
                substitution_scores.append(score)
        if substitution_scores:
            min_priority = min(substitution_scores)
            sum_priority = sum(substitution_scores)
            return (min_priority, sum_priority)
        else:
            # Original string has the highest priority
            return (0, 0)

    # Step 5: Collect variations with their priority metrics
    variations_with_priority = []
    for combo in all_combinations:
        variant = ''.join(combo)
        priority_metrics = calculate_priority_metrics(input_string, variant)
        variations_with_priority.append((priority_metrics, variant))

    # Step 6: Sort the variations based on priority metrics
    # Primary: min_priority ascending
    # Secondary: sum_priority ascending
    sorted_variations = sorted(variations_with_priority, key=lambda x: (x[0][0], x[0][1]))

    # Step 7: Extract the sorted variation strings, maintaining the original string first
    sorted_variations_list = [variant for metrics, variant in sorted_variations]

    return sorted_variations_list

def add_kbb_info(plate, car):
    car['success'] = False
    r = kbb.KBB(plate, "CA").lookup()
    try:
        if r['data']['vehicleUrlByLicense']['url']:
            logs(f"Found a KBB entry for license {plate}!")
            car['year'] = r['data']['vehicleUrlByLicense']['year']
            car['make'] = r['data']['vehicleUrlByLicense']['make']
            car['model'] = r['data']['vehicleUrlByLicense']['model']
            car['vin'] = r['data']['vehicleUrlByLicense']['vin']
            car['plate'] = plate
            car['url'] = r['data']['vehicleUrlByLicense']['url']
            car['success'] = True
    except Exception as e:
        logs(f"Error when looking up via KBB: {e}")

def list_mov_files_in_directory(directory):
    mov_files = [f for f in os.listdir(directory)
                 if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith('.mov')]
    mov_files.sort()
    return mov_files

def is_license_plate(text):
    return len(text) >= 5 and len(text) <= 10 and any(char.isdigit() for char in text)

def clean_license_plate(license_plate):
    cleaned_plate = re.sub(r'[^A-Za-z0-9]', '', license_plate)
    return cleaned_plate.upper()

def process_video(video_file, frame_skip, reader):
    start_time = time.time()
    logs(f"Processing {video_file}")

    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        logs("Error: Could not open video file.")
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    logs(f"Total number of frames: {total_frames}. Frame skip: {frame_skip}")
    possible_plates = []

    logs("Reading text from video frames...")
    current_frame = 0
    read_frames = 0
    while True:
        read_success, frame = cap.read()
        if not read_success:
            break
        if current_frame % frame_skip == 0:
            read_frames += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Run EasyOCR
            results = reader.readtext(gray)
            for (bbox, text, prob) in results:
                plate = clean_license_plate(text)
                if is_license_plate(plate):
                    possible_plates.append(plate)

        current_frame += 1

    cap.release()

    end_time = time.time()
    logs(f"Analyzed {read_frames} frames in {round(end_time - start_time, 2)} secs")
    return sorted(possible_plates, key=len, reverse=True)

def find_car_from_file(file, directory_path, frame_skip, reader):
    car = {}
    video_file = os.path.join(directory_path, file)
    metadata = get_video_metadata(video_file)
    car['file'] = video_file
    if metadata and 'Composite:GPSLatitude' in metadata:
        try:
            car['latitude'] = metadata['Composite:GPSLatitude']
            car['longitude'] = metadata['Composite:GPSLongitude']
        except:
            logs("Unable to read GPS data from file metadata")
            car['latitude'] = None
            car['longitude'] = None
    else:
        car['latitude'] = None
        car['longitude'] = None

    if metadata and 'QuickTime:CreateDate' in metadata:
        original_date = metadata['QuickTime:CreateDate']
        date_obj = datetime.strptime(original_date, '%Y:%m:%d %H:%M:%S')
        corrected_date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
        car['date_time'] = corrected_date
    else:
        car['date_time'] = None

    possible_plates = process_video(video_file, frame_skip, reader)
    logs(f"Possible plates found: {len(possible_plates)}")

    plate = ""
    most_common_count = 0
    count = Counter(possible_plates)
    try:
        plate, most_common_count = count.most_common(1)[0]
    except:
        logs(f"Could not find any license plate text from {file}")
        car['success'] = False
        return car

    logs(f"The most common value is: '{plate}' with {most_common_count} occurrences.")

    variations = generate_variations(plate)
    logs(f"Variation count for {plate}: {len(variations)}")
    for index, variation in enumerate(variations):
        add_kbb_info(variation, car)
        if car.get('success'):
            break
        else:
            time.sleep(1)
        if index >= 50:
            logs(f"We tried too many variations, giving up on {file}")
            break

    if car.get('success'):
        car['license_plate'] = car['plate']
        car['video_path'] = file  # Assuming the video file is in the data/videos/ directory
        return car
    else:
        logs(f"Did not find any cars with all the variations for file {file}")
        car['license_plate'] = plate  # Store the plate even if KBB lookup failed
        car['video_path'] = file
        car['success'] = False

    return car

def insert_car_data(car_data):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create the table if it doesn't exist (now includes 'state' column)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_time TEXT,
        year INTEGER,
        make TEXT,
        model TEXT,
        license_plate TEXT,
        color TEXT,
        vin TEXT,
        latitude REAL,
        longitude REAL,
        video_path TEXT,
        state TEXT
    )
    ''')

    # Insert the car data
    cursor.execute('''
    INSERT INTO cars (date_time, year, make, model, license_plate, color, vin, latitude, longitude, video_path, state)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        car_data.get('date_time'),
        car_data.get('year'),
        car_data.get('make'),
        car_data.get('model'),
        car_data.get('license_plate'),
        car_data.get('color'),
        car_data.get('vin'),
        car_data.get('latitude'),
        car_data.get('longitude'),
        car_data.get('video_path'),
        car_data.get('state')
    ))

    conn.commit()
    conn.close()


def process_videos(directory_path, frame_skip=3):
    files = list_mov_files_in_directory(directory_path)
    total_files = len(files)
    logs(f"Total files: {total_files}")

    # Initialize EasyOCR reader once
    reader = easyocr.Reader(['en'])

    for f in files:
        start_time = time.time()
        car = find_car_from_file(f, directory_path, frame_skip, reader)
        car['state'] = "CA" # hack for now.. just hardcode CA
        end_time = time.time()
        elapsed_time = round((end_time - start_time), 2)
        car['process_time'] = elapsed_time
        insert_car_data(car)

        orig_filepath = directory_path + "/" + f
        new_filepath = f"data/videos/{f}"
        shutil.move(orig_filepath, new_filepath)
        logs(f"Moving {orig_filepath} to {new_filepath}")
        logs(f"Finished processing {f} in {elapsed_time} seconds")


if __name__ == '__main__':
    directory_path = 'data/videos-to-process/'  # Update with your actual directory
    frame_skip = 3  # Adjust as needed

    process_videos(directory_path, frame_skip)
