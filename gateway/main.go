package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/google/uuid"
	amqp "github.com/rabbitmq/amqp091-go"
)

// ScrapeRequest represents the incoming scrape request
type ScrapeRequest struct {
	Query      string `json:"query" validate:"required,min=1,max=500"`
	Location   string `json:"location" validate:"required,min=1,max=100"`
	WebhookURL string `json:"webhook_url,omitempty" validate:"omitempty,url"`
	ProductID  string `json:"product_id,omitempty" validate:"omitempty,uuid4"`
}

// ScrapeResponse represents the response to the client
type ScrapeResponse struct {
	JobID  string `json:"job_id"`
	Status string `json:"status"`
}

// JobMessage represents the message sent to RabbitMQ
type JobMessage struct {
	JobID     string `json:"job_id"`
	Query     string `json:"query"`
	Location  string `json:"location"`
	ProductID string `json:"product_id,omitempty"`
	Status    string `json:"status"`
}

// HealthResponse represents health check response
type HealthResponse struct {
	Status    string `json:"status"`
	Service   string `json:"service"`
	Version   string `json:"version"`
	Timestamp string `json:"timestamp"`
	RabbitMQ  string `json:"rabbitmq"`
}

// SourceLink represents a source link with URL and title
type SourceLink struct {
	URL   string `json:"url"`
	Title string `json:"title"`
	Date  string `json:"date,omitempty"`
}

// JobResult represents the result received from workers
type JobResult struct {
	JobID                    string                 `json:"job_id"`
	ProductID                string                 `json:"product_id"`
	Query                    string                 `json:"query"`
	Success                  bool                   `json:"success"`
	Location                 string                 `json:"location"`
	Timestamp                string                 `json:"timestamp"`
	SourceLinks              []SourceLink           `json:"source_links"`
	ErrorMessage             string                 `json:"error_message"`
	OriginalQuery            string                 `json:"original_query"`
	StructureType            string                 `json:"structure_type"`
	AIOverviewText           string                 `json:"ai_overview_text"`
	AIOverviewFound          bool                   `json:"ai_overview_found"`
	QueryModifications       []string               `json:"query_modifications_tried"`
	DidQueryPoppedAIOverview bool                   `json:"did_query_popped_AI_overview"`
	AIModeFound              bool                   `json:"ai_mode_found"`
	AIModeText               string                 `json:"ai_mode_text"`
	RawSERPResults           map[string]interface{} `json:"raw_serp_results"`
}

// WebSocketMessage represents a message sent to WebSocket clients
type WebSocketMessage struct {
	Type      string      `json:"type"` // "job_result", "job_status", "error"
	JobID     string      `json:"job_id,omitempty"`
	Data      interface{} `json:"data,omitempty"`
	Timestamp string      `json:"timestamp"`
}

var rabbitMQConn *amqp.Connection
var rabbitMQChannel *amqp.Channel

// In-memory storage for job results (for demo purposes)
var jobResults = make(map[string]JobResult)
var resultsMutex sync.RWMutex

func scrapeResultCallbackHandler(c *fiber.Ctx) error {
	// Log the received callback data
	log.Printf("📥 Received scrape result callback")

	// Get the raw body
	body := c.Body()

	// Log the received data
	log.Printf("📋 Callback data: %s", string(body))

	// Parse the job result
	var result JobResult
	if err := json.Unmarshal(body, &result); err != nil {
		log.Printf("❌ Failed to parse callback data: %v", err)
		log.Printf("🐛 Raw JSON: %s", string(body))
		return fiber.NewError(fiber.StatusBadRequest, "Invalid JSON format")
	}

	// Log the received data
	log.Printf("📋 Job %s result received: %s", result.JobID, result.Query)

	// Store result for polling
	resultsMutex.Lock()
	jobResults[result.JobID] = result
	resultsMutex.Unlock()

	// Log that result is available for polling
	log.Printf("💾 Result stored for job %s - available via /api/job-result/%s", result.JobID, result.JobID)

	// Return success response
	return c.JSON(fiber.Map{
		"status":    "success",
		"message":   "Callback received successfully",
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	})
}

func jobResultHandler(c *fiber.Ctx) error {
	jobID := c.Params("jobId")
	if jobID == "" {
		return fiber.NewError(fiber.StatusBadRequest, "jobId is required")
	}

	resultsMutex.RLock()
	result, exists := jobResults[jobID]
	resultsMutex.RUnlock()

	if !exists {
		return c.JSON(fiber.Map{
			"status":  "pending",
			"message": "Job not found or still processing",
			"job_id":  jobID,
		})
	}

	// Debug: Log what we're about to return
	log.Printf("🔍 DEBUG: Returning result for job %s", jobID)
	log.Printf("🔍 DEBUG: Query: %s", result.Query)
	log.Printf("🔍 DEBUG: AI Overview Found: %t", result.AIOverviewFound)
	if result.AIOverviewText != "" {
		log.Printf("🔍 DEBUG: AI Overview length: %d", len(result.AIOverviewText))
	}

	return c.JSON(fiber.Map{
		"status": "completed",
		"data":   result,
	})
}

func main() {
	// Initialize Fiber app
	app := fiber.New(fiber.Config{
		ErrorHandler: func(c *fiber.Ctx, err error) error {
			code := fiber.StatusInternalServerError
			if e, ok := err.(*fiber.Error); ok {
				code = e.Code
			}
			return c.Status(code).JSON(fiber.Map{
				"error": err.Error(),
			})
		},
	})

	// Middleware
	app.Use(recover.New())
	app.Use(logger.New())
	app.Use(cors.New(cors.Config{
		AllowOrigins:     "*",
		AllowMethods:     "GET,POST,PUT,DELETE,OPTIONS",
		AllowHeaders:     "Origin,Content-Type,Accept,Authorization,X-Requested-With",
		AllowCredentials: false,
	}))

	// Initialize RabbitMQ
	if err := initRabbitMQ(); err != nil {
		log.Fatalf("Failed to initialize RabbitMQ: %v", err)
	}
	defer cleanupRabbitMQ()

	// Routes
	app.Get("/health", healthCheck)
	app.Post("/api/v1/scrape", scrapeHandler)
	app.Post("/api/scrape-result", scrapeResultCallbackHandler)
	app.Get("/api/job-result/:jobId", jobResultHandler)

	// Start server
	// FIX: Prioritize the system PORT (from Railway), then GATEWAY_PORT, then 8080
	port := getEnv("PORT", getEnv("GATEWAY_PORT", "8080"))
	log.Printf("🚀 GodsEye Gateway starting on port %s", port)
	log.Printf("🐰 RabbitMQ URL: %s", getEnv("RABBITMQ_URL", "amqp://admin:admin123@godseye-rabbitmq:5672/"))

	if err := app.Listen(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

func initRabbitMQ() error {
	rabbitMQURL := getEnv("RABBITMQ_URL", "amqp://admin:admin123@godseye-rabbitmq:5672/")

	var err error
	for i := 0; i < 5; i++ {
		rabbitMQConn, err = amqp.Dial(rabbitMQURL)
		if err == nil {
			break
		}
		log.Printf("Failed to connect to RabbitMQ (attempt %d/5): %v", i+1, err)
		time.Sleep(time.Duration(i+1) * time.Second)
	}

	if err != nil {
		return fmt.Errorf("failed to connect to RabbitMQ after 5 attempts: %w", err)
	}

	rabbitMQChannel, err = rabbitMQConn.Channel()
	if err != nil {
		return fmt.Errorf("failed to open RabbitMQ channel: %w", err)
	}

	// Declare queue
	_, err = rabbitMQChannel.QueueDeclare(
		"scrape_jobs", // name
		true,          // durable
		false,         // delete when unused
		false,         // exclusive
		false,         // no-wait
		nil,           // arguments
	)
	if err != nil {
		return fmt.Errorf("failed to declare queue: %w", err)
	}

	log.Println("✅ RabbitMQ connection established")
	return nil
}

func cleanupRabbitMQ() {
	if rabbitMQChannel != nil {
		rabbitMQChannel.Close()
	}
	if rabbitMQConn != nil {
		rabbitMQConn.Close()
	}
}

func healthCheck(c *fiber.Ctx) error {
	rabbitMQStatus := "disconnected"
	if rabbitMQConn != nil && !rabbitMQConn.IsClosed() {
		rabbitMQStatus = "connected"
	}

	response := HealthResponse{
		Status:    "healthy",
		Service:   "GodsEye Gateway",
		Version:   "1.0.0",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		RabbitMQ:  rabbitMQStatus,
	}

	return c.JSON(response)
}

func scrapeHandler(c *fiber.Ctx) error {
	// Parse request
	var req ScrapeRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid JSON format")
	}

	// Validate request
	if err := validateScrapeRequest(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, err.Error())
	}

	// Generate unique job ID
	jobID := uuid.New().String()

	// Generate product_id if not provided
	productID := req.ProductID
	if productID == "" {
		productID = uuid.New().String()
	}

	// Create job message
	jobMsg := JobMessage{
		JobID:     jobID,
		Query:     req.Query,
		Location:  req.Location,
		ProductID: productID,
		Status:    "pending",
	}

	// Publish to RabbitMQ
	if err := publishJob(jobMsg); err != nil {
		log.Printf("Failed to publish job %s: %v", jobID, err)
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to queue job")
	}

	// Return response
	response := ScrapeResponse{
		JobID:  jobID,
		Status: "queued",
	}

	log.Printf("📋 Job %s queued for query: '%s' in %s", jobID, req.Query, req.Location)
	return c.Status(fiber.StatusAccepted).JSON(response)
}

func validateScrapeRequest(req *ScrapeRequest) error {
	if req.Query == "" {
		return fmt.Errorf("query is required")
	}
	if len(req.Query) > 500 {
		return fmt.Errorf("query must be less than 500 characters")
	}
	if req.Location == "" {
		return fmt.Errorf("location is required")
	}
	if len(req.Location) > 50 {
		return fmt.Errorf("location must be less than 50 characters")
	}
	return nil
}

func publishJob(jobMsg JobMessage) error {
	if rabbitMQChannel == nil {
		return fmt.Errorf("RabbitMQ channel not available")
	}

	body, err := json.Marshal(jobMsg)
	if err != nil {
		return fmt.Errorf("failed to marshal job message: %w", err)
	}

	err = rabbitMQChannel.Publish(
		"",            // exchange
		"scrape_jobs", // routing key
		false,         // mandatory
		false,         // immediate
		amqp.Publishing{
			ContentType:  "application/json",
			Body:         body,
			DeliveryMode: amqp.Persistent, // Make message persistent
			Timestamp:    time.Now(),
		})

	return err
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
