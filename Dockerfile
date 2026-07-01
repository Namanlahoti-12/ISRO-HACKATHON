FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Set working directory
WORKDIR /app

# Install system dependencies if any are needed for shapely/rasterio
# (Usually not needed because wheels are available, but libgomp1 is needed for LightGBM/XGBoost often)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
# We copy the root directory because backend/app.py accesses ../outputs and ../models
COPY . /project

# Set working directory to backend
WORKDIR /project/backend

# Expose port
EXPOSE 5000

# Start gunicorn server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
