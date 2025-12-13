-- 1. USERS TABLE (Added is_admin flag)
CREATE TABLE users (
  user_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120),
  email VARCHAR(160) UNIQUE, -- Enforce uniqueness at DB level too
  student_id VARCHAR(20) UNIQUE,
  password_hash VARCHAR(255),
  is_admin BOOLEAN DEFAULT FALSE
);

CREATE TABLE organizations (
  org_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  org_name VARCHAR(120)
);

CREATE TABLE org_members (
  org_id INT UNSIGNED NOT NULL,
  user_id INT UNSIGNED NOT NULL,
  role VARCHAR(50) NOT NULL DEFAULT 'MEMBER',
  PRIMARY KEY (org_id, user_id),
  CONSTRAINT fk_members_org FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE,
  CONSTRAINT fk_members_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 2. EVENTS TABLE (Added description column)
CREATE TABLE events (
  event_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  org_id INT UNSIGNED NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT, -- New Column
  venue VARCHAR(200),
  starts_at DATETIME NOT NULL,
  ends_at DATETIME NOT NULL,
  capacity INT UNSIGNED NOT NULL,
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_events_org FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE,
  CHECK (capacity >= 0),
  CHECK (ends_at > starts_at)
) ENGINE=InnoDB;

CREATE TABLE tickets (
  ticket_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  event_id INT UNSIGNED NOT NULL,
  name VARCHAR(120) NOT NULL,
  price_cents INT UNSIGNED NOT NULL,
  qty_total INT UNSIGNED NOT NULL,
  CONSTRAINT fk_tickets_event FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
  UNIQUE KEY uq_ticket_name_per_event (event_id, name),
  CHECK (price_cents >= 0),
  CHECK (qty_total >= 0)
) ENGINE=InnoDB;

CREATE TABLE orders (
  order_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  buyer_user_id INT UNSIGNED NULL,
  email VARCHAR(254) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_orders_user FOREIGN KEY (buyer_user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE order_items (
  order_item_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_id INT UNSIGNED NOT NULL,
  ticket_id INT UNSIGNED NOT NULL,
  qty INT UNSIGNED NOT NULL,
  unit_price_cents INT UNSIGNED NOT NULL,
  CONSTRAINT fk_oi_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
  CONSTRAINT fk_oi_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON DELETE RESTRICT,
  CHECK (qty > 0),
  CHECK (unit_price_cents >= 0)
) ENGINE=InnoDB;

CREATE TABLE payments (
  payment_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_id INT UNSIGNED NOT NULL,
  provider VARCHAR(40) NOT NULL,
  status ENUM('PENDING', 'SUCCEEDED', 'FAILED', 'REFUNDED') NOT NULL,
  amount_cents INT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pay_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
  CHECK (amount_cents >= 0)
) ENGINE=InnoDB;

CREATE TABLE revenue (
  revenue_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_id INT UNSIGNED NOT NULL,
  platform_fee_cents INT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_revenue_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_events_org ON events(org_id);
CREATE INDEX idx_tickets_event ON tickets(event_id);
CREATE INDEX idx_oi_order ON order_items(order_id);
CREATE INDEX idx_oi_ticket ON order_items(ticket_id);
CREATE INDEX idx_pay_order ON payments(order_id);

-- 3. STORED PROCEDURES

DELIMITER //

DROP PROCEDURE IF EXISTS GetOrgRevenueReport //
-- Calculates 93% of revenue for the specific organization
CREATE PROCEDURE GetOrgRevenueReport(IN target_org_id INT)
BEGIN
    SELECT 
        e.title, 
        e.starts_at,
        COALESCE(SUM(oi.qty), 0) as tickets_sold,
        -- Calculate Total Revenue minus 7% fee (Approx 93%)
        CAST(COALESCE(SUM(p.amount_cents) * 0.93, 0) AS UNSIGNED) as revenue_cents
    FROM events e
    LEFT JOIN tickets t ON e.event_id = t.event_id
    LEFT JOIN order_items oi ON t.ticket_id = oi.ticket_id
    LEFT JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN payments p ON o.order_id = p.order_id
    WHERE e.org_id = target_org_id 
      AND (p.status = 'SUCCEEDED' OR p.status IS NULL)
    GROUP BY e.event_id
    ORDER BY e.starts_at DESC;
END //

DROP PROCEDURE IF EXISTS GetAdminRevenueReport //
-- Calculates 7% of revenue across ALL organizations
CREATE PROCEDURE GetAdminRevenueReport()
BEGIN
    SELECT 
        e.title,
        o_org.org_name,
        e.starts_at,
        COALESCE(SUM(oi.qty), 0) as tickets_sold,
        -- Calculate 7% Fee
        CAST(COALESCE(SUM(p.amount_cents) * 0.07, 0) AS UNSIGNED) as revenue_cents
    FROM events e
    JOIN organizations o_org ON e.org_id = o_org.org_id
    LEFT JOIN tickets t ON e.event_id = t.event_id
    LEFT JOIN order_items oi ON t.ticket_id = oi.ticket_id
    LEFT JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN payments p ON o.order_id = p.order_id
    WHERE (p.status = 'SUCCEEDED' OR p.status IS NULL)
    GROUP BY e.event_id
    ORDER BY e.starts_at DESC;
END //

DROP PROCEDURE IF EXISTS CreateEventWithTicket //

CREATE PROCEDURE CreateEventWithTicket(
    IN p_org_id INT, 
    IN p_title VARCHAR(200),
    IN p_description TEXT, -- Added Description
    IN p_venue VARCHAR(200), 
    IN p_starts_at DATETIME, 
    IN p_ends_at DATETIME, 
    IN p_capacity INT,
    IN p_price_cents INT,
    IN p_ticket_qty INT
)
BEGIN
    DECLARE new_event_id INT;

    INSERT INTO events (org_id, title, description, venue, starts_at, ends_at, capacity, is_published)
    VALUES (p_org_id, p_title, p_description, p_venue, p_starts_at, p_ends_at, p_capacity, TRUE);
    
    SET new_event_id = LAST_INSERT_ID();

    INSERT INTO tickets (event_id, name, price_cents, qty_total)
    VALUES (new_event_id, 'General Admission', p_price_cents, p_ticket_qty);
END //

DELIMITER ;