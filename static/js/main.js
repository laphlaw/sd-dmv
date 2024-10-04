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
            populateStates();

            // Add event listeners to filter inputs to automatically apply filters
            const filterInputs = document.querySelectorAll('#filter-form input, #filter-form select');
            filterInputs.forEach(input => {
                input.addEventListener('change', function() {
                    fetchCars();
                    if (this.id === 'make') {
                        populateModels(); // Update models when make changes
                    }
                });
            });

            // Handle reset filters button
            document.getElementById('reset-filters').addEventListener('click', function() {
                resetFilters();
                fetchCars();
            });
        })
        .catch(error => console.error('Error fetching first car location:', error));
}

// Fetch and display cars based on filters
function fetchCars() {
    // Get filter values
    const make = document.getElementById('make').value;
    const model = document.getElementById('model').value;
    const start_year = document.getElementById('start_year').value;
    const end_year = document.getElementById('end_year').value;
    const state = document.getElementById('state').value;
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
    if (state) params.append('state', state);
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
            // Update car count
            document.getElementById('car-count').textContent = `Car Count: ${data.length}`;

            // Calculate unknown count
            let unknownCount = data.filter(car => !car.make || car.make === '').length;
            document.getElementById('unknown-count').textContent = `Unknown Count: ${unknownCount}`;
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

            // Correctly format the date/time for the datetime-local input
            let formattedDateTime = '';
            if (car.date_time) {
                // Create a new Date object from the car.date_time string
                let date = new Date(car.date_time);
                if (!isNaN(date.getTime())) {
                    // Adjust for timezone offset if necessary
                    let tzOffset = date.getTimezoneOffset() * 60000; // Offset in milliseconds
                    let localISOTime = new Date(date.getTime() - tzOffset).toISOString().slice(0, 16);
                    formattedDateTime = localISOTime;
                }
            }

            // Build the HTML content with current values
            contentDiv.innerHTML = `
                <h3><input type="text" id="info-title-${car.id}" value="${marker.title}" readonly></h3>
                <p>
                    <label for="info-license-plate-${car.id}">License Plate:</label>
                    <input type="text" id="info-license-plate-${car.id}" value="${car.license_plate || ''}">
                </p>
                <p>
                    <label for="info-state-${car.id}">State:</label>
                    <input type="text" id="info-state-${car.id}" value="${car.state || ''}">
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
                    <input type="datetime-local" id="info-date-time-${car.id}" value="${formattedDateTime}" readonly>
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
                <button type="button" id="refresh-car-data-${car.id}" class="refresh-button">Refresh</button>
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
                    deleteCarData(car.id, car.video_path);
                });

                // Refresh button
                document.getElementById(`refresh-car-data-${car.id}`).addEventListener('click', function() {
                    refreshCarData(car.id);
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
            makes.forEach((make, index) => {
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

function populateStates() {
    fetch('/api/states')
        .then(response => response.json())
        .then(states => {
            const stateSelect = document.getElementById('state');
            stateSelect.innerHTML = '<option value="">All</option>';
            states.forEach(state => {
                const option = document.createElement('option');
                option.value = state;
                option.textContent = state;
                stateSelect.appendChild(option);
            });
        })
        .catch(error => console.error('Error fetching states:', error));
}

function resetFilters() {
    document.getElementById('make').value = '';
    document.getElementById('model').value = '';
    document.getElementById('start_year').value = '';
    document.getElementById('end_year').value = '';
    document.getElementById('state').value = '';
    document.getElementById('license_plate').value = '';
    document.getElementById('color').value = '';
    document.getElementById('start_date').value = '';
    document.getElementById('end_date').value = '';
    populateModels(); // Reset models dropdown
}

function saveCarData(carId) {
    const updatedCarData = {
        id: carId,
        year: document.getElementById(`info-year-${carId}`).value || null,
        make: document.getElementById(`info-make-${carId}`).value || null,
        model: document.getElementById(`info-model-${carId}`).value || null,
        license_plate: document.getElementById(`info-license-plate-${carId}`).value || null,
        color: document.getElementById(`info-color-${carId}`).value || null,
        vin: document.getElementById(`info-vin-${carId}`).value || null,
        latitude: parseFloat(document.getElementById(`info-latitude-${carId}`).value) || null,
        longitude: parseFloat(document.getElementById(`info-longitude-${carId}`).value) || null,
        state: document.getElementById(`info-state-${carId}`).value || null
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
            // Optionally show a success message
            fetchCars();
            infoWindow.close();
        } else {
            alert('Failed to update car data.');
        }
    })
    .catch(error => console.error('Error updating car data:', error));
}

function deleteCarData(carId, videoPath) {
    if (confirm('Are you sure you want to delete this car?')) {
        fetch('/api/delete_car', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: carId, video_path: videoPath })
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                // Remove the marker from the map
                currentMarker.setMap(null);
                // Remove the marker from the markers array
                markers = markers.filter(marker => marker.carData.id !== carId);
                infoWindow.close();
                // Update car count
                document.getElementById('car-count').textContent = `Car Count: ${markers.length}`;
            } else {
                alert('Failed to delete car.');
            }
        })
        .catch(error => console.error('Error deleting car data:', error));
    }
}

function refreshCarData(carId) {
    const licensePlate = document.getElementById(`info-license-plate-${carId}`).value || null;
    const state = document.getElementById(`info-state-${carId}`).value || null;

    if (!licensePlate || !state) {
        alert('License plate and state are required to refresh car data.');
        return;
    }

    fetch('/api/refresh_car', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id: carId, license_plate: licensePlate, state: state })
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            // Update fields with new data
            document.getElementById(`info-year-${carId}`).value = result.year || '';
            document.getElementById(`info-make-${carId}`).value = result.make || '';
            document.getElementById(`info-model-${carId}`).value = result.model || '';
            document.getElementById(`info-vin-${carId}`).value = result.vin || '';
            document.getElementById(`info-state-${carId}`).value = result.state || '';
            // Update the marker title
            currentMarker.title = `${result.year} ${result.make} ${result.model}`;
            // Optionally, refresh the markers and car count
            fetchCars();
        } else {
            alert('Failed to refresh car data: ' + result.message);
        }
    })
    .catch(error => {
        console.error('Error refreshing car data:', error);
        alert('An error occurred while refreshing car data.');
    });
}

// Event listener for the "Unknown Count" clickable link
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the map when the DOM is fully loaded
    initMap();

    // Add event listener to the unknown count
    document.getElementById('unknown-count').addEventListener('click', function() {
        openUnknownModal();
    });
});

// Function to open the unknown cars modal
function openUnknownModal() {
    const modal = document.getElementById('unknown-modal');
    const closeButton = document.getElementById('modal-close');

    // Show the modal
    modal.style.display = 'block';

    // Fetch unknown cars and populate the table
    fetchUnknownCars();

    // Function to close the modal
    const closeModal = function() {
        modal.style.display = 'none';
        // Remove event listeners
        closeButton.removeEventListener('click', closeModal);
        window.removeEventListener('click', outsideClick);
        document.removeEventListener('keydown', keydownListener);
    };

    // Function to handle clicks outside the modal content
    const outsideClick = function(event) {
        if (event.target == modal) {
            closeModal();
        }
    };

    const keydownListener = function(event) {
        event = event || window.event;
        const key = event.key.toLowerCase();

        // Check if the event target is an input field
        if (event.target.tagName.toLowerCase() === 'input') {
            if (key === 'escape' || key === 'esc') {
                // Unfocus the input field
                event.target.blur();
                // Prevent default behavior and stop propagation
                event.preventDefault();
                event.stopPropagation();
            }
            // Do not handle other keys when input is focused
            return;
        }

        // If no input is focused, handle hotkeys
        if (key === 'v' || key === 'r' || key === 'd') {
            event.preventDefault(); // Prevent default behavior
        }

        if (key === 'v') {
            triggerReviewTopCar();
        } else if (key === 'r') {
            triggerRefreshTopCar();
        } else if (key === 'd') {
            triggerDeleteTopCar();
        } else if (key === 'escape' || key === 'esc') {
            // Do nothing when Escape is pressed and no input is focused
            event.preventDefault();
        }
    };

    // Close the modal when the close button is clicked
    closeButton.addEventListener('click', closeModal);

    // Close the modal when clicking outside the modal content
    window.addEventListener('click', outsideClick);

    // Add keydown event listener
    document.addEventListener('keydown', keydownListener);
}
// Function to fetch unknown cars and populate the table
function fetchUnknownCars() {
    fetch('/api/unknown_cars')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#unknown-cars-table tbody');
            tbody.innerHTML = ''; // Clear existing rows

            data.forEach(car => {
                const row = document.createElement('tr');

                // Store car ID and video path as data attributes
                row.setAttribute('data-car-id', car.id);
                row.setAttribute('data-video-path', car.video_path);

                // Editable fields
                const licensePlateCell = document.createElement('td');
                const licensePlateInput = document.createElement('input');
                licensePlateInput.type = 'text';
                licensePlateInput.value = car.license_plate || '';
                licensePlateInput.id = `modal-license-plate-${car.id}`;
                licensePlateCell.appendChild(licensePlateInput);

                const stateCell = document.createElement('td');
                const stateInput = document.createElement('input');
                stateInput.type = 'text';
                stateInput.value = car.state || '';
                stateInput.id = `modal-state-${car.id}`;
                stateCell.appendChild(stateInput);

                const yearCell = document.createElement('td');
                const yearInput = document.createElement('input');
                yearInput.type = 'number';
                yearInput.value = car.year || '';
                yearInput.id = `modal-year-${car.id}`;
                yearCell.appendChild(yearInput);

                const makeCell = document.createElement('td');
                const makeInput = document.createElement('input');
                makeInput.type = 'text';
                makeInput.value = car.make || '';
                makeInput.id = `modal-make-${car.id}`;
                makeCell.appendChild(makeInput);

                const modelCell = document.createElement('td');
                const modelInput = document.createElement('input');
                modelInput.type = 'text';
                modelInput.value = car.model || '';
                modelInput.id = `modal-model-${car.id}`;
                modelCell.appendChild(modelInput);

                // Actions
                const actionsCell = document.createElement('td');
                actionsCell.colSpan = 2; // Span two columns

                // Create a container for the buttons
                const buttonContainer = document.createElement('div');
                buttonContainer.className = 'button-container';

                // Review Button
                const reviewButton = document.createElement('button');
                reviewButton.textContent = 'Review';
                reviewButton.addEventListener('click', function() {
                    openVideoModal(car.video_path);
                });
                buttonContainer.appendChild(reviewButton);

                // Refresh Button
                const refreshButton = document.createElement('button');
                refreshButton.textContent = 'Refresh';
                refreshButton.addEventListener('click', function() {
                    modalRefreshCarData(car.id);
                });
                buttonContainer.appendChild(refreshButton);

                // Save Button
                const saveButton = document.createElement('button');
                saveButton.textContent = 'Save';
                saveButton.addEventListener('click', function() {
                    modalSaveCarData(car.id);
                });
                buttonContainer.appendChild(saveButton);

                // Delete Button
                const deleteButton = document.createElement('button');
                deleteButton.textContent = 'Delete';
                deleteButton.style.backgroundColor = 'red';
                deleteButton.style.color = 'white';
                deleteButton.addEventListener('click', function() {
                    modalDeleteCarData(car.id, car.video_path);
                });
                buttonContainer.appendChild(deleteButton);

                // Append the button container to the actions cell
                actionsCell.appendChild(buttonContainer);

                // Append cells to the row
                row.appendChild(licensePlateCell);
                row.appendChild(stateCell);
                row.appendChild(yearCell);
                row.appendChild(makeCell);
                row.appendChild(modelCell);
                row.appendChild(actionsCell);

                // Append row to the table body
                tbody.appendChild(row);
            });
        })
        .catch(error => console.error('Error fetching unknown cars:', error));
}

function openVideoModal(videoPath) {
    const modal = document.getElementById('video-modal');
    const closeButton = document.getElementById('video-modal-close');
    const videoSource = document.getElementById('car-video-source');
    const videoElement = document.getElementById('car-video');

    // Set the video source
    videoSource.src = `/videos/${videoPath}`;
    videoElement.load();

    // Show the modal
    modal.style.display = 'block';

    // Function to close the modal
    const closeModal = function() {
        modal.style.display = 'none';
        videoElement.pause();
        // Remove event listeners
        closeButton.removeEventListener('click', closeModal);
        window.removeEventListener('click', outsideClick);
        document.removeEventListener('keydown', keydownListener);

        // After closing the video modal, focus on the license plate input of the topmost row
        focusLicensePlateInput();
    };

    // Function to handle clicks outside the modal content
    const outsideClick = function(event) {
        if (event.target == modal) {
            closeModal();
        }
    };

    // Function to handle keydown events
    const keydownListener = function(event) {
        event = event || window.event;
        const key = event.key.toLowerCase();

        if (key === ' ') { // Spacebar pressed
            event.preventDefault(); // Prevent scrolling
            if (videoElement.paused) {
                videoElement.play();
            } else {
                videoElement.pause();
            }
            event.stopPropagation(); // Prevent event from reaching other handlers
        } else if (key === 'escape' || key === 'esc') {
            event.preventDefault();
            closeModal();
            event.stopPropagation(); // Prevent event from reaching other handlers
        }
    };

    // Close the modal when the close button is clicked
    closeButton.addEventListener('click', closeModal);

    // Close the modal when clicking outside the modal content
    window.addEventListener('click', outsideClick);

    // Add keydown event listener
    document.addEventListener('keydown', keydownListener);
}

// Function to refresh car data from the modal
function modalRefreshCarData(carId) {
    const licensePlate = document.getElementById(`modal-license-plate-${carId}`).value || null;
    const state = document.getElementById(`modal-state-${carId}`).value || null;

    if (!licensePlate || !state) {
        alert('License plate and state are required to refresh car data.');
        return;
    }

    fetch('/api/refresh_car', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id: carId, license_plate: licensePlate, state: state })
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            // Update fields with new data
            document.getElementById(`modal-year-${carId}`).value = result.year || '';
            document.getElementById(`modal-make-${carId}`).value = result.make || '';
            document.getElementById(`modal-model-${carId}`).value = result.model || '';
            // Optionally, refresh counts and markers
            fetchCars();
            fetchUnknownCars();
        } else {
            alert('Failed to refresh car data: ' + result.message);
        }
    })
    .catch(error => {
        console.error('Error refreshing car data:', error);
        alert('An error occurred while refreshing car data.');
    });
}

// Function to save manually edited car data from the modal
function modalSaveCarData(carId) {
    const updatedCarData = {
        id: carId,
        year: document.getElementById(`modal-year-${carId}`).value || null,
        make: document.getElementById(`modal-make-${carId}`).value || null,
        model: document.getElementById(`modal-model-${carId}`).value || null,
        license_plate: document.getElementById(`modal-license-plate-${carId}`).value || null,
        state: document.getElementById(`modal-state-${carId}`).value || null,
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
            // Optionally show a success message
            // Update counts and markers
            fetchCars();
            fetchUnknownCars();
        } else {
            alert('Failed to save car data.');
        }
    })
    .catch(error => console.error('Error saving car data:', error));
}

// Function to delete a car and its video file from the modal
function modalDeleteCarData(carId, videoPath) {
    if (confirm('Are you sure you want to delete this car? This action cannot be undone.')) {
        fetch('/api/delete_car', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: carId, video_path: videoPath })
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                // Update counts and markers
                fetchCars();
                fetchUnknownCars();
            } else {
                alert('Failed to delete car.');
            }
        })
        .catch(error => console.error('Error deleting car data:', error));
    }
}

function triggerReviewTopCar() {
    const firstCarRow = document.querySelector('#unknown-cars-table tbody tr');
    if (firstCarRow) {
        const videoPath = firstCarRow.getAttribute('data-video-path');
        if (videoPath) {
            openVideoModal(videoPath);
        } else {
            alert('No video available for the top car.');
        }
    } else {
        alert('No unknown cars available.');
    }
}

function triggerRefreshTopCar() {
    const firstCarRow = document.querySelector('#unknown-cars-table tbody tr');
    if (firstCarRow) {
        const carId = firstCarRow.getAttribute('data-car-id');
        const licensePlateInput = document.getElementById(`modal-license-plate-${carId}`);
        const stateInput = document.getElementById(`modal-state-${carId}`);
        const licensePlate = licensePlateInput ? licensePlateInput.value : null;
        const state = stateInput ? stateInput.value : null;

        if (!licensePlate || !state) {
            alert('License plate and state are required to refresh car data.');
            return;
        }

        fetch('/api/refresh_car', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: carId, license_plate: licensePlate, state: state })
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                // Update fields with new data
                document.getElementById(`modal-year-${carId}`).value = result.year || '';
                document.getElementById(`modal-make-${carId}`).value = result.make || '';
                document.getElementById(`modal-model-${carId}`).value = result.model || '';
                // Refresh counts and markers
                fetchCars();
                fetchUnknownCars();
            } else {
                alert('Failed to refresh car data: ' + result.message);
            }
        })
        .catch(error => {
            console.error('Error refreshing car data:', error);
            alert('An error occurred while refreshing car data.');
        });
    } else {
        alert('No unknown cars available.');
    }
}

function focusLicensePlateInput() {
    const firstCarRow = document.querySelector('#unknown-cars-table tbody tr');
    if (firstCarRow) {
        const carId = firstCarRow.getAttribute('data-car-id');
        const licensePlateInput = document.getElementById(`modal-license-plate-${carId}`);
        if (licensePlateInput) {
            licensePlateInput.focus();
            licensePlateInput.select();
        }
    }
}

function triggerDeleteTopCar() {
    const firstCarRow = document.querySelector('#unknown-cars-table tbody tr');
    if (firstCarRow) {
        const carId = firstCarRow.getAttribute('data-car-id');
        const videoPath = firstCarRow.getAttribute('data-video-path');

        if (confirm('Are you sure you want to delete this car? This action cannot be undone.')) {
            fetch('/api/delete_car', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: carId, video_path: videoPath })
            })
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    // Update counts and markers
                    fetchCars();
                    fetchUnknownCars();
                } else {
                    alert('Failed to delete car.');
                }
            })
            .catch(error => console.error('Error deleting car data:', error));
        }
    } else {
        alert('No unknown cars available.');
    }
}