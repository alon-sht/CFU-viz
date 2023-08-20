# app/Dockerfile

FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/alon-sht/CFU-viz.git .

RUN pip3 install -r requirements.txt

EXPOSE 5401

HEALTHCHECK CMD curl --fail http://localhost:5401/_stcore/health

ENTRYPOINT ["streamlit", "run", "MyCFUViz.py", "--server.port=5401", "--server.address=0.0.0.0"]