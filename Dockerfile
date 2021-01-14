FROM metocean/ops-libs:3.6-buster

ADD . $SOURCE/ops-qc

RUN pip install -r $SOURCE/ops-qc/requirements/default.txt &&\
    pip install -r $SOURCE/ops-qc/requirements/tests.txt &&\
    pip install $SOURCE/ops-qc
