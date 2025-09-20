package main

import (
	"crypto/rand"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"time"

	"github.com/google/uuid"
)

const (
	stage1Dir       = "/mnt/stage1"
	stage2Dir       = "/mnt/stage2"
	totalWorkers    = 100
	workersPerStage = 50
	fileSize        = 15 * 1024 * 1024 // 15MB
	filesToGenerate = 5000             // Total files to generate per stage
)

// generateRandomData creates a byte slice of the specified size with random data
func generateRandomData(size int) ([]byte, error) {
	data := make([]byte, size)
	_, err := rand.Read(data)
	if err != nil {
		return nil, err
	}
	return data, nil
}

// writeFile creates a 5MB file with UUID name at the specified directory
func writeFile(dir string) error {
	// Generate UUID for filename
	fileUUID := uuid.New()
	filename := fmt.Sprintf("%s.15MB", fileUUID.String())
	filepath := filepath.Join(dir, filename)

	// Generate 5MB of random data
	data, err := generateRandomData(fileSize)
	if err != nil {
		return err
	}

	// Write file
	return os.WriteFile(filepath, data, 0644)
}

// fileWorker generates files in the specified directory
func fileWorker(id int, dir string, filesPerWorker int, successCount *int64, wg *sync.WaitGroup) {
	defer wg.Done()

	localSuccess := 0
	fmt.Printf("Worker %d starting - generating %d files in %s\n", id, filesPerWorker, dir)

	for i := 0; i < filesPerWorker; i++ {
		if err := writeFile(dir); err != nil {
			fmt.Printf("Worker %d error writing file %d: %v\n", id, i+1, err)
		} else {
			localSuccess++
		}

		// Progress update every 50 files
		if (i+1)%50 == 0 {
			fmt.Printf("Worker %d: %d/%d files completed\n", id, i+1, filesPerWorker)
		}
	}

	atomic.AddInt64(successCount, int64(localSuccess))
	fmt.Printf("Worker %d completed - successfully wrote %d files\n", id, localSuccess)
}

func main() {
	fmt.Println("Starting 15MB file generation...")
	fmt.Printf("Configuration:\n")
	fmt.Printf("- Total workers: %d\n", totalWorkers)
	fmt.Printf("- Workers per stage: %d\n", workersPerStage)
	fmt.Printf("- File size: %d MB\n", fileSize/(1024*1024))
	fmt.Printf("- Files per stage: %d\n", filesToGenerate)
	fmt.Printf("- Target directories: %s, %s\n", stage1Dir, stage2Dir)

	// Create directories if they don't exist
	if err := os.MkdirAll(stage1Dir, 0755); err != nil {
		fmt.Printf("Error creating stage1 directory: %v\n", err)
		os.Exit(1)
	}

	if err := os.MkdirAll(stage2Dir, 0755); err != nil {
		fmt.Printf("Error creating stage2 directory: %v\n", err)
		os.Exit(1)
	}

	var wg sync.WaitGroup
	var stage1SuccessCount, stage2SuccessCount int64

	filesPerWorker := filesToGenerate / workersPerStage

	startTime := time.Now()

	prefix := "/local_stage/TLB22710_VIRAJITH_TEST_BP_APP_USER_SCHEMA/data-persist-dir/materialize/tables/v0__b8481b904854cb31b66b1532a68cbac9/1739849135/1758092781218882556/"
	dir1, dir2 := stage1Dir+prefix, stage1Dir+prefix

	os.MkdirAll(dir1, 0755)
	os.MkdirAll(dir2, 0755)

	// Start workers for stage1
	fmt.Printf("\nStarting %d workers for %s...\n", workersPerStage, stage1Dir)
	for i := 0; i < workersPerStage; i++ {
		wg.Add(1)
		go fileWorker(i+1, dir1, filesPerWorker, &stage1SuccessCount, &wg)
	}

	// Start workers for stage2
	fmt.Printf("Starting %d workers for %s...\n", workersPerStage, stage2Dir)
	for i := 0; i < workersPerStage; i++ {
		wg.Add(1)
		go fileWorker(workersPerStage+i+1, dir2, filesPerWorker, &stage2SuccessCount, &wg)
	}

	// Wait for all workers to complete
	fmt.Println("\nWaiting for all workers to complete...")
	wg.Wait()

	duration := time.Since(startTime)

	// Print results
	fmt.Printf("\n=== Generation Complete ===\n")
	fmt.Printf("Duration: %v\n", duration)
	fmt.Printf("Stage1 (%s): %d files successfully created\n", stage1Dir, stage1SuccessCount)
	fmt.Printf("Stage2 (%s): %d files successfully created\n", stage2Dir, stage2SuccessCount)
	fmt.Printf("Total files created: %d\n", stage1SuccessCount+stage2SuccessCount)
	fmt.Printf("Expected total: %d\n", filesToGenerate*2)

	if stage1SuccessCount+stage2SuccessCount == int64(filesToGenerate*2) {
		fmt.Println("✅ All files generated successfully!")
	} else {
		fmt.Printf("⚠️  Some files failed to generate. Missing: %d files\n",
			int64(filesToGenerate*2)-(stage1SuccessCount+stage2SuccessCount))
	}
}
