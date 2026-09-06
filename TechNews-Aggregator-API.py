import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
import uvicorn
import sqlite3

# 1. Initialize FastAPI app
app = FastAPI(title="Tech News Aggregator API", description="Scrapes and stores top tech news")

# 2. Database Setup Function
def init_db():
    # This creates a file named 'news_database.db' in your folder
    conn = sqlite3.connect('news_database.db')
    cursor = conn.cursor()
    # Create a table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Run the DB setup when the script starts
init_db()

# 3. Scraping & Saving Function
def scrape_and_save():
    url = "https://news.ycombinator.com/"
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tags = soup.find_all('span', class_='titleline')
        
        # Connect to DB to save data
        conn = sqlite3.connect('news_database.db')
        cursor = conn.cursor()
        
        # Clear old data before saving new ones (optional, keeps db clean)
        cursor.execute("DELETE FROM articles")
        
        for tag in title_tags[:10]:
            title = tag.text
            link = tag.find('a')['href'] if tag.find('a') else "No Link"
            
            # Insert into database
            cursor.execute("INSERT INTO articles (title, url) VALUES (?, ?)", (title, link))
            
        conn.commit()
        conn.close()
        return True
    return False

# 4. API Endpoints
@app.get("/")
def home():
    return {"message": "Welcome! Use /api/update to fetch new data, and /api/news to view it."}

# Endpoint to trigger the scraper
@app.get("/api/update")
def update_news():
    success = scrape_and_save()
    if success:
        return {"status": "success", "message": "Database updated with latest news!"}
    return {"status": "error", "message": "Failed to scrape data."}

# Endpoint to fetch data FROM THE DATABASE
@app.get("/api/news")
def get_news():
    conn = sqlite3.connect('news_database.db')
    cursor = conn.cursor()
    
    # Read data from database
    cursor.execute("SELECT title, url FROM articles")
    rows = cursor.fetchall()
    conn.close()
    
    # Convert DB rows into JSON format
    articles_list = [{"title": row[0], "url": row[1]} for row in rows]
    
    return {
        "status": "success",
        "total_results": len(articles_list),
        "source": "Database",
        "articles": articles_list
    }

if __name__ == "__main__":
    print("Starting FastAPI Server with Database...")
    uvicorn.run(app, host="127.0.0.1", port=8000)