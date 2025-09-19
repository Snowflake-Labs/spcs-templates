package main

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"sync/atomic"
)

const (
	srcDir  = "/mnt/stage1"
	dstDir  = "/mnt/block1/part1"
	workers = 200
)

// copyFile copies a single file from src to dst using higher-level operations
func copyFile(src, dst string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	return os.WriteFile(dst, data, 0644)
}

// worker processes a slice of files
func worker(id int, files []string, copiedCount *int64, wg *sync.WaitGroup) {
	defer wg.Done()

	localCopied := 0
	fmt.Printf("Worker %d processing %d files\n", id, len(files))

	for _, filename := range files {
		srcPath := filepath.Join(srcDir, filename)
		dstPath := filepath.Join(dstDir, filename)

		if err := copyFile(srcPath, dstPath); err == nil {
			localCopied++
		} else {
			fmt.Printf("Error copying file %s: %v\n", filename, err)
		}
	}

	atomic.AddInt64(copiedCount, int64(localCopied))
}

// hasValidUUID checks if filename contains a valid UUID pattern
func hasValidUUID(filename string) bool {
	// UUID pattern: 8-4-4-4-12 hex characters with hyphens
	uuidPattern := regexp.MustCompile(`[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`)
	return uuidPattern.MatchString(filename)
}

func main() {
	// Create destination directory
	if err := os.MkdirAll(dstDir, 0755); err != nil {
		fmt.Printf("Error creating destination directory: %v\n", err)
		os.Exit(1)
	}

	// Get all .dat files with UUID validation
	fmt.Println("Getting file list...")

	entries, err := os.ReadDir(srcDir)
	if err != nil {
		fmt.Printf("Error reading source directory: %v\n", err)
		os.Exit(1)
	}

	var validFiles []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		filename := entry.Name()
		if strings.HasPrefix(filename, "file_") &&
			strings.HasSuffix(filename, ".dat") &&
			hasValidUUID(filename) {
			validFiles = append(validFiles, filename)
		}
	}

	fmt.Printf("Found %d valid files with UUIDs to copy\n", len(validFiles))

	if len(validFiles) == 0 {
		fmt.Println("No files to copy")
		return
	}

	// Split files evenly across workers
	filesPerWorker := len(validFiles) / workers
	var wg sync.WaitGroup
	var copiedCount int64

	for i := 0; i < workers; i++ {
		startIdx := i * filesPerWorker
		var endIdx int

		if i == workers-1 { // Last worker gets any remaining files
			endIdx = len(validFiles)
		} else {
			endIdx = (i + 1) * filesPerWorker
		}

		if startIdx < len(validFiles) {
			workerFiles := validFiles[startIdx:endIdx]
			if len(workerFiles) > 0 {
				wg.Add(1)
				go worker(i+1, workerFiles, &copiedCount, &wg)
			}
		}
	}

	// Wait for all workers to complete
	wg.Wait()

	fmt.Printf("Copied %d files\n", copiedCount)
}
