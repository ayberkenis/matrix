FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "living_matrix", "--host", "0.0.0.0", "--port", "1337"]
