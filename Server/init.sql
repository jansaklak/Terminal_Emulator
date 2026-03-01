USE labdb;

CREATE TABLE IF NOT EXISTS users (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50)  NOT NULL,
    role     VARCHAR(50)  NOT NULL DEFAULT 'student',
    email    VARCHAR(100),
    created  DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, role, email) VALUES
('admin',    'administrator', 'admin@lab.local'),
('student1', 'student',       's1@lab.local'),
('student2', 'student',       's2@lab.local'),
('student3', 'student',       's3@lab.local');

CREATE TABLE IF NOT EXISTS orders (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    product  VARCHAR(100) NOT NULL,
    amount   INT          NOT NULL DEFAULT 1,
    price    DECIMAL(10,2),
    ordered  DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO orders (product, amount, price) VALUES
('Laptop',      3,  3499.99),
('Monitor',    10,   899.00),
('Klawiatura',  5,   149.50),
('Mysz',        8,    79.99),
('Headset',     4,   249.00);

CREATE TABLE IF NOT EXISTS products (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    category    VARCHAR(50),
    stock       INT DEFAULT 0,
    unit_price  DECIMAL(10,2)
);

INSERT INTO products (name, category, stock, unit_price) VALUES
('Laptop Pro 15',  'Computers',    12,  4299.00),
('Monitor 27"',    'Monitors',     25,   949.00),
('Mechanical KB',  'Peripherals',  40,   299.00),
('Wireless Mouse', 'Peripherals',  60,    89.00),
('USB-C Hub',      'Accessories',  35,   129.00),
('SSD 1TB',        'Storage',      50,   399.00),
('RAM 32GB',       'Memory',       30,   599.00);