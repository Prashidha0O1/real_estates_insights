package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/PuerkitoBio/goquery"
)

// Property represents a single real estate listing.
type Property struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	Price       float64   `json:"price"`
	Currency    string    `json:"currency"`
	Location    string    `json:"location"`
	Description string    `json:"description"`
	Bedrooms    int       `json:"bedrooms"`
	Bathrooms   int       `json:"bathrooms"`
	AreaSqFt    float64   `json:"areaSqFt"`
	URL         string    `json:"url"`
	ScrapedAt   time.Time `json:"scrapedAt"`
	Source      string    `json:"source"` // Track which website the property came from
}

// ScraperConfig holds configuration for the scraper
type ScraperConfig struct {
	BaseURL       string
	SearchPath    string
	PagesToScrape int
	Source        string
}

// WebsiteConfig defines how to scrape different websites
type WebsiteConfig struct {
	Selector     string
	TitleSelect  string
	PriceSelect  string
	LocationSelect string
	URLSelect    string
	BedroomRegex string
	BathroomRegex string
	AreaRegex    string
	PriceRegex   string
}

func main() {
	// Define multiple websites to scrape
	websites := []ScraperConfig{
		{
			BaseURL:       "https://www.realestateinnepal.com/",
			SearchPath:    "/search-result/?location=kathmandu",
			PagesToScrape: 2,
			Source:        "realestateinnepal.com",
		},
		{
			BaseURL:       "https://www.realestate.com.au/international/ae/dubai",
			SearchPath:    "",
			PagesToScrape: 3,
			Source:        "realestate.com.au/dubai",
		},
	}

	allProperties := make(chan Property)
	var wg sync.WaitGroup
	var mu sync.Mutex
	var propertiesCollected []Property

	// Collect properties from channel
	go func() {
		for prop := range allProperties {
			mu.Lock()
			propertiesCollected = append(propertiesCollected, prop)
			mu.Unlock()
		}
	}()

	// Scrape each website
	for _, config := range websites {
		wg.Add(1)
		go func(cfg ScraperConfig) {
			defer wg.Done()
			log.Printf("Starting to scrape: %s", cfg.Source)
			
			if cfg.Source == "realestate.com.au/dubai" {
				scrapeDubaiProperties(cfg, allProperties)
			} else {
				scrapeNepalProperties(cfg, allProperties)
			}
		}(config)
	}

	wg.Wait()
	close(allProperties)

	time.Sleep(1 * time.Second)

	// Save to file
	outputPath := "../data/properties.json"
	file, err := json.MarshalIndent(propertiesCollected, "", "  ")
	if err != nil {
		log.Fatalf("Failed to marshal properties: %v", err)
	}

	err = saveToFile(outputPath, file)
	if err != nil {
		log.Fatalf("Failed to save properties to file: %v", err)
	}
	log.Printf("Scraping complete. Saved %d properties to %s", len(propertiesCollected), outputPath)
}

func scrapeDubaiProperties(config ScraperConfig, allProperties chan<- Property) {
	url := config.BaseURL
	log.Printf("Scraping Dubai properties from: %s", url)
	
	res, err := http.Get(url)
	if err != nil {
		log.Printf("Failed to fetch Dubai URL %s: %v", url, err)
		return
	}
	defer res.Body.Close()

	if res.StatusCode != 200 {
		log.Printf("Received non-200 status code for Dubai: %d %s", res.StatusCode, res.Status)
		return
	}

	doc, err := goquery.NewDocumentFromReader(res.Body)
	if err != nil {
		log.Printf("Failed to parse Dubai HTML: %v", err)
		return
	}

	// Based on the realestate.com.au Dubai page structure
	doc.Find("a[href*='/international/ae/']").Each(func(i int, s *goquery.Selection) {
		// Extract property URL
		propertyURL, exists := s.Attr("href")
		if !exists || !strings.Contains(propertyURL, "/international/ae/") {
			return
		}
		
		// Make URL absolute
		if !strings.HasPrefix(propertyURL, "http") {
			propertyURL = "https://www.realestate.com.au" + propertyURL
		}

		// Extract title from the link text or nearby elements
		title := strings.TrimSpace(s.Text())
		if title == "" {
			title = s.Find("h3, h4, .property-title").First().Text()
		}

		// Extract price - look for price elements
		priceText := s.Find("[class*='price'], .price, strong").First().Text()
		price, currency := parseDubaiPrice(priceText)

		// Extract location
		location := extractDubaiLocation(s)

		// Extract bedrooms and area from the text
		fullText := s.Text()
		bedrooms := extractBedrooms(fullText)
		area := extractDubaiArea(fullText)

		// Generate unique ID
		id := fmt.Sprintf("dubai-%d-%d", time.Now().UnixNano(), i)

		prop := Property{
			ID:          id,
			Title:       title,
			Price:       price,
			Currency:    currency,
			Location:    location,
			Description: fmt.Sprintf("%s - %s", title, location),
			Bedrooms:    bedrooms,
			Bathrooms:   0, // Not easily extractable from this view
			AreaSqFt:    area,
			URL:         propertyURL,
			ScrapedAt:   time.Now(),
			Source:      config.Source,
		}

		// Only add if we have meaningful data
		if title != "" && price > 0 {
			allProperties <- prop
		}
	})
}

