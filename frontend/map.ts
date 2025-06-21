import * as L from 'leaflet';

// Extend Leaflet types to include marker cluster
declare module 'leaflet' {
    function markerClusterGroup(options?: any): any;
}

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

// Initialize map
const map = L.map('map').setView([27.7172, 85.3240], 13); // Default to Kathmandu, Nepal

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Create marker cluster group for better performance and less cluttering
const markerClusterGroup = (L as any).markerClusterGroup({
    chunkedLoading: true,
    maxClusterRadius: 50,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true
});

map.addLayer(markerClusterGroup);

const propertiesDataPath = '../data/unique_properties.json'; // Path to your processed data
const loadButton = document.getElementById('loadProperties') as HTMLButtonElement;
const infoPanel = document.querySelector('.info-panel') as HTMLElement;

// Add loading state to button
function setLoadingState(loading: boolean) {
    if (loadButton) {
        loadButton.disabled = loading;
        loadButton.textContent = loading ? 'Loading...' : 'Load Properties';
    }
}

// Add status message to info panel
function updateStatus(message: string, isError = false) {
    const statusDiv = document.getElementById('status') || document.createElement('div');
    statusDiv.id = 'status';
    statusDiv.textContent = message;
    statusDiv.style.color = isError ? 'red' : 'green';
    statusDiv.style.marginTop = '10px';
    
    if (!document.getElementById('status')) {
        infoPanel.appendChild(statusDiv);
    }
}

// Sample data for testing if no data file exists
const sampleProperties: Property[] = [
    {
        id: "1",
        title: "Modern Apartment in Kathmandu",
        price: 25000000,
        currency: "NPR",
        location_raw: "Thamel, Kathmandu",
        full_address: "Thamel, Kathmandu, Nepal",
        latitude: 27.7172,
        longitude: 85.3240,
        description: "Beautiful modern apartment in the heart of Thamel with all amenities.",
        bedrooms: 2,
        bathrooms: 2,
        areaSqFt: 1200,
        url: "#",
        extracted_amenities: ["Parking", "Garden", "Security"],
        scrapedAt: new Date().toISOString()
    },
    {
        id: "2",
        title: "Luxury Villa in Lalitpur",
        price: 45000000,
        currency: "NPR",
        location_raw: "Patan, Lalitpur",
        full_address: "Patan, Lalitpur, Nepal",
        latitude: 27.6766,
        longitude: 85.3149,
        description: "Spacious luxury villa with garden and parking space.",
        bedrooms: 4,
        bathrooms: 3,
        areaSqFt: 2500,
        url: "#",
        extracted_amenities: ["Garden", "Parking", "Security", "Swimming Pool"],
        scrapedAt: new Date().toISOString()
    }
];

loadButton?.addEventListener('click', loadProperties);

async function loadProperties() {
    setLoadingState(true);
    updateStatus('Loading properties...');
    
    try {
        // Clear existing markers
        markerClusterGroup.clearLayers();
        
        const response = await fetch(propertiesDataPath);
        let properties: Property[];
        
        if (!response.ok) {
            console.warn(`Could not load data file: ${response.status}. Using sample data.`);
            properties = sampleProperties;
            updateStatus('Using sample data (data file not found)', true);
        } else {
            properties = await response.json();
            updateStatus(`Loaded ${properties.length} properties successfully.`);
        }
        
        console.log(`Processing ${properties.length} properties.`);
        addMarkersToMap(properties);
        
    } catch (error) {
        console.error("Error loading properties:", error);
        updateStatus('Error loading properties. Using sample data.', true);
        
        // Use sample data as fallback
        addMarkersToMap(sampleProperties);
    } finally {
        setLoadingState(false);
    }
}

function addMarkersToMap(properties: Property[]) {
    let validProperties = 0;
    
    properties.forEach(property => {
        if (property.latitude && property.longitude) {
            const marker = L.marker([property.latitude, property.longitude]);
            marker.bindPopup(createPopupContent(property));
            markerClusterGroup.addLayer(marker);
            validProperties++;
        }
    });
    
    console.log(`Added ${validProperties} markers to map.`);
    
    // Fit map to show all markers if we have any
    if (validProperties > 0) {
        map.fitBounds(markerClusterGroup.getBounds());
    }
}

function createPopupContent(property: Property): string {
    const amenitiesList = property.extracted_amenities.length > 0
        ? `<li><strong>Amenities:</strong> ${property.extracted_amenities.join(', ')}</li>`
        : '';
    const priceDisplay = property.price ? `${property.currency} ${property.price.toLocaleString()}` : 'N/A';
    const areaDisplay = property.areaSqFt ? `${property.areaSqFt} sqft` : 'N/A';

    return `
        <div style="max-width: 300px;">
            <h3 style="margin: 0 0 10px 0; color: #333;">${property.title}</h3>
            <p style="margin: 5px 0;"><strong>Price:</strong> ${priceDisplay}</p>
            <p style="margin: 5px 0;"><strong>Location:</strong> ${property.full_address || property.location_raw}</p>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li><strong>Bedrooms:</strong> ${property.bedrooms || 'N/A'}</li>
                <li><strong>Bathrooms:</strong> ${property.bathrooms || 'N/A'}</li>
                <li><strong>Area:</strong> ${areaDisplay}</li>
                ${amenitiesList}
            </ul>
            <p style="margin: 10px 0; font-size: 0.9em; color: #666;">
                ${property.description.substring(0, 150)}${property.description.length > 150 ? '...' : ''}
            </p>
            <a href="${property.url}" target="_blank" style="color: #007bff; text-decoration: none;">View Listing →</a>
        </div>
    `;
}
