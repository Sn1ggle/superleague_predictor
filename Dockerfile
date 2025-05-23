FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=backend/app.py

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]