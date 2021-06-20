  
FROM ubuntu:20.04

RUN apt-get update 
RUN DEBIAN_FRONTEND='noninteractive' apt-get install -y --no-install-recommends \
    pkg-config \
    libpng-dev \
    libjpeg8-dev \
    libfreetype6-dev \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    libsndfile1-dev \
    gfortran \
    python3 \
    python3-dev \
    python3-pip \
    curl \
    g++
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash
RUN DEBIAN_FRONTEND='noninteractive' apt-get install -y nodejs

COPY ./server_hmm/requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

COPY ./server_hmm/ /src/server_hmm/
COPY ./static/ /src/static/

WORKDIR /src/static/
# RUN npm install
RUN npm install
# RUN npm rebuild node-sass
RUN npm run build

WORKDIR /src/server_hmm/

EXPOSE 8080
CMD [ "python3", "server.py" ]