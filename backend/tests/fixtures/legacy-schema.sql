-- Original schema exported from merged PR4 model metadata (445a400).
CREATE TABLE users (
	id INTEGER NOT NULL,
	username VARCHAR(40) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	role VARCHAR(10) NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE TABLE player_profiles (
	user_id INTEGER NOT NULL,
	full_name VARCHAR(100) NOT NULL,
	position VARCHAR(30) NOT NULL,
	age INTEGER,
	team VARCHAR(100) NOT NULL,
	bio TEXT NOT NULL,
	PRIMARY KEY (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE analysis_jobs (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	status VARCHAR(16) NOT NULL,
	stage VARCHAR(24) NOT NULL,
	progress INTEGER NOT NULL,
	original_filename VARCHAR(255) NOT NULL,
	stored_filename VARCHAR(50) NOT NULL,
	selected_player_id INTEGER,
	demo BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	started_at DATETIME,
	completed_at DATETIME,
	error TEXT,
	video JSON NOT NULL,
	gallery JSON NOT NULL,
	tracks JSON NOT NULL,
	calibration JSON,
	result JSON,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_analysis_jobs_status ON analysis_jobs (status);

CREATE INDEX ix_analysis_jobs_user_id ON analysis_jobs (user_id);
