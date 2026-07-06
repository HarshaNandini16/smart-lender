# Use official stable Python runtime as parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Set working directory
WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 5000

# Run database creation & model training if models are missing, then start server
CMD python -c "import os; from train_model import generate_synthetic_dataset, train_and_evaluate; \
    csv_path=os.path.join('dataset', 'loan_data.csv'); \
    models_dir='models'; charts_dir=os.path.join('static', 'images', 'charts'); \
    generate_synthetic_dataset(csv_path) if not os.path.exists(csv_path) else None; \
    train_and_evaluate(csv_path, models_dir, charts_dir) if not os.path.exists(os.path.join(models_dir, 'best_model.joblib')) else None" && \
    gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 2 app:app
