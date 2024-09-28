// static/js/main.js

let map;
let markers = [];

function initMap() {
    // Initialize the map centered on a default location
    const defaultLocation = { lat: 37.7749, lng: -122.4194 }; // Example: San Francisco
    map = new google.maps.Map(document.getElementById('map'), {
        center: defaultLocation,
        zoom: 12,
    });

    // Load initial data
    fetchCars();

    // Add event listener to the filter form
    document.getElementById('filter-form').addEventListener('submit', function(event) {
        event.preventDefault();
        fetchCars();
    });
}

function fetchCars() {
    // Get filter values
    const make = document.getElementById('make').value;
    const model = document.getElementById('model').value;
    const year = document.getElementById('year').value;
    const license_plate = document.getElementById('license_plate').value;
    const color = document.getElementById('color').value;
    const start_date = document.getElementById('start_date').value;
    const end_date = document.getElementById('end_date').value;

    // Build query parameters
    const params = new URLSearchParams();

    if (make) params.append('make', make);
    if (model) params.append('model', model);
    if (year) params.append('year', year);
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

        const infoWindow = new google.maps.InfoWindow();

        marker.addListener('click', function() {
            // Populate the info window content
            document.getElementById('info-title').textContent = marker.title;
            document.getElementById('info-details').innerHTML = `
                <p>License Plate: ${car.license_plate}</p>
                <p>VIN: ${car.vin}</p>
                <p>Color: ${car.color}</p>
                <p>Date/Time: ${car.date_time}</p>
            `;
            document.getElementById('video-source').src = '/videos/' + car.video_path;
            document.getElementById('info-video').load();

            // Set the content of the info window
            infoWindow.setContent(document.getElementById('info-window-content').innerHTML);
            infoWindow.open(map, marker);
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
