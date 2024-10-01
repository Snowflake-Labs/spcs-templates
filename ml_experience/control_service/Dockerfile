FROM nvcr.io/nvidia/pytorch:23.08-py3

RUN apt-get update && apt-get upgrade -y
RUN apt-get install dnsutils -y && apt-get install net-tools -y

RUN apt update && apt install  openssh-server sudo -y
RUN useradd -rm -d /home/ubuntu -s /bin/bash -g root -G sudo -u 1000 test
RUN  echo 'test:test' | chpasswd
RUN service ssh start
EXPOSE 22

RUN curl -LO https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 \
    && mv ttyd.* /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd

RUN pip install --upgrade pip
COPY requirements.txt ./
RUN pip install -r ./requirements.txt

COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh
COPY query_service.py ./

ENTRYPOINT [ "./entrypoint.sh" ]