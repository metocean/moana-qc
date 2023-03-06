FROM python:3.8-slim-buster

ADD . $SOURCE/ops-qc

ARG GIT_TOKEN

RUN pip install -r $SOURCE/ops-qc/requirements/default.txt &&\
    pip install -r $SOURCE/ops-qc/requirements/tests.txt &&\
    pip install $SOURCE/ops-qc

CMD ["/bin/bash"]