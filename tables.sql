CREATE DATABASE IF NOT EXISTS voting_db;
USE voting_system;

CREATE TABLE IF NOT EXISTS organizations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) UNIQUE NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(150) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  role ENUM('admin','organization','voter') NOT NULL,
  org_id INT NULL,
  public_key TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS candidates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  org_id INT NULL,
  description TEXT,
  FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS settings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  voting_active BOOLEAN NOT NULL DEFAULT FALSE,
  results_declared BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE result_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    results_data JSON,
    total_votes INTEGER,
    winner TEXT
);
