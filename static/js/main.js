// static/js/main.js

let map;
let markers = [];
let infoWindow;
let currentCarId = null;
let currentMarker = null;

function initMap() {
    // Initialize the map after fetching the first car's location
    fetch('/api/first_car_location')
        .then(response => response.json())
        .then(location => {
            const defaultLocation = { lat: location.latitude, lng: location.longitude };
            map = new google.maps.Map(document.getElementById('map'), {
                center: defaultLocation,
                zoom: 12,
            });

            // Load initial data
            fetchCars();

            // Populate dropdowns
            populateMakes();
            populateYears();

            // Add event listener to the filter form
            document.getElementById('filter-form').addEventListener('submit', function(event) {
                event.preventDefault();
                fetchCars();
            });

            // Handle make change to update models
            document.getElementById('make').addEventListener('change', function() {
                populateModels();
            });

            // Handle reset filters button
            document.getElementById('reset-filters').addEventListener('click', function() {
                resetFilters();
                fetchCars();
            });
        })
        .catch(error => console.error('Error fetching first car location:', error));
}

function fetchCars() {
    // Get filter values
    const make = document.getElementById('make').value;
    const model = document.getElementById('model').value;
    const start_year = document.getElementById('start_year').value;
    const end_year = document.getElementById('end_year').value;
    const license_plate = document.getElementById('license_plate').value;
    const color = document.getElementById('color').value;
    const start_date = document.getElementById('start_date').value;
    const end_date = document.getElementById('end_date').value;

    // Build query parameters
    const params = new URLSearchParams();

    if (make) params.append('make', make);
    if (model) params.append('model', model);
    if (start_year) params.append('start_year', start_year);
    if (end_year) params.append('end_year', end_year);
    if (license_plate) params.append('license_plate', license_plate);
    if (color) params.append('color', color);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);

    // Fetch data from the backend
    fetch('/api/cars?' + params.toString())
        .then(response => response.json())
        .then(data => {
            // Clear existing markers
            clearMarkers();
            // Add new markers
            addMarkers(data);
        })
        .catch(error => console.error('Error fetching car data:', error));
}

function addMarkers(cars) {
    cars.forEach(car => {
        const position = { lat: parseFloat(car.latitude), lng: parseFloat(car.longitude) };
        const marker = new google.maps.Marker({
            position: position,
            map: map,
            title: `${car.year} ${car.make} ${car.model}`,
        });

        marker.carData = car;

        marker.addListener('click', function() {
            currentCarId = car.id;
            currentMarker = marker; // Store the current marker for later removal

            // Create a new div element to hold the info window content
            const contentDiv = document.createElement('div');

            // Build the HTML content with current values
            contentDiv.innerHTML = `
                <h3><input type="text" id="info-title-${car.id}" value="${marker.title}" readonly></h3>
                <p>
                    <label for="info-license-plate-${car.id}">License Plate:</label>
                    <input type="text" id="info-license-plate-${car.id}" value="${car.license_plate || ''}">
                </p>
                <p>
                    <label for="info-vin-${car.id}">VIN:</label>
                    <input type="text" id="info-vin-${car.id}" value="${car.vin || ''}">
                </p>
                <p>
                    <label for="info-make-${car.id}">Make:</label>
                    <input type="text" id="info-make-${car.id}" value="${car.make || ''}">
                </p>
                <p>
                    <label for="info-model-${car.id}">Model:</label>
                    <input type="text" id="info-model-${car.id}" value="${car.model || ''}">
                </p>
                <p>
                    <label for="info-year-${car.id}">Year:</label>
                    <input type="number" id="info-year-${car.id}" value="${car.year || ''}">
                </p>
                <p>
                    <label for="info-color-${car.id}">Color:</label>
                    <input type="text" id="info-color-${car.id}" value="${car.color || ''}">
                </p>
                <p>
                    <label for="info-date-time-${car.id}">Date/Time:</label>
                    <input type="datetime-local" id="info-date-time-${car.id}" value="${car.date_time ? car.date_time.replace(' ', 'T') : ''}">
                </p>
                <p>
                    <label for="info-latitude-${car.id}">Latitude:</label>
                    <input type="text" id="info-latitude-${car.id}" value="${car.latitude || ''}">
                </p>
                <p>
                    <label for="info-longitude-${car.id}">Longitude:</label>
                    <input type="text" id="info-longitude-${car.id}" value="${car.longitude || ''}">
                </p>
                <button type="button" id="save-car-data-${car.id}">Save</button>
                <button type="button" id="delete-car-data-${car.id}" class="delete-button">Delete</button>
                <video width="320" height="240" controls>
                    <source src="/videos/${car.video_path}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            `;

            // Create the info window
            if (!infoWindow) {
                infoWindow = new google.maps.InfoWindow();
            }
            infoWindow.setContent(contentDiv);
            infoWindow.open(map, marker);

            // Add event listeners for buttons after the info window is rendered
            google.maps.event.addListenerOnce(infoWindow, 'domready', function() {
                // Save button
                document.getElementById(`save-car-data-${car.id}`).addEventListener('click', function() {
                    saveCarData(car.id);
                });

                // Delete button
                document.getElementById(`delete-car-data-${car.id}`).addEventListener('click', function() {
                    deleteCarData(car.id);
                });
            });
        });

        markers.push(marker);
    });
}

