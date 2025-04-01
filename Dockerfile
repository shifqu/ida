# Stage 1: Base build stage
FROM python:3.12-slim AS builder

# Create the app directory
RUN mkdir /app

# Set the working directory
WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

# Upgrade pip and install dependencies
RUN pip install --upgrade pip pip-tools

# Copy the requirements files first (better caching)
COPY requirements/ /app/requirements/

# Install Python dependencies
RUN pip-sync requirements/main.txt

# Stage 2: Development stage
FROM builder AS development

# Install development dependencies
COPY requirements/ /app/requirements/
RUN pip-sync requirements/dev.txt

# Copy application code
COPY . .

# Install the application in editable mode
RUN pip install --editable .[dev]

# Copy and set the entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Run the application
CMD ["manage", "runserver"]

# Stage 3: Production stage
FROM python:3.12-slim

RUN useradd -m -r appuser && \
   mkdir /app && \
   chown -R appuser /app

# Copy the Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Set the working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Install the application
RUN pip install .

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

# Create a directory for the SQLite database and staticfiles
RUN mkdir /dbdata && chown -R appuser:appuser /dbdata
RUN mkdir /staticdata && chown -R appuser:appuser /staticdata

# Switch to non-root user
USER appuser

# Copy and set the entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:38080", "--workers", "4", "ida.wsgi:application"]
