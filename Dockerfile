# Base image
FROM python:3.6

# Maintainer
MAINTAINER Patrick Lombard<patrick.lombard@gosh.nhs.uk>
# Install prequisites (last four entries added by me - PD)
RUN apt-get update && apt-get -y install \
    libpq-dev \
    cpanminus \
    build-essential \
    git \
    unzip \
    curl \
    python-pip \
    libpango1.0-0 \
    libcairo2 \
    zlib1g-dev \
    vim \
    mysql-server \
    default-libmysqlclient-dev \
    software-properties-common \
    screen

# RUN add-apt-repository ppa:webupd8team/java
RUN apt-get update
RUN apt-get install -y --allow-unauthenticated python3-dev python3-pip python3-virtualenv \
    libsasl2-dev libldap2-dev libssl-dev
RUN apt-get install -y curl

# Install VEP Perl dependencies
WORKDIR /root
COPY DBI-1.643.tar.gz /root
RUN tar -xvzf DBI-1.643.tar.gz
WORKDIR DBI-1.643
RUN perl Makefile.PL
RUN make && make install


# Install VEP. Using version 92 as per Gel2MDT Readme.  AUTO prevents prompts and -n prevents attempts to update
# which otherwise cause an unattended install to fail.
WORKDIR /root
RUN git clone https://github.com/Ensembl/ensembl-vep.git
WORKDIR /root/ensembl-vep
RUN git checkout release/91
RUN perl INSTALL.pl --VERSION 91 --AUTO ap -n --PLUGINS all

# Install Gel2MDT
RUN mkdir /root/gel2mdt
COPY . /root/gel2mdt
WORKDIR /root/gel2mdt
# This is already installed with Anaconda and fails to 'downgrade'. Remove from requirements file?
RUN sed -i 's/certifi==/# certifi==/g' requirements.txt
RUN pip install -r requirements.txt
# Install GelReportModels
RUN pip install gelreportmodels==7.8.0 --no-dependencies

RUN pip install gunicorn
RUN pip install mysqlclient
# RUN pip install pip install Werkzeug
