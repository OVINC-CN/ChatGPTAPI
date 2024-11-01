FROM python:3.10.15-slim

WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app/
RUN pip3 install -U pip && pip3 install -r requirements.txt

COPY . /usr/src/app
RUN mkdir -p /usr/src/app/logs /usr/src/app/tmp /usr/share/fonts/zh_cn

RUN bin/proxy_gemini.sh
