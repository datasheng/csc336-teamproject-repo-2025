
CREATE TABLE users (
  user_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120),
  email VARCHAR(160)
);

CREATE TABLE organizations (
  org_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  org_name VARCHAR(120)
);

CREATE TABLE events (
  event_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  org_id INT UNSIGNED NOT NULL,
  title VARCHAR(200) NOT NULL,
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

CREATE INDEX idx_events_org ON events(org_id);
CREATE INDEX idx_tickets_event ON tickets(event_id);
CREATE INDEX idx_oi_order ON order_items(order_id);
CREATE INDEX idx_oi_ticket ON order_items(ticket_id);
CREATE INDEX idx_pay_order ON payments(order_id);