function clearMarkers() {
    markers.forEach(marker => {
        marker.setMap(null);
    });
    markers = [];
}

function populateMakes() {
    fetch('/api/makes')
        .then(response => response.json())
        .then(makes => {
            const makeSelect = document.getElementById('make');
            makeSelect.innerHTML = '<option value="">All</option>';
            makes.forEach(make => {
                const option = document.createElement('option');
                option.value = make;
                option.textContent = make;
                makeSelect.appendChild(option);
            });
        })
        .catch(error => console.error('Error fetching makes:', error));
}

function populateModels() {
    const make = document.getElementById('make').value;
    const params = new URLSearchParams();
    if (make) params.append('make', make);

    fetch('/api/models?' + params.toString())
        .then(response => response.json())
        .then(models => {
            const modelSelect = document.getElementById('model');
            modelSelect.innerHTML = '<option value="">All</option>';
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });
        })
        .catch(error => console.error('Error fetching models:', error));
}

function populateYears() {
    fetch('/api/years')
        .then(response => response.json())
        .then(years => {
            const startYearSelect = document.getElementById('start_year');
            const endYearSelect = document.getElementById('end_year');
            startYearSelect.innerHTML = '<option value="">Any</option>';
            endYearSelect.innerHTML = '<option value="">Any</option>';
            years.forEach(year => {
                const option1 = document.createElement('option');
                option1.value = year;
                option1.textContent = year;
                startYearSelect.appendChild(option1);

                const option2 = document.createElement('option');
                option2.value = year;
                option2.textContent = year;
                endYearSelect.appendChild(option2);
            });
        })
        .catch(error => console.error('Error fetching years:', error));
}

function resetFilters() {
    document.getElementById('make').value = '';
    document.getElementById('model').value = '';
    document.getElementById('start_year').value = '';
    document.getElementById('end_year').value = '';
    document.getElementById('license_plate').value = '';
    document.getElementById('color').value = '';
    document.getElementById('start_date').value = '';
    document.getElementById('end_date').value = '';
    populateModels(); // Reset models dropdown
}

function saveCarData(carId) {
    const updatedCarData = {
        id: carId,
        date_time: document.getElementById(`info-date-time-${carId}`).value.replace('T', ' '),
        year: document.getElementById(`info-year-${carId}`).value || null,
        make: document.getElementById(`info-make-${carId}`).value || null,
        model: document.getElementById(`info-model-${carId}`).value || null,
        license_plate: document.getElementById(`info-license-plate-${carId}`).value || null,
        color: document.getElementById(`info-color-${carId}`).value || null,
        vin: document.getElementById(`info-vin-${carId}`).value || null,
        latitude: parseFloat(document.getElementById(`info-latitude-${carId}`).value) || null,
        longitude: parseFloat(document.getElementById(`info-longitude-${carId}`).value) || null
    };

    fetch('/api/update_car', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatedCarData)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            alert('Car data updated successfully.');
            fetchCars();
            infoWindow.close();
        } else {
            alert('Failed to update car data.');
        }
    })
    .catch(error => console.error('Error updating car data:', error));
}

function deleteCarData(carId) {
    if (confirm('Are you sure you want to delete this car?')) {
        fetch('/api/delete_car', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: carId })
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                alert('Car deleted successfully.');
                // Remove the marker from the map
                currentMarker.setMap(null);
                // Remove the marker from the markers array
                markers = markers.filter(marker => marker.carData.id !== carId);
                infoWindow.close();
            } else {
                alert('Failed to delete car.');
            }
        })
        .catch(error => console.error('Error deleting car data:', error));
    }
}
