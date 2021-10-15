FROM metocean/ops-libs:3.6-master

ADD . $SOURCE/ops-qc

ARG GIT_TOKEN

RUN pip install -r $SOURCE/ops-qc/requirements/default.txt &&\
    pip install -I -r $SOURCE/ops-qc/requirements/opslibs.txt &&\
    pip install -r $SOURCE/ops-qc/requirements/tests.txt &&\
    pip install $SOURCE/ops-qc

CMD ["/bin/bash"]
