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
}

// ScraperConfig holds configuration for the scraper
type ScraperConfig struct {
	BaseURL    string
	SearchPath string
	PagesToScrape int
}

func main() {
	config := ScraperConfig{
		BaseURL:    "https://www.realestateinnepal.com/", 
		SearchPath: "/search-result/?location=kathmandu",
		PagesToScrape: 2, 
	}

	allProperties := make(chan Property)
	var wg sync.WaitGroup
	var mu sync.Mutex 
	var propertiesCollected []Property

	
	go func() {
		for prop := range allProperties {
			mu.Lock()
			propertiesCollected = append(propertiesCollected, prop)
			mu.Unlock()
		}
	}()

	for i := 1; i <= config.PagesToScrape; i++ {
		wg.Add(1)
		go func(page int) {
			defer wg.Done()
			url := fmt.Sprintf("%s%s%d", config.BaseURL, config.SearchPath, page)
			log.Printf("Scraping page: %s", url)
			properties, err := scrapePage(url)
			if err != nil {
				log.Printf("Error scraping page %d: %v", page, err)
				return
			}
			for _, p := range properties {
				allProperties <- p
			}
		}(i)
		time.Sleep(2 * time.Second) 
	}

	wg.Wait()
	close(allProperties)

	
	time.Sleep(1 * time.Second)

	
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

func scrapePage(url string) ([]Property, error) {
	res, err := http.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch URL %s: %w", url, err)
	}
	defer res.Body.Close()

	if res.StatusCode != 200 {
		return nil, fmt.Errorf("received non-200 status code: %d %s", res.StatusCode, res.Status)
	}

	doc, err := goquery.NewDocumentFromReader(res.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	var properties []Property
	
	// Based on the actual website structure from realestateinnepal.com
	doc.Find("article, .property-item, .listing-item").Each(func(i int, s *goquery.Selection) {
		// Extract property ID from code or generate one
		codeElement := s.Find("code, .property-code").First()
		id := strings.TrimSpace(codeElement.Text())
		if id == "" {
			id = fmt.Sprintf("property-%d-%d", time.Now().UnixNano(), i)
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
		}
		properties = append(properties, prop)
	})

	return properties, nil
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