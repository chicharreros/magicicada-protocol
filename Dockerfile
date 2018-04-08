FROM ubuntu:16.04

ADD . /home/ubuntu/magicicada
COPY . /home/ubuntu/magicicada
WORKDIR /home/ubuntu/magicicada

RUN apt update && apt install make gcc python python-dev virtualenv -y --no-install-recommends
RUN make bootstrap

RUN useradd -ms /bin/bash ubuntu
RUN chown -R ubuntu:ubuntu /home/ubuntu

USER ubuntu
ENV HOME /home/ubuntu
