# syntax=docker/dockerfile:1

FROM python:3.11

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

EXPOSE 8080