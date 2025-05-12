# ---------- build stage: only for code -------------
FROM python:3.12-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
COPY . .

# ---------- runtime stage --------------------------
FROM python:3.12-slim
WORKDIR /app
# bring the pre-installed libs across
COPY --from=build /install /usr/local/
COPY --from=build /app /app

COPY docker-entrypoint.sh /usr/local/bin/
USER root
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "radarr_sonarr_watchmon.py"]
