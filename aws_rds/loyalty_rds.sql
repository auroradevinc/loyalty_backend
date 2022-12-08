-- =================
-- DATABASE CREATION
-- =================
CREATE DATABASE LOYALTY_RDS_DB;
USE LOYALTY_RDS_DB;

-- ===============
-- TABLES CREATION
-- ===============
-- #1 CLIENT DB
CREATE TABLE CLIENT(
client_id	INT 		NOT NULL AUTO_INCREMENT,
name		VARCHAR(20) NOT NULL,
PRIMARY KEY(client_id)
);

-- #2 BUSINESS DB
CREATE TABLE BUSINESS(
bus_id		INT 		NOT NULL AUTO_INCREMENT,
name		VARCHAR(20) NOT NULL,
client_id	INT			NOT NULL,
FOREIGN KEY(client_id) REFERENCES CLIENT(client_id),
PRIMARY KEY(bus_id)
);

-- #3 CUSTOMER DB
CREATE TABLE CUSTOMER(
customer_id		INT			NOT NULL AUTO_INCREMENT,
client_id		INT			NOT NULL,
first_name		VARCHAR(20) NOT NULL,
middle_name     VARCHAR(20),
last_name		VARCHAR(20),
phone_number	VARCHAR(10) NOT NULL,
email			VARCHAR(30) NOT NULL,
verification	BOOLEAN		NOT NULL,
address			VARCHAR(50),
num_referred	INT,
reward_points	INT,
FOREIGN KEY(client_id) REFERENCES CLIENT(client_id),
PRIMARY KEY(customer_id)
);

-- #4 CARD DB
CREATE TABLE CARD(
card_id			VARCHAR(7)  NOT NULL,
client_id		INT		    NOT NULL,
security_code	INT		    NOT NULL,
status			BOOLEAN     NOT NULL,
customer_id		INT,
card_type		VARCHAR(20) NOT NULL,
origin			VARCHAR(50),
FOREIGN KEY(customer_id) REFERENCES CUSTOMER(customer_id),
FOREIGN KEY(client_id) REFERENCES CLIENT(client_id),
PRIMARY KEY(card_id)
);

-- #5 PROMO DB
CREATE TABLE PROMO(
promo_id 			  INT 	NOT NULL AUTO_INCREMENT,
client_id			  INT	NOT NULL,
bus_id				  INT,
card_id				  VARCHAR(7),
gold_promo			  VARCHAR(20),
platinum_promo		  VARCHAR(20),
titanium_promo		  VARCHAR(20),
custom_promo		  VARCHAR(20),
date_created		  DATE	NOT NULL,
date_validity		  DATE,        							-- NULL When No expiry date specified
custom_promo_validity ENUM("DATE", "ONE-TIMER", "CLAIMED"), -- DATE implies see data_validity for expiry date
FOREIGN KEY(bus_id) REFERENCES BUSINESS(bus_id),
FOREIGN KEY(client_id) REFERENCES CLIENT(client_id),
FOREIGN KEY(card_id) REFERENCES CARD(card_id),
PRIMARY KEY(promo_id)
);

-- #6 SCAN DB
CREATE TABLE SCAN(
scan_id			INT 		NOT NULL AUTO_INCREMENT,
scan_time		DATETIME	NOT NULL,
client_id		INT 		NOT NULL,
bus_id			INT			NOT NULL,
customer_id		INT			NOT NULL,
card_id			VARCHAR(7)	NOT NULL,
promo_id		INT			NOT NULL,
FOREIGN KEY(customer_id) REFERENCES CUSTOMER(customer_id),
FOREIGN KEY(bus_id) REFERENCES BUSINESS(bus_id),
FOREIGN KEY(client_id) REFERENCES CLIENT(client_id),
FOREIGN KEY(promo_id) REFERENCES PROMO(promo_id),
PRIMARY KEY(scan_id)
);

-- =====================
-- DESCRIBING ALL TABLES
-- =====================
USE LOYALTY_RDS_DB;
DESC CLIENT;
DESC BUSINESS;
DESC CUSTOMER;
DESC CARD;
DESC PROMO;
DESC SCAN;

-- ===================
-- DROPPING ALL TABLES
-- =================== 
USE LOYALTY_RDS_DB;
DROP TABLE SCAN;
DROP TABLE PROMO;
DROP TABLE CARD;
DROP TABLE CUSTOMER;
DROP TABLE  BUSINESS;
DROP TABLE CLIENT;

-- =============================================
-- QUERIES(POPULATE DATA TO MATCH DOCUMENTATION)
-- =============================================
INSERT INTO CLIENT VALUES (NULL, "GLOWBAL"); -- AUTO_INCREMENT takes NULL to incremental automatically without query specifying the attribute names(INSERT INTO TABLE(aatribute_1, attribute_2) VALUES(value_1, value_2))
INSERT INTO CLIENT VALUES (NULL, "TABLETOP");
SELECT * FROM CLIENT;

INSERT INTO BUSINESS VALUES (NULL, "RILEY'S FISH & GRILL", 1);
INSERT INTO BUSINESS VALUES (NULL, "COAST", 			   1);
SELECT * FROM BUSINESS;

INSERT INTO CUSTOMER VALUES (NULL, 1, "JOHN", 	NULL, "DOE", 	 "7783337777", "johndoe@icloud.com",  1,  NULL,               0, 0);
INSERT INTO CUSTOMER VALUES (NULL, 1, "JOHN", 	NULL, "DOE", 	 "7783337777", "johndoe@icloud.com",  1, "123 ST. VANCOUVER", 0, 0);
INSERT INTO CUSTOMER VALUES (NULL, 1, "SERGIO", NULL, "PEREZ", "6045553333", "sergio95@icloud.com", 1,  NULL,                 5, 0);
SELECT * FROM CUSTOMER;

INSERT INTO CARD VALUES("00AUV6", 1, 001, 1, 1,    "TITANIUM", "REFERRAL");
INSERT INTO CARD VALUES("00AUV9", 1, 063, 1, 2,    "PLATINUM", "FAIRMOUNT HOTEL");
INSERT INTO CARD VALUES("00AUV7", 1, 094, 1, 3,    "GOLD",     "RILEY'S RESTAURANT");
INSERT INTO CARD VALUES("00AUVA", 1, 099, 0, NULL, "EVENT",    "ANNUAL BUSINESS EVENT 2022");
INSERT INTO CARD VALUES("00AUVB", 1, 091, 0, NULL, "EVENT",    "ANNUAL BUSINESS EVENT 2022 Part 2");
INSERT INTO CARD VALUES("00AUVC", 1, 054, 0, NULL, "GOLD",     "");
INSERT INTO CARD VALUES("00AUVF", 1, 251, 0, NULL, "GOLD",     "");
INSERT INTO CARD VALUES("00AUVG", 1, 124, 0, NULL, "GOLD",     "");
INSERT INTO CARD VALUES("00AUVH", 1, 454, 0, NULL, "PLATINUM",     "");
INSERT INTO CARD VALUES("00AUVE", 1, 457, 0, NULL, "TITANIUM",     "");
SELECT * FROM CARD;

INSERT INTO PROMO VALUES(NULL, 1, 1, NULL,    "20%_OFF_WINE", "30%_OFF_WINE", "FREE_WINE", NULL,          "2022-11-10", "2022-11-13", NULL);
INSERT INTO PROMO VALUES(NULL, 1, 1, NULL,    "20%_OFF_WINE", "30%_OFF_WINE", "FREE_WINE", NULL,          "2022-11-13", NULL,         NULL);
INSERT INTO PROMO VALUES(NULL, 1, 1, "00AUV6", NULL,           NULL,           NULL,       "FREE_DINNER", "2022-11-23", NULL,         "One-Timer");
SELECT * FROM PROMO;

INSERT INTO SCAN VALUES(NULL, "2022-11-22 13:00:00", 1, 1, 1, "00AUV6", 1);
INSERT INTO SCAN VALUES(NULL, "2022-11-23 13:01:00", 1, 1, 3, "00AUV7", 1);
INSERT INTO SCAN VALUES(NULL, "2022-11-25 16:00:00", 1, 2, 1, "00AUV6", 2);
SELECT * FROM SCAN;


UPDATE CUSTOMER c SET c.num_referred = c.num_referred + 1 WHERE c.customer_id = 4;
SELECT * from CARD c WHERE c.card_type = "GOLD" AND c.status = 0 LIMIT 1;

DELETE FROM CARD c where c.customer_id = 4;
DELETE FROM CUSTOMER c where c.customer_id = 4;
-- ===================
-- QUERIES FOR BACKEND
-- =================== 
