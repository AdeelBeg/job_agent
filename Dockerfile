# Official Playwright image — all browser deps pre-installed, no libasound2 issues
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Create necessary directories
RUN mkdir -p data logs/screenshots

# Run the agent
CMD ["python", "main.py"]
