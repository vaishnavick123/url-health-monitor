FROM python:3.11-slim

RUN apt-get clean
# Install Poetry
RUN pip install poetry

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN poetry install

# Expose ports
EXPOSE 8000 8501

# Run both backend and frontend
CMD bash -c "poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8000 & poetry run streamlit run frontend/app.py --server.port 8501 --server.enableCORS false --server.address 0.0.0.0"
