CREATE TABLE IF NOT EXISTS pociagi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL,
    producent TEXT NOT NULL,
    skala TEXT NOT NULL,
    cena REAL NOT NULL
);

INSERT INTO pociagi (nazwa, producent, skala, cena) VALUES
('Pendolino ED250', 'Alstom', 'H0', 1200.00),
('Ty2-911', 'Piko', 'H0', 850.50),
('TGV Duplex', 'Mehano', 'N', 450.00),
('ST44 Gagar', 'Roco', 'TT', 720.00);
