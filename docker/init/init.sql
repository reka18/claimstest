DROP TABLE IF EXISTS claims;
CREATE TABLE claims (
    id SERIAL PRIMARY KEY,
    service_date DATE,
    submitted_procedure VARCHAR(255) NOT NULL,
    quadrant VARCHAR(10),
    plan_group VARCHAR(50) NOT NULL,
    subscriber_id BIGINT NOT NULL,
    provider_npi BIGINT NOT NULL,
    provider_fees NUMERIC(10, 2) NOT NULL,
    allowed_fees NUMERIC(10, 2) NOT NULL,
    member_coinsurance NUMERIC(10, 2) NOT NULL,
    member_copay NUMERIC(10, 2) NOT NULL,
    net_fee NUMERIC(10, 2) NOT NULL,
);