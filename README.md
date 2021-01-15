# ops-qc

This library contains data quality-control code initially intended for the quality-control of oceanographic observation data.  Only automatic quality control is included at this time, for use with near real-time data.

The first versions are for the purpose of quality-controlling data from the Moana Project's Mangopare (Te Tiro Moana) temperature and pressure sensor, but will be made more generic when convenient.

---

## Building and running the docker image
The metocean/ops-qc docker image requires some libraries in private git repositories.  They are accessed via a github token.  To run from a computer with the github token under variable GIT_TOKEN, build the docker image via 

`docker build --build-arg GIT_TOKEN=${GIT_TOKEN} -t metocean/ops-qc .`

Then run the docker image via something like

`docker run -ti -v /source:/source -v /data:/data metocean/ops-qc:latest`

---
## Other notes

Currently github actions is disabled on this repository, until I'm done writing them.  To turn back on in github, go to Settings, Actions (left menu), Actions permissions, choose 'Allow all actions'.

---

More information will be included here as the library progresses.