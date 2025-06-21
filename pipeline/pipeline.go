package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

func runCommand(name string, args ...string) error {
	cmd := exec.Command(name, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	log.Printf("Running command: %s %v", name, args)
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("command '%s %v' failed: %w", name, args, err)
	}
	log.Printf("Command '%s %v' completed successfully.", name, args)
	return nil
}

func main() {
	log.Println("Starting Real Estate Insights Data Pipeline...")

	// Define paths relative to the pipeline.go executable
	baseDir, err := os.Getwd()
	if err != nil {
		log.Fatalf("Failed to get current working directory: %v", err)
	}
	// Adjust baseDir to be the root of the project if running from pipeline/
	// Assuming pipeline.go is in real-estate-insights/pipeline/
	projectRoot := filepath.Join(baseDir, "..") 

	extractPath := filepath.Join(projectRoot, "processing", "extract.py")
	linkagePath := filepath.Join(projectRoot, "processing", "linkage.py")
	ragPath := filepath.Join(projectRoot, "processing", "rag.py")
	knowledgeGraphPath := filepath.Join(projectRoot, "processing", "knowledge_graph.py")

	// 1. Run Scraper
	log.Println("--- Step 1: Running Scraper ---")
	// Run the scraper from its directory
	scraperDir := filepath.Join(projectRoot, "scraper")
	cmd := exec.Command("go", "run", "scraper.go")
	cmd.Dir = scraperDir
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		log.Fatalf("Scraper failed: %v", err)
	}
	log.Println("Scraper completed.")
	time.Sleep(1 * time.Second) // Small delay for file system writes

	// 2. Run Data Extraction
	log.Println("--- Step 2: Running Data Extraction ---")
	if err := runCommand("python", extractPath); err != nil {
		log.Fatalf("Data Extraction failed: %v", err)
	}
	log.Println("Data Extraction completed.")
	time.Sleep(1 * time.Second)

	// 3. Run Record Linkage
	log.Println("--- Step 3: Running Record Linkage ---")
	if err := runCommand("python", linkagePath); err != nil {
		log.Fatalf("Record Linkage failed: %v", err)
	}
	log.Println("Record Linkage completed.")
	time.Sleep(1 * time.Second)

	// 4. Run Knowledge Graph Generation
	log.Println("--- Step 4: Running Knowledge Graph Generation ---")
	if err := runCommand("python", knowledgeGraphPath); err != nil {
		log.Fatalf("Knowledge Graph Generation failed: %v", err)
	}
	log.Println("Knowledge Graph Generation completed.")
	time.Sleep(1 * time.Second)

	// 5. Run RAG System
	log.Println("--- Step 5: Running RAG System ---")
	if err := runCommand("python", ragPath); err != nil {
		log.Fatalf("RAG System failed: %v", err)
	}
	log.Println("RAG System completed.")
	time.Sleep(1 * time.Second)

	log.Println("Real Estate Insights Data Pipeline finished successfully!")
}