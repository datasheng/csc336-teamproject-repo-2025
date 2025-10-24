INSERT INTO users(full_name,email) VALUES
('Alex Chen','alex@citymail.cuny.edu'),
('James Wilson','james@citymail.cuny.edu')
ON CONFLICT DO NOTHING;

INSERT INTO organizations(org_name) VALUES
('CCNY Tech Club')
ON CONFLICT DO NOTHING;

INSERT INTO org_members(org_id,user_id,role)
SELECT 1, 1, 'owner'
ON CONFLICT DO NOTHING;

-- Users
INSERT INTO users (full_name, email)
VALUES 
('Alice Johnson', 'alice@citymail.cuny.edu'),
('Bob Lee', 'bob@citymail.cuny.edu'),
('Carla Singh', 'carla@citymail.cuny.edu');

-- Organizations
INSERT INTO organizations (org_name)
VALUES 
('Tech Club'),
('Robotics Society');

-- Org Members
INSERT INTO org_members (org_id, user_id, role)
VALUES 
(1, 1, 'admin'),
(1, 2, 'member'),
(2, 3, 'owner');

-- Events
INSERT INTO events (org_id, event_name, event_date, location)
VALUES 
(1, 'AI Workshop', '2025-11-10', 'Auditorium'),
(2, 'Drone Demo Day', '2025-12-02', 'Lab Hall');

-- Event Registrations
INSERT INTO event_registrations (event_id, user_id, registration_date)
VALUES 
(1, 1, NOW()),
(1, 2, NOW()),
(2, 3, NOW());
