// Inicjalizacja MongoDB
db.products.insertMany([
    { name: "Laptop", category: "Electronics", price: 1200, stock: 10 },
    { name: "Smartphone", category: "Electronics", price: 800, stock: 25 },
    { name: "Coffee Maker", category: "Appliances", price: 150, stock: 15 },
    { name: "Desk Lamp", category: "Furniture", price: 45, stock: 30 }
]);
