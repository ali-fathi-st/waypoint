-- Runs once when the Docker database is first created.
-- pytest uses this separate database so tests never touch your real data.
CREATE DATABASE waypoint_test OWNER waypoint;
