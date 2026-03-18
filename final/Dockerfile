FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Download ALL required NLTK data with SSL bypass
# (avoids certificate errors in Docker/corporate environments)
RUN python -c "\
import ssl; \
ssl._create_default_https_context = ssl._create_unverified_context; \
import nltk; \
nltk.download('punkt', quiet=True); \
nltk.download('punkt_tab', quiet=True); \
nltk.download('cmudict', quiet=True); \
print('NLTK data downloaded successfully') \
"

# Create a persistent volume mount point for the SQLite DB
RUN mkdir -p /app/data

# Streamlit config: disable telemetry, set theme
RUN mkdir -p /app/.streamlit && cat > /app/.streamlit/config.toml <<EOF
[server]
headless = true
address = "0.0.0.0"
port = 8501
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false

[theme]
base = "dark"
EOF

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
