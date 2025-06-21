import * as L from 'leaflet';

interface Property {
    id: string;
    title: string;
    price: number;
    currency: string;
    location_raw: string;
    full_address: string | null;
    latitude: number | null;
    longitude: number | null;
    description: string;
    bedrooms: number;
    bathrooms: number;
    areaSqFt: number;
    url: string;
    extracted_amenities: string[];
    scrapedAt: string; // ISO 8601 string
}

const map = L.map('map').setView([27.7172, 85.3240], 13); // Default to Kathmandu, Nepal

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

const propertiesDataPath = '../data/unique_properties.json'; // Path to your processed data

document.getElementById('loadProperties')?.addEventListener('click', loadProperties);

async function loadProperties() {
    try {
        const response = await fetch(propertiesDataPath);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const properties: Property[] = await response.json();
        console.log(`Loaded ${properties.length} properties.`);
        addMarkersToMap(properties);
    } catch (error) {
        console.error("Could not load properties:", error);
    }
}

function addMarkersToMap(properties: Property[]) {
    properties.forEach(property => {
        if (property.latitude && property.longitude) {
            const marker = L.marker([property.latitude, property.longitude]).addTo(map);
            marker.bindPopup(createPopupContent(property));
        }
    });
}

function createPopupContent(property: Property): string {
    const amenitiesList = property.extracted_amenities.length > 0
        ? `<li>Amenities: ${property.extracted_amenities.join(', ')}</li>`
        : '';
    const priceDisplay = property.price ? `${property.currency} ${property.price.toLocaleString()}` : 'N/A';
    const areaDisplay = property.areaSqFt ? `${property.areaSqFt} sqft` : 'N/A';

    return `
        <h3>${property.title}</h3>
        <p><strong>Price:</strong> ${priceDisplay}</p>
        <p><strong>Location:</strong> ${property.full_address || property.location_raw}</p>
        <ul>
            <li>Bedrooms: ${property.bedrooms || 'N/A'}</li>
            <li>Bathrooms: ${property.bathrooms || 'N/A'}</li>
            <li>Area: ${areaDisplay}</li>
            ${amenitiesList}
        </ul>
        <p>${property.description.substring(0, 150)}...</p>
        <a href="${property.url}" target="_blank">View Listing</a>
    `;
}
