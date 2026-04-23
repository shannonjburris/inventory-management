# ---- Stage 1: builder ----
# Install dependencies into a separate prefix so we can copy just the
# installed packages into the smaller runtime image.
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Stage 2: runtime ----
# Lean final image — no build tools, no pip cache.
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create a non-root user for security — running as root inside a container
# means a container escape gives the attacker root on the host.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy installed packages from the builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Switch to the non-root user before starting the process
USER appuser

EXPOSE 5000

# gunicorn is the production WSGI server (like pm2 for Node).
# "app:create_app()" tells gunicorn to call create_app() from the app package
# to get the Flask application object.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:create_app()"]
