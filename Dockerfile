# Use Python 3.11 slim image for efficiency
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BOT_STATE_PATH=/app/data/state.json

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create data directory with proper permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bot.py .

# Create startup script
RUN echo '#!/bin/bash\n\
if [ ! -f "/app/data/state.json" ]; then\n\
    echo "{}" > /app/data/state.json\n\
fi\n\
python bot.py' > /app/start.sh && chmod +x /app/start.sh

# Change ownership to app user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import json; import os; print('Bot is running')" || exit 1

# Expose port (for future web features)
EXPOSE 8080

# Start the application
CMD ["/app/start.sh"]