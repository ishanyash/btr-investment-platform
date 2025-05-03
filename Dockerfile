FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install reportlab prophet folium streamlit-folium

# Copy project files
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

# Start the application
CMD ["python", "scripts/run_data_collection.py", "--schedule", "daily"]