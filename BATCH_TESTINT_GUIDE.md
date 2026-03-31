# 🚀 GodsEye Batch Worker: Testing Guide

The system has been upgraded to a **Batch Processing Model**. This allows **5 queries** to run simultaneously inside **one single browser instance**, significantly saving RAM and CPU resources.

---

## 1. Start the Infrastructure
Before testing, ensure your Docker environment is clean and running the latest batch worker.

```bash
# Shutdown existing containers
docker-compose down

# Build and start all services
# This will launch RabbitMQ, Postgres, the API Gateway, and the Batch Workers
docker-compose up -d --build
```

---

## 2. Run the Batch Test
Use the pre-configured test script to send **5 concurrent jobs** to the worker queue.

```bash
# Run the 5-query concurrent test
python test_5_concurrent.py
```

---

## 3. Monitor the Batch Process
Since the worker waits for a batch (or a 10s timeout), you should tail the logs of the first worker node to watch it happen live.

```bash
# Watch the worker buffer the jobs and launch the browser
docker logs -f godseye-googleaimodescraper-worker_node-1
```

### What to look for in the logs:
1.  **Buffering**: `📥 Buffered 1/5...`, `📥 Buffered 2/5...`
2.  **Trigger**: `📦 Batch full, starting processing...` or `🕒 Batch timeout reached...`
3.  **Parallel Tabs**: `✨ Tab 1 scraping...`, `✨ Tab 2 scraping...` (Note the 2.5s staggered start).
4.  **Completion**: `✅ Tab 1: Success!`, `🔥 Batch successfully processed.`

---

## 4. Verify Results in Database
After the "Batch complete" message appears in the logs, verify that the data has reached Supabase.

```bash
# Check the latest entries in your product_analysis_google table
python check_supabase.py
```

---

## 💡 Key Optimization Details
*   **Worker**: Now uses `worker_batch.py`.
*   **Economy**: 1 Browser Instance = 5 Concurrent Tabs.
*   **Stealth**: Uses the **Staggered Start Secret** (Tab 1 @ 0s, Tab 2 @ 2.5s...) to evade Google's "unusual traffic" detection.
*   **Schema**: Correctly nests results in the `raw_serp_results` JSON column for compatibility with the Frontend.
