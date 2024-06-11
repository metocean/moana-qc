FROM python:3.8-slim-buster

ADD . $SOURCE/moana-qc

ARG GIT_TOKEN

RUN apt-get update && apt-get install -y build-essential

RUN pip install -r $SOURCE/moana-qc/requirements/default.txt &&\
    pip install -r $SOURCE/moana-qc/requirements/tests.txt &&\
    pip install $SOURCE/moana-qc

CMD ["/bin/bash"]