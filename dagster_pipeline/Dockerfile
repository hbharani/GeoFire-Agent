FROM python:3.11-slim

WORKDIR /app

# GDAL system dependencies required by rasterio / geopandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000

CMD ["dagster-webserver", "--host", "0.0.0.0", "--port", "3000", "--workspace", "workspace.yaml"]
