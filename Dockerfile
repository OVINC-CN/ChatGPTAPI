FROM python:3.10

RUN mkdir -p /usr/src/app/logs /usr/src/app/tmp /usr/share/fonts/zh_cn

COPY ./support-files/fonts/* /usr/share/fonts/zh_cn
RUN fc-list :lang=zh

COPY . /usr/src/app
WORKDIR /usr/src/app

RUN pip3 install -U pip && pip3 install -r requirements.txt
RUN bin/proxy_gemini.sh
