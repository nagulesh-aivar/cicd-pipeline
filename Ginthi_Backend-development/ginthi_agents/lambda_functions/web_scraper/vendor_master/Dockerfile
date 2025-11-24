# ✅ Use Playwright’s official image (includes Chromium, Node, deps, etc.)
FROM mcr.microsoft.com/playwright/python:v1.45.0-focal

# Set Lambda task root as working directory
WORKDIR /var/task

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install AWS Lambda Runtime Interface Client (required for container-based Lambda)
RUN pip install awslambdaric

# Copy your Python code
COPY vendor_data_scraper.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/var/task"

# ✅ Correct Lambda entrypoint
CMD ["python3", "-m", "awslambdaric", "vendor_data_scraper.handler"]
