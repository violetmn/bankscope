FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY bankscope ./bankscope
RUN pip install --no-cache-dir .
RUN useradd --create-home appuser && mkdir /app/data && chown appuser /app/data
USER appuser
EXPOSE 8000
CMD ["uvicorn", "bankscope.api:app", "--host", "0.0.0.0", "--port", "8000"]
