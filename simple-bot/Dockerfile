FROM python:3.11-slim

WORKDIR /bot

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot script
COPY simple_bot.py .

# Create data directory for SQLite database
RUN mkdir -p /bot/data

# Make it executable
RUN chmod +x simple_bot.py

CMD ["python", "simple_bot.py"]
