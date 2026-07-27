-- Inicjalizacja bazy danych PostgreSQL
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 0,
    price DECIMAL(10,2)
);

INSERT INTO inventory (item_name, quantity, price) VALUES 
('Laptop', 5, 1200.00),
('Mouse', 20, 25.50),
('Keyboard', 15, 45.00),
('Monitor', 10, 300.00);
