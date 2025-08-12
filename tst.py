from pymongo import MongoClient

uri = "mongodb+srv://sina:sina1234@cluster0.94hgdzt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(uri)
    print("✅ Connected to MongoDB!")
    print("Databases:", client.list_database_names())
except Exception as e:
    print("❌ Connection failed:", e)
