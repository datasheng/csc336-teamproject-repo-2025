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

