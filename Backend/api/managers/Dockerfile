FROM ubuntu:16.04

RUN "sh" "-c" "echo nameserver 8.8.8.8 >> /etc/resolv.conf"
RUN "sh" "-c" "echo nameserver 147.88.112.200 >> /etc/resolv.conf"
RUN "sh" "-c" "echo nameserver 147.117.20.200 >> /etc/resolv.conf"
RUN "sh" "-c" "echo nameserver 146.11.115.200 >> /etc/resolv.conf"

RUN apt-get update && apt-get install -y \
    wget git build-essential autoconf curl python gcc python-dev \
    libtool libffi-dev libssl-dev libxml2-dev libxslt1-dev libjpeg8-dev zlib1g-dev

RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py
RUN mkdir -p /usr/src/node-manager
COPY ./  /usr/src/node-manager/

RUN pip install -r /usr/src/node-manager/requirements.txt

EXPOSE 5001

WORKDIR /usr/src/node-manager
CMD ["python","/usr/src/node-manager/api.py"]