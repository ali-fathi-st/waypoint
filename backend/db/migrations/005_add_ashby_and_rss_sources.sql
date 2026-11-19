-- Two more job sources:
--   ashby  employers' public job boards on Ashby (e.g. Jobber, in Edmonton)
--   rss    employers' public RSS job feeds (e.g. the Government of Alberta)

ALTER TABLE jobs DROP CONSTRAINT jobs_source_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_source_check
    CHECK (source IN ('greenhouse', 'lever', 'ashby', 'adzuna', 'rss', 'manual'));

ALTER TABLE source_settings DROP CONSTRAINT source_settings_source_check;
ALTER TABLE source_settings ADD CONSTRAINT source_settings_source_check
    CHECK (source IN ('greenhouse', 'lever', 'ashby', 'adzuna', 'rss'));

INSERT INTO source_settings (source) VALUES ('ashby'), ('rss');
