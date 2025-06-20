package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/PuerkitoBio/goquery"
)

// Property represents a single real estate listing.
type Property struct {
	ID          string  `json:"id"`
	Title       string  `json:"title"`
	Price       float66 `json:"price"`
	Currency    string  `json:"currency"`
	Location    string  `json:"location"`
	Description string  `json:"description"`
	Bedrooms    int     `json:"bedrooms"`
	Bathrooms   int     `json:"bathrooms"`
	AreaSqFt    float64 `json:"areaSqFt"`
	URL         string  `json:"url"`
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
		BaseURL:    "", 
		SearchPath: "/search?q=property&page=",
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
	doc.Find(".row").Each(func(i int, s *goquery.Selection) {
		id, _ := s.Attr("data-id")
		if id == "" {
			id = fmt.Sprintf("property-%d-%d", time.Now().UnixNano(), i) // Fallback ID
		}

		title := strings.TrimSpace(s.Find(".listing-title a").Text())
		priceStr := strings.TrimSpace(s.Find(".listing-price").Text())
		location := strings.TrimSpace(s.Find(".listing-location").Text())
		description := strings.TrimSpace(s.Find(".listing-description").Text())
		propertyURL, _ := s.Find(".listing-title a").Attr("href")
		if !strings.HasPrefix(propertyURL, "http") {
			propertyURL = "https://www.example-real-estate.com" + propertyURL // Make absolute
		}

		price, currency := parsePrice(priceStr)
		bedrooms, _ := strconv.Atoi(strings.TrimSpace(s.Find(".listing-beds").Text()))
		bathrooms, _ := strconv.Atoi(strings.TrimSpace(s.Find(".listing-baths").Text()))
		areaStr := strings.TrimSpace(s.Find(".listing-area").Text())
		area, _ := strconv.ParseFloat(strings.TrimSuffix(areaStr, " sqft"), 64)

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