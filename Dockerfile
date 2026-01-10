FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose API port
EXPOSE 8000

# Run the FastAPI server
# Set MATRIX_DEBUG=false by default (can be overridden with -e)
ENV MATRIX_DEBUG=false

CMD ["python", "-m", "uvicorn", "living_matrix.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