func scrapeNepalProperties(config ScraperConfig, allProperties chan<- Property) {
	for i := 1; i <= config.PagesToScrape; i++ {
		url := fmt.Sprintf("%s%s%d", config.BaseURL, config.SearchPath, i)
		log.Printf("Scraping Nepal page: %s", url)
		
		res, err := http.Get(url)
		if err != nil {
			log.Printf("Failed to fetch Nepal URL %s: %v", url, err)
			continue
		}
		defer res.Body.Close()

		if res.StatusCode != 200 {
			log.Printf("Received non-200 status code for Nepal: %d %s", res.StatusCode, res.Status)
			continue
		}

		doc, err := goquery.NewDocumentFromReader(res.Body)
		if err != nil {
			log.Printf("Failed to parse Nepal HTML: %v", err)
			continue
		}

		// Based on the actual website structure from realestateinnepal.com
		doc.Find("article, .property-item, .listing-item").Each(func(i int, s *goquery.Selection) {
			// Extract property ID from code or generate one
			codeElement := s.Find("code, .property-code").First()
			id := strings.TrimSpace(codeElement.Text())
			if id == "" {
				id = fmt.Sprintf("nepal-%d-%d", time.Now().UnixNano(), i)
			}

			// Extract title
			titleElement := s.Find("h3, h4, .property-title").First()
			title := strings.TrimSpace(titleElement.Text())

			// Extract price
			priceElement := s.Find(".price, [class*='price'], strong").First()
			priceStr := strings.TrimSpace(priceElement.Text())

			// Extract location
			locationElement := s.Find(".location, [class*='location'], p").First()
			location := strings.TrimSpace(locationElement.Text())

			// Extract description (might be in title or location if no separate description)
			description := title
			if location != "" && location != title {
				description = fmt.Sprintf("%s - %s", title, location)
			}

			// Extract URL
			linkElement := s.Find("a").First()
			propertyURL, _ := linkElement.Attr("href")
			if propertyURL != "" && !strings.HasPrefix(propertyURL, "http") {
				propertyURL = "https://www.realestateinnepal.com" + propertyURL
			}

			// Parse price and currency
			price, currency := parsePrice(priceStr)

			// Extract bedrooms and bathrooms from the property details
			detailsText := s.Text()
			bedrooms := extractBedrooms(detailsText)
			bathrooms := extractBathrooms(detailsText)
			area := extractArea(detailsText)

			prop := Property{
				ID:          id,
				Title:       title,
				Price:       price,
				Currency:    currency,
				Location:    location,
				Description: description,
				Bedrooms:    bedrooms,
				Bathrooms:   bathrooms,
				AreaSqFt:    area,
				URL:         propertyURL,
				ScrapedAt:   time.Now(),
				Source:      config.Source,
			}
			allProperties <- prop
		})

		time.Sleep(2 * time.Second) // Be respectful to the server
	}
}

// Helper functions for Dubai properties
func parseDubaiPrice(priceStr string) (float64, string) {
	// Handle formats like "AUD $393,161" or "AED 934,000"
	priceStr = strings.ReplaceAll(priceStr, ",", "")
	re := regexp.MustCompile(`([A-Z]{3})\s*\$?\s*([\d.]+)`)
	matches := re.FindStringSubmatch(priceStr)
	if len(matches) > 2 {
		currency := strings.TrimSpace(matches[1])
		price, err := strconv.ParseFloat(matches[2], 64)
		if err == nil {
			return price, currency
		}
	}
	return 0.0, ""
}

func extractDubaiLocation(s *goquery.Selection) string {
	// Look for location in various elements
	location := s.Find(".location, [class*='location'], .address").First().Text()
	if location == "" {
		// Try to extract from the full text
		fullText := s.Text()
		// Look for patterns like "Dubai, Dubai, Dubai" or specific areas
		re := regexp.MustCompile(`([A-Za-z\s]+),\s*Dubai`)
		matches := re.FindStringSubmatch(fullText)
		if len(matches) > 1 {
			location = strings.TrimSpace(matches[1])
		}
	}
	return strings.TrimSpace(location)
}

func extractDubaiArea(text string) float64 {
	// Look for area in m2 format
	re := regexp.MustCompile(`(\d+(?:\.\d+)?)\s*m2`)
	matches := re.FindStringSubmatch(text)
	if len(matches) > 1 {
		if area, err := strconv.ParseFloat(matches[1], 64); err == nil {
			// Convert m2 to sqft (1 m2 = 10.764 sqft)
			return area * 10.764
		}
	}
	return 0.0
}

// Helper functions to extract property details from text
func extractBedrooms(text string) int {
	re := regexp.MustCompile(`(\d+)\s*Bed`)
	matches := re.FindStringSubmatch(text)
	if len(matches) > 1 {
		if beds, err := strconv.Atoi(matches[1]); err == nil {
			return beds
		}
	}
	return 0
}

func extractBathrooms(text string) int {
	re := regexp.MustCompile(`(\d+)\s*Bath`)
	matches := re.FindStringSubmatch(text)
	if len(matches) > 1 {
		if baths, err := strconv.Atoi(matches[1]); err == nil {
			return baths
		}
	}
	return 0
}

func extractArea(text string) float64 {
	re := regexp.MustCompile(`(\d+(?:\.\d+)?)\s*sqft`)
	matches := re.FindStringSubmatch(text)
	if len(matches) > 1 {
		if area, err := strconv.ParseFloat(matches[1], 64); err == nil {
			return area
		}
	}
	return 0.0
}

// parsePrice attempts to extract price and currency from a string.
func parsePrice(priceStr string) (float64, string) {
	priceStr = strings.ReplaceAll(priceStr, ",", "") // Remove commas
	re := regexp.MustCompile(`([A-Z$€£]+)?\s*([\d.]+)`)
	matches := re.FindStringSubmatch(priceStr)
	if len(matches) > 2 {
		currency := strings.TrimSpace(matches[1])
		price, err := strconv.ParseFloat(matches[2], 64)
		if err == nil {
			return price, currency
		}
	}
	return 0.0, ""
}

func saveToFile(filepath string, data []byte) error {
	return os.WriteFile(filepath, data, 0644)
}