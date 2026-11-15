FROM python:3.14-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY company_brain ./company_brain
EXPOSE 8080
CMD ["uvicorn", "company_brain.app:app", "--host", "0.0.0.0", "--port", "8080"]
