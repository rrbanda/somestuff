import streamlit as st
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin
from datetime import datetime

# Asynchronous function to fetch a single webpage
async def fetch_page(session, url):
    async with session.get(url) as response:
        return await response.text()

# Function to clean and filter out non-content paragraphs (template noise)
def clean_article_content(paragraphs):
    filtered_content = []
    
    for p in paragraphs:
        text = p.get_text(strip=True)
        
        if ("HTTPS" in text or "gov" in text or "Official websites use" in text or "Learn more" in text):
            continue  # Skip template/irrelevant content
        
        if len(text) > 20:
            filtered_content.append(text)
    
    return ' '.join(filtered_content) if filtered_content else "No relevant content available"

# Function to scrape article content asynchronously
async def scrape_article_content(session, base_url, relative_link):
    # Convert relative link to absolute URL using urljoin
    link = urljoin(base_url, relative_link)
    
    page_content = await fetch_page(session, link)
    soup = BeautifulSoup(page_content, 'html.parser')
    paragraphs = soup.find_all('p')
    content = clean_article_content(paragraphs)
    return content

# Asynchronous function to fetch news data and articles from the main page
async def fetch_news_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    async with aiohttp.ClientSession(headers=headers) as session:
        page_content = await fetch_page(session, url)
        soup = BeautifulSoup(page_content, 'html.parser')

        # Find all news articles - Inspect the site to verify the class for articles
        articles = soup.find_all('div', class_='views-row')

        docling_data = {"documents": []}

        # Asynchronously scrape the content for each article
        tasks = []
        for article in articles:
            title = article.find('h3').get_text(strip=True)
            relative_link = article.find('a')['href']
            date_tag = article.find('time')
            date = date_tag['datetime'] if date_tag else str(datetime.now().date())
            
            tasks.append(asyncio.create_task(scrape_article_content(session, url, relative_link)))
            docling_data["documents"].append({
                "title": title,
                "url": urljoin(url, relative_link),
                "content": None,  # To be filled later by the task
                "metadata": {
                    "date": date,
                    "source": url
                }
            })

        # Wait for all content scraping tasks to complete
        contents = await asyncio.gather(*tasks)

        # Fill in the content data for each document
        for i, content in enumerate(contents):
            docling_data["documents"][i]['content'] = content

        return docling_data

# Preprocessing content function with options
def preprocess_content(content, lowercase, remove_special_chars, remove_stopwords):
    if lowercase:
        content = content.lower()
    
    if remove_special_chars:
        content = re.sub(r'[^a-z\s]', '', content)

    tokens = content.split()

    if remove_stopwords:
        stop_words = set(['the', 'is', 'in', 'and', 'to', 'of', 'a', 'for', 'it'])
        tokens = [word for word in tokens if word not in stop_words]

    cleaned_content = ' '.join(tokens)
    return cleaned_content

# UI Setup
st.title('Asynchronous News Scraper and Preprocessor')

# Step 1: Scrape the news articles
url_input = st.text_input("Enter News URL")

# Button to trigger the asynchronous scraping
if st.button('Run Scraping'):
    if url_input:
        st.write("Processing the URL:", url_input)
        
        # Run the asynchronous fetching
        docling_data = asyncio.run(fetch_news_data(url_input))
        
        # If no articles found, show a warning message
        if len(docling_data['documents']) == 0:
            st.warning("No articles found. Please check the URL or structure of the page.")
        else:
            # Store the fetched data in session state for further processing
            st.session_state['fetched_data'] = docling_data
            st.success("Scraping completed asynchronously. You can now download the raw data or proceed to preprocessing.")
    else:
        st.error("Please enter a valid URL.")

# Step 2: Option to download raw data before preprocessing
if 'fetched_data' in st.session_state:
    raw_file_name = "raw_scraped_data.json"
    st.download_button(label=f"Download Raw Data ({raw_file_name})", data=json.dumps(st.session_state['fetched_data'], indent=4), file_name=raw_file_name, mime="application/json")

# Step 3: Preprocessing options
if 'fetched_data' in st.session_state:
    st.write("### Preprocessing Options")

    lowercase = st.checkbox("Convert to lowercase", value=True)
    remove_special_chars = st.checkbox("Remove special characters", value=True)
    remove_stopwords = st.checkbox("Remove stopwords", value=True)

    if st.button('Run Preprocessing'):
        # Apply preprocessing based on options selected
        preprocessed_data = st.session_state['fetched_data']
        for document in preprocessed_data['documents']:
            document['content'] = preprocess_content(document['content'], lowercase, remove_special_chars, remove_stopwords)

        # Save the preprocessed data in session state for download
        st.session_state['preprocessed_data'] = json.dumps(preprocessed_data, indent=4)
        st.success("Preprocessing completed. You can now download the preprocessed file.")

# Step 4: Download the preprocessed file
if 'preprocessed_data' in st.session_state:
    preprocessed_file_name = "preprocessedfile.json"
    st.download_button(label=f"Download Preprocessed Data ({preprocessed_file_name})", data=st.session_state['preprocessed_data'], file_name=preprocessed_file_name, mime="application/json")

