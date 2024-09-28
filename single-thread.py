import cv2
import easyocr
from utils import kbb
import re
import os
from collections import Counter
from datetime import datetime
import exiftool
import time

reader = easyocr.Reader(['en'])


def logs(msg):
    # Get the current time
    current_time = datetime.now()

    # Print the current time
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
        '0': ['O'],  # Zero to Capital O
        'O': ['0'],  # Capital O to Zero
        '1': ['I', 'L'],  # One to Capital I and L
        'I': ['1'],  # Capital I to One
        '5': ['S'],  # Five to S
        'S': ['5'],  # S to Five
        '6': ['G'],  # Six to G
        'G': ['6'],  # G to Six
        '8': ['B'],  # Eight to B
        'B': ['8'],  # B to Eight
        'Z': ['2', '7'],  # Z to Two and Seven
        '2': ['Z', '7'],
        '7': ['Z', '2'],
        'Q': ['O'],  # Q to O
        '4': ['L'],
        'L': ['4'],
    }

    result = []
    seen = set()

    # Start with the original string
    result.append(input_string)
    seen.add(input_string)

    # Function to generate variations
    def generate_for_position(position, current_strings):
        if position >= len(input_string):
            return

        next_strings = []
        for s in current_strings:
            orig_char = s[position]
            if orig_char in mistaken_mapping:
                # For each substitution in the order specified in mistaken_mapping
                for substitution in mistaken_mapping[orig_char]:
                    new_s = s[:position] + substitution + s[position + 1:]
                    if new_s not in seen:
                        seen.add(new_s)
                        result.append(new_s)
                        next_strings.append(new_s)

        # After processing substitutions at the current position,
        # proceed to the next position with the new strings
        if next_strings:
            # Only proceed with new strings that had substitutions at this position
            generate_for_position(position + 1, next_strings)
        else:
            # No substitutions at this position, proceed with the same strings
            generate_for_position(position + 1, current_strings)

    # Start generating variations from position 0
    generate_for_position(0, [input_string])

    return result


def add_kbb_info(plate, car):
    car['success'] = False
    r = kbb.KBB(plate, "CA").lookup()
    try:
        if r['data']['vehicleUrlByLicense']['url']:
            logs(f"Found a KBB entry for license {plate} !")
            car['year'] = r['data']['vehicleUrlByLicense']['year']
            car['make'] = r['data']['vehicleUrlByLicense']['make']
            car['model'] = r['data']['vehicleUrlByLicense']['model']
            car['plate'] = plate
            car['url'] = r['data']['vehicleUrlByLicense']['url']
            car['success'] = True
        # else:
        #     logs(f"Unable to find plate {plate}")
    except:
        logs("Something happened when looking up via KBB")


def list_mov_files_in_directory(directory):
    # Get all .MOV files in the directory
    mov_files = [f for f in os.listdir(directory)
                 if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith('.mov')]

    # Sort the .MOV files in alphabetical order
    mov_files.sort()

    return mov_files


def is_license_plate(text):
    # Example criteria: Length and character pattern for license plates
    return len(text) >= 5 and len(text) <= 10 and any(char.isdigit() for char in text)


def clean_license_plate(license_plate):
    # Use regex to keep only alphanumeric characters (A-Z, a-z, 0-9)
    cleaned_plate = re.sub(r'[^A-Za-z0-9]', '', license_plate)
    return cleaned_plate.upper()


def process_video(video_file, frame_skip):
    start_time = time.time()
    print("")
    logs(f"Processing {video_file}")
    car = {}

    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        logs("Error: Could not open video file.")
        return

    # Get the number of frames
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
        # only process certain frames
        if current_frame % frame_skip == 0:
            read_frames += 1
            # logs(f"On frame number: {current_frame}")
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

def find_car_from_file(file, frame_skip=3):
    car = {}
    video_file = directory_path + f"/{file}"
    metadata = get_video_metadata(video_file)
    car['file'] = video_file
    car['gps'] = metadata['Composite:GPSPosition']

    possible_plates = process_video(video_file, frame_skip)
    logs(f"Possible plates found: {len(possible_plates)}")
    # for p in possible_plates:
    #     print(p)

    # First try variations of most common text found
    plate = ""
    most_common_count = 0
    count = Counter(possible_plates)
    try:
        plate, most_common_count = count.most_common(1)[0]
    except:
        print(f"Could not find any license plate text from {file}")
    logs(f"The most common value is: '{plate}' with {most_common_count} occurrences.")

    variations = generate_variations(plate)
    logs(f"Variation count for {plate}: {len(variations)}")
    for index, variation in enumerate(variations):
        add_kbb_info(variation, car)
        if car['success']:
            break
        else:
            time.sleep(1)
        if index >= 50:
            logs(f"we tried too many variations, giving up on {file}")
            break

    if car['success']:
        return car
    else:
        logs(f"Did not find any cars with all the variations for file {file}")

    logs("Trying raw text found from video rather than variations...")
    for possible_plate in list(set(possible_plates)):
        add_kbb_info(possible_plate, car)
        if car['success']:
            break
        else:
            time.sleep(1)

    return car


cars = []
directory_path = '/Users/neil/Downloads/lps'
frame_skip = 3
# directory_path = '/Users/neil/Downloads/licensePlates'
files = list_mov_files_in_directory(directory_path)
total_files = len(files)
logs(f"Total files: {total_files}")
plates_not_found = []
total_start_time = time.time()

for f in files:
    start_time = time.time()
    car = find_car_from_file(f, frame_skip=3)
    end_time = time.time()

    elapsed_time = round((end_time - start_time), 2)
    car['process_time'] = elapsed_time
    logs(f"Finished processing {f} in {elapsed_time} seconds")
    cars.append(car)

total_end_time = time.time()
elapsed_time = total_end_time - total_start_time
print("---------------------------------------------------")
print("")

logs(f"Finished processing {total_files} files in {round(elapsed_time, 2)} seconds")
logs(f"Frame skip: {frame_skip}")
logs(f"Avg time per car: {round(elapsed_time / len(cars), 2)}")

success_count = sum(1 for c in cars if c.get('success') == True)
fail_count = sum(1 for c in cars if c.get('success') == False)

logs(f"Success rate: {round(success_count / (len(files)), 2)}")
print("")

logs(f"Total successful cars: {success_count}")
sorted_cars = sorted(cars, key=lambda x: x['process_time'], reverse=True)

for car in sorted_cars:
    if car['success']:
        print(car)

print("")

logs(f"Total failed cars: {fail_count}")
for car in sorted_cars:
    if not car['success']:
        print(car)