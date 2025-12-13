-- PostgreSQL Schema for AI-SOC Platform
-- Content Events & Metrics Tracking

CREATE TABLE IF NOT EXISTS content_events (
    id SERIAL PRIMARY KEY,
    notion_id TEXT UNIQUE,
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
    channel TEXT NOT NULL,  -- 'linkedin', 'threads', 'x', 'bot_dm', 'site'
    content_type TEXT NOT NULL,  -- 'post', 'thread', 'dm', 'landing'
    theme TEXT,  -- 'audit', 'monitoring', 'ki', 'energy', 'gov', 'fun'
    title TEXT,
    url TEXT,
    metric_views INTEGER DEFAULT 0,
    metric_reactions INTEGER DEFAULT 0,
    metric_comments INTEGER DEFAULT 0,
    metric_shares INTEGER DEFAULT 0,
    metric_clicks INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS funnel_events (
    id SERIAL PRIMARY KEY,
    notion_id TEXT UNIQUE,
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
    org_name TEXT,
    sector TEXT,  -- 'energy', 'gov', 'other'
    stage TEXT NOT NULL,  -- 'lead', 'meeting', 'pilot', 'deal'
    source_channel TEXT,  -- 'linkedin', 'threads', 'x', 'bot_dm', 'email', 'referral'
    source_content_notion_id TEXT REFERENCES content_events(notion_id),
    amount NUMERIC,
    owner TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_content_channel ON content_events(channel);
CREATE INDEX IF NOT EXISTS idx_content_theme ON content_events(theme);
CREATE INDEX IF NOT EXISTS idx_content_occurred ON content_events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_funnel_stage ON funnel_events(stage);
CREATE INDEX IF NOT EXISTS idx_funnel_sector ON funnel_events(sector);
CREATE INDEX IF NOT EXISTS idx_funnel_occurred ON funnel_events(occurred_at);

-- Views for analytics
CREATE OR REPLACE VIEW monthly_channel_metrics AS
SELECT
    date_trunc('month', occurred_at)::date AS month,
    channel,
    COUNT(*) FILTER (WHERE content_type IN ('post','thread')) AS content_items,
    SUM(metric_views) AS views,
    (SUM(metric_reactions) + SUM(metric_comments) + SUM(metric_shares)) AS engagements,
    SUM(metric_clicks) AS clicks
FROM content_events
GROUP BY 1, 2;

CREATE OR REPLACE VIEW monthly_funnel_metrics AS
SELECT
    date_trunc('month', occurred_at)::date AS month,
    source_channel AS channel,
    COUNT(*) FILTER (WHERE stage = 'lead') AS leads,
    COUNT(*) FILTER (WHERE stage = 'meeting') AS meetings,
    COUNT(*) FILTER (WHERE stage = 'pilot') AS pilots,
    COUNT(*) FILTER (WHERE stage = 'deal') AS deals,
    SUM(amount) FILTER (WHERE stage = 'deal') AS revenue
FROM funnel_events
GROUP BY 1, 2;
