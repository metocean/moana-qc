# ops-qc

This library contains code initially intended for the operational, near real-time quality-control of Mangōpare/Moana oceanographic observation data.  Only automatic quality control is included at this time, for use with measurements transmitted in near real-time.

The first versions are for the purpose of quality-controlling data from the Moana Project's Mangopare (Te Tiro Moana) Mangōpare/Moana temperature and pressure sensor, but will be made more generic when needed.

---
# Current Notes
Master branch is currently intended for MetOcean operational use.  The external-aus branch is intended for development use by the IMOS Fish-SOOP programme.

---
## Some to-dos
Add remaining qc tests (time checks from deck unit issue, grey list, qc reset check, calibration check, datetime after offload, datetime increasing)
Improve netcdf format/attributes/etc.
Change "mobile" to "towed" and "stationary" to "passive."  Not that important but more accurate names.
Complete and fix code unittests.
Improve documentation.

---
## Code structure
wrapper.py is the highest level class, which coordinates all the others.  Within it, the user specifies the data reader, the metadata reader, a preprocessor, and the qc_class.
Data reader: reads the observations in each sensor offload file, formats variable names, and loads global attributes from the file header.
Metadata reader: right now, reads a spreadsheet with fisher metadata, including whether the sensor is stationary or mobile.
Preprocessor: very Mangopare specific, mostly does position processing.  Also adds variable attributes from attribute file specified in wrapper.py and finds the "bottom" data points for fishing data.
QC class: specifies the class that actually applies the QC tests after reading and preprocessing the data.

Defaults for the above are included in wrapper.py in case none are specified.

Currently, the data and metadata readers are both classes in readers.py.

---
## Quality control summary
"Standard" oceanographic QC tests for temperature and pressure data are included in qc_tests_df.py.  Most of these are based on QARTOD or Argo tests.  If any new tests are needed, that is most likely the best place to put them.  The tests in qc_test_df.py were originally provided by the Berring Data Collective, then modified at MetOcean.  For each test, a quality flag is assigned:  
Quality flag values = [0,1,2,3,4]
QF = 0: QC not performed
QF = 1: Test passed (good data)
QF = 2: Test failed, but probably still good data
QF = 3: Test failed, probably bad data
QF = 4: Test failed, bad data
Once all tests have been performed, a "global" quality flag is calculated (the "worst" value for all tests for each measurement).

The tests from qc_test_df.py that should be included in a quality-control run are specified in warpper.py under the variable name `test_list`.  This variable is passed to apply_qc.py where each test is run.  See qc_tests_df.py documentation for lists of possible test names.  Some tests generally work well, others currently not at all.  This is indicated in the qc_tests_df.py docstring.

Right now, tests in qc_tests_df need a pandas dataframe with LONGITUDE, LATITUDE, DATETIME, TEMPERATURE, and PRESSURE fields.  At some point this will be generalised.

---
## Recommended Mangōpare QC tests
Currently recommended qc tests in order:
test_list_1: ['impossible_date', 'impossible_location', 'impossible_speed', 'timing_gap', 'global_range', 'remove_ref_location', 'spike', 'temp_drift', 'stationary_position_check']
test_list_2: ['start_end_dist_check']
Stationary_position_check could go in either list, depending on whether this test should be applied to both mobile and stationary gear, or only 
stationary gear.

---
## File Format
Currently, all QC'd files are saved in netCDF format (see wrapper.py).  If needed, additional formats can be added.  The user can choose whether to save quality flags for all individual tests or only save the global quality flag.

---
## Status file
Each time the wrapper is run on a list of files, a status file (csv) is created with information on any errors that may have occurred during processing.  This file is saved in the same directory as the output quality controlled nc files.  Note that all of this is in beta, so will be improved in the future.

---
## Building and running the docker image

Current latest version of docker image: ops-qc:v0.1.12-dev.

The metocean/ops-qc docker image requires some libraries in private git repositories.  They are accessed via a github token.  To run from a computer with the github token under variable GIT_TOKEN, build the docker image via

`docker build --no-cache --build-arg GIT_TOKEN=${GIT_TOKEN} -t metocean/ops-qc:latest .`

Then run the docker image via something like

`docker run -ti -v /source:/source -v /data:/data metocean/ops-qc:latest`

In the future, github actions will do this also.

---
## Other notes

Currently github actions is disabled on this repository, until I'm done writing them.  To turn back on in github, go to Settings, Actions (left menu), Actions permissions, choose 'Allow all actions'.

---

Gradually working on unittests/learning how to  write them.  Making slow progress...

---

More information will be included here as the library progresses.
