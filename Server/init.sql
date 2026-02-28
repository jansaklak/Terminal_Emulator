USE labdb;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    role VARCHAR(50)
);

INSERT INTO users (username, role) VALUES
('admin', 'administrator'),
('student1', 'student'),
('student2', 'student');

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product VARCHAR(100),
    amount INT
);

INSERT INTO orders (product, amount) VALUES
('Laptop', 3),
('Monitor', 10),
('Klawiatura', 5);