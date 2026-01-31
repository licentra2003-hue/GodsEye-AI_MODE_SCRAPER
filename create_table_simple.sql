-- RUN THIS IN YOUR SUPABASE SQL EDITOR
-- Copy and paste this entire script

-- Step 1: Create the table
CREATE TABLE IF NOT EXISTS processed_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Step 2: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_processed_jobs_job_id ON processed_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_processed_jobs_expires_at ON processed_jobs(expires_at);

-- Step 3: Verify table was created
SELECT * FROM processed_jobs LIMIT 1;

-- You should see: "No rows returned" which means the table exists but is empty
