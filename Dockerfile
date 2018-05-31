FROM ubuntu:latest

MAINTAINER Luca Valtulina "valtulina.luca@gmail.com"

RUN apt-get update -y
RUN apt-get install -y python-pip python-dev python-mysqldb build-essential

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY ./loan /loan

COPY ./users.csv /usr/local/share/users.csv