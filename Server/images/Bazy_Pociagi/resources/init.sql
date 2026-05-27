CREATE TABLE IF NOT EXISTS pociagi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nazwa VARCHAR(100),
    producent VARCHAR(100),
    skala VARCHAR(20),
    cena DECIMAL(10, 2)
);

INSERT INTO pociagi (nazwa, producent, skala, cena) VALUES
('Pendolino ED250', 'Alstom', 'H0', 1200.00),
('Ty2-911', 'Piko', 'H0', 850.50),
('TGV Duplex', 'Mehano', 'N', 450.00),
('ST44 Gagar', 'Roco', 'TT', 720.00);
