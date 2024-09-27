import cv2
import easyocr
import kbb
import re
import os
from collections import Counter
from datetime import datetime
import exiftool
import time
from multiprocessing import Pool
from functools import partial
import math

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
        '0': ['O'],
        'O': ['0'],
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
        'Q': ['O'],
        '4': ['L'],
        'L': ['4'],
    }

    result = []
    seen = set()

    result.append(input_string)
    seen.add(input_string)

    def generate_for_position(position, current_strings):
        if position >= len(input_string):
            return

        next_strings = []
        for s in current_strings:
            orig_char = s[position]
            if orig_char in mistaken_mapping:
                for substitution in mistaken_mapping[orig_char]:
                    new_s = s[:position] + substitution + s[position + 1:]
                    if new_s not in seen:
                        seen.add(new_s)
                        result.append(new_s)
                        next_strings.append(new_s)

        if next_strings:
            generate_for_position(position + 1, next_strings)
        else:
            generate_for_position(position + 1, current_strings)

    generate_for_position(0, [input_string])

    return result

def add_kbb_info(plate, car):
    car['success'] = False
    r = kbb.KBB(plate, "CA").lookup()
    try:
        if r['data']['vehicleUrlByLicense']['url']:
            logs(f"Found a KBB entry for license {plate}!")
            car['year'] = r['data']['vehicleUrlByLicense']['year']
            car['make'] = r['data']['vehicleUrlByLicense']['make']
            car['model'] = r['data']['vehicleUrlByLicense']['model']
            car['plate'] = plate
            car['url'] = r['data']['vehicleUrlByLicense']['url']
            car['success'] = True
    except:
        logs("Something happened when looking up via KBB")

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
    car = {}

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
    if metadata and 'Composite:GPSPosition' in metadata:
        car['gps'] = metadata['Composite:GPSPosition']
    else:
        car['gps'] = None

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
        return car
    else:
        logs(f"Did not find any cars with all the variations for file {file}")

    logs("Trying raw text found from video rather than variations...")
    for possible_plate in list(set(possible_plates)):
        add_kbb_info(possible_plate, car)
        if car.get('success'):
            break
        else:
            time.sleep(1)

    return car

def process_files(file_list, directory_path, frame_skip):
    # Initialize EasyOCR reader once per process
    reader = easyocr.Reader(['en'])
    logs(f"Initialized EasyOCR reader in process PID {os.getpid()}")
    results = []
    for f in file_list:
        start_time = time.time()
        car = find_car_from_file(f, directory_path, frame_skip, reader)
        end_time = time.time()
        elapsed_time = round((end_time - start_time), 2)
        car['process_time'] = elapsed_time
        logs(f"Finished processing {f} in {elapsed_time} seconds")
        results.append(car)
    return results

if __name__ == '__main__':
    cars = []
    directory_path = '/Users/neil/Downloads/lps'  # Update your directory path as needed
    frame_skip = 3
    files = list_mov_files_in_directory(directory_path)
    total_files = len(files)
    num_processes = 4  # Adjust based on your CPU cores
    logs(f"Total files: {total_files}")
    total_start_time = time.time()

    # Divide files among processes
    files_per_process = math.ceil(total_files / num_processes)
    file_chunks = [files[i:i + files_per_process] for i in range(0, total_files, files_per_process)]

    # Prepare the partial function
    process_files_partial = partial(process_files, directory_path=directory_path, frame_skip=frame_skip)

    with Pool(processes=num_processes) as pool:
        results = pool.map(process_files_partial, file_chunks)

    # Flatten the list of results
    cars = [car for sublist in results for car in sublist]

    total_end_time = time.time()
    elapsed_time = total_end_time - total_start_time
    print("---------------------------------------------------\n")

    logs(f"Finished processing {total_files} files in {round(elapsed_time, 2)} seconds")
    logs(f"Frame skip: {frame_skip}")
    logs(f"Avg time per car: {round(elapsed_time / len(cars), 2)}")

    success_count = sum(1 for c in cars if c.get('success'))
    fail_count = sum(1 for c in cars if not c.get('success'))

    logs(f"Success rate: {round(success_count / len(files), 2)}\n")

    logs(f"Total successful cars: {success_count}")
    sorted_cars = sorted(cars, key=lambda x: x['process_time'], reverse=True)

    for car in sorted_cars:
        if car.get('success'):
            print(car)

    print("")

    logs(f"Total failed cars: {fail_count}")
    for car in sorted_cars:
        if not car.get('success'):
            print(car)
