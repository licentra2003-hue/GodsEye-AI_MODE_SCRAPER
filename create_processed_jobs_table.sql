-- Create processed_jobs table for deduplication
-- Run this in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS processed_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_processed_jobs_job_id ON processed_jobs(job_id);

-- Create index for cleanup operations
CREATE INDEX IF NOT EXISTS idx_processed_jobs_expires_at ON processed_jobs(expires_at);

-- Optional: Create a function to automatically clean up old jobs
CREATE OR REPLACE FUNCTION cleanup_old_processed_jobs()
RETURNS void AS $$
BEGIN
    DELETE FROM processed_jobs WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Optional: Create a trigger to automatically clean up old jobs (run every hour)
-- This requires pg_cron extension to be enabled in Supabase
-- Uncomment if you have pg_cron enabled:
-- SELECT cron.schedule('cleanup-processed-jobs', '0 * * * *', 'SELECT cleanup_old_processed_jobs();');
