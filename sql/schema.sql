-- ============================================================
-- USA Database Schema
-- Run: mysql -u root -p < sql/usa_schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS usa;
USE usa;

-- Source: company list with market cap data
CREATE TABLE IF NOT EXISTS usa_companiesmarketcap (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Symbol VARCHAR(20) NOT NULL
);

-- Enriched company records (HQ, financials, website)
CREATE TABLE IF NOT EXISTS usa_companies_final (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Symbol VARCHAR(20),
    City VARCHAR(100),
    State VARCHAR(100),
    Full_Address VARCHAR(500),
    Country VARCHAR(100),
    Sector VARCHAR(150),
    Industry VARCHAR(150),
    Revenue_million DECIMAL(15,2),
    Company_Website VARCHAR(500),
    UNIQUE KEY uq_name (Name)
);

-- Company page URLs on companiesmarketcap.com
CREATE TABLE IF NOT EXISTS USA_companies_link (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Link VARCHAR(500),
    UNIQUE KEY uq_name (Name)
);

-- Sector tags per company
CREATE TABLE IF NOT EXISTS usa_companies_sector (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Company_Name VARCHAR(255) NOT NULL,
    Sectors TEXT,
    UNIQUE KEY uq_company (Company_Name)
);

-- Key executives scraped from Yahoo Finance
CREATE TABLE IF NOT EXISTS Key_people_info (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(255),
    Ticker VARCHAR(20),
    Designation VARCHAR(250),
    Person_Name VARCHAR(250)
);

-- LinkedIn profiles matched to executives
CREATE TABLE IF NOT EXISTS LinkedIn_Profiles (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Person_ID INT,
    Company_Name VARCHAR(255),
    Designation VARCHAR(250),
    LinkedIn_Profile VARCHAR(500),
    Person_Name_DB VARCHAR(250),
    UNIQUE KEY uq_person (Person_ID)
);

-- Best email per executive with confidence rating
CREATE TABLE IF NOT EXISTS usa_top_companies_key_people_email (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Company_ID INT,
    Company_Name VARCHAR(255),
    Person_Name VARCHAR(250),
    Designation VARCHAR(250),
    Email_Id VARCHAR(255),
    Rating TINYINT COMMENT '3=pattern, 4=found in Google, 5=SMTP verified',
    LinkedIn_Name VARCHAR(255),
    LinkedIn_Profile VARCHAR(500),
    UNIQUE KEY uq_email (Email_Id)
);
