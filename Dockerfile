FROM python:3.10
RUN mkdir -p /usr/src/app/logs /usr/src/app/tmp
COPY . /usr/src/app
WORKDIR /usr/src/app
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    -O ./support-files/google-chrome-stable_current_amd64.deb \
    && dpkg -i ./support-files/google-chrome-stable_current_amd64.deb \
    && apt install -f \
    && google-chrome --version \
    && rm ./support-files/google-chrome-stable_current_amd64.deb
RUN pip3 install -U pip -i https://mirrors.cloud.tencent.com/pypi/simple && pip3 install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple
RUN bin/proxy_gemini.sh
