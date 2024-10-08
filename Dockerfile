# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python libraries
RUN pip install --upgrade pip
RUN pip install beautifulsoup4 requests streamlit pandas aiohttp

# Expose port for Streamlit
EXPOSE 8501

# Command to run Streamlit app on container start
CMD ["streamlit", "run", "crawl.py", "--server.port=8501", "--server.address=0.0.0.0"]

