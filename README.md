# Moana TD Sensor Quality Control and Processing

This library contains code initially intended for the operational, near real-time quality-control of Mangōpare/Moana oceanographic observation data (https://www.moanaproject.org/temperature-sensors, https://www.zebra-tech.co.nz/moana/).  Only automatic quality control is included at this time, for use with measurements transmitted in near real-time.  For more information on the sensor programme, see Jakoboski et. al, 2023, in preparation, contact info@moanaproject.org, or visit the websites above.

The current versions are for the purpose of quality-controlling data from the Moana Project's Mangopare (Te Tiro Moana) Mangōpare/Moana temperature and pressure sensor, but will be made more generic if needed.

---
# Current Notes
The master branch is currently intended for MetOcean operational use.  The external-aus branch is intended for development by the IMOS Fish-SOOP programme.  Please contact info@moanaproject.org if you'd like to create a new branch for development by your organisation.

---
## Some to-dos
- Add remaining qc tests (time checks from deck unit issue, grey list, qc reset check, calibration check, datetime after offload, datetime increasing)
- Improve netcdf format/attributes/etc.
- Change "mobile" to "towed" and "stationary" to "passive."  Not that important but more accurate names.
- Complete and fix unittests.
- Improve documentation.

---
## Code structure
- wrapper.py is the highest level class, which coordinates all the others.  Within it, the user specifies the data reader, the metadata reader, a preprocessor, and the qc_class.
- Data reader: reads the observations in each sensor offload file, formats variable names, and loads global attributes from the file header.
- Metadata reader: right now, reads a spreadsheet with fisher metadata, including whether the sensor is stationary or mobile.
- Preprocessor: very Mangopare specific, mostly does position processing.  Also adds variable attributes from attribute file specified in wrapper.py and finds the "bottom" data points for fishing data.
- QC class: specifies the class that actually applies the QC tests after reading and preprocessing the data.

Defaults for the above are included in wrapper.py in case none are specified.

Currently, the data and metadata readers are both classes in readers.py.

---
## Stationary vs mobile gear
Fishing methods (or any other deployment method) are dividing into two categories for processing: "stationary" or "mobile."  (Should be "passive" or "towed" in the future).  Towed is simply gear towed behind a moving vessel.  In this case, the sensor is always assumed to be in the same location as the vessel.  Stationary gear is gear that is detached form the vessel (i.e. potting).  All measurements in a stationary deployment are currently given the same position, which is the average between the first and last "good" location as recorded by the deck unit.  If the first or last position is not near the surface, the stationary position cannot be calculated and processing will fail (see qc test "stationary_position_check" in qc_tests_df.py).

---
## Quality control summary
"Standard" oceanographic QC tests for temperature and pressure data are included in qc_tests_df.py.  Most of these are based on QARTOD or Argo tests.  If any new tests are needed, that is most likely the best place to put them.  For each test, a quality flag is assigned:  

Quality flag values = [0,1,2,3,4]

- QF = 0: QC not performed
- QF = 1: Test passed (good data)
- QF = 2: Test failed, but probably still good data
- QF = 3: Test failed, probably bad data
- QF = 4: Test failed, bad data
Once all tests have been performed, a "global" quality flag is calculated (the "worst" value for all tests for each measurement).

The tests from qc_test_df.py that should be included in a quality-control run are specified in warpper.py under the variable name `test_list`.  This variable is passed to apply_qc.py where each test is run.  See qc_tests_df.py documentation for lists of possible test names.  Some tests generally work well, others currently not at all.  This is indicated in the qc_tests_df.py docstring.

Right now, tests in qc_tests_df need a pandas dataframe with LONGITUDE, LATITUDE, DATETIME, TEMPERATURE, and PRESSURE fields.  At some point this will be generalised.

---
## Recommended Mangōpare QC tests
These are loose recommendations, depending on application, region, and any recent developments.
Currently recommended qc tests in order:

- test_list_1: ['impossible_date', 'impossible_location', 'impossible_speed', 'timing_gap', 'global_range', 'remove_ref_location', 'spike', 'temp_drift', 'stationary_position_check']
- test_list_2: ['start_end_dist_check']

Stationary_position_check could go in either list, depending on whether this test should be applied to both mobile and stationary gear, or only 
stationary gear.

---
## File Format
Currently, all QC'd files are saved in netCDF format (see wrapper.py).  If needed, additional formats can be added.  The user can choose whether to save quality flags for all individual tests or only save the global quality flag.

---
## Status file
Each time the wrapper is run on a list of files, a status file (csv) is created with information on any errors that may have occurred during processing.  This file is saved in the same directory as the output quality controlled nc files.  Note that all of this is in beta, so will be improved in the future.

---
## Installation: Building and running the docker image

The metocean/moana-qc repository contains a default (external) [`Dockerfile`](https://github.com/metocean/moana-qc/blob/master/Dockerfile) and an internal operational [`Dockerfile_internal`](https://github.com/metocean/moana-qc/blob/master/Dockerfile_internal).  To build a new image, external users want to use the default `Dockerfile` (which is independent of MetOcean's internal libraries).  For MetOcean operational internal use, please build from `Dockerfile_internal`.

To build the external use Dockerfile version (outside of Metservice/MetOcean ops system), from the moana-qc directory, use something like: 
```shell
docker build -f Dockerfile -t moana-qc .
```

The metocean/moana-qc/Dockerfile docker image requires some libraries in private git repositories, but are needed for the current operational version at MetOcean.  They are accessed via a github token.  To run from a computer with the github token under variable GIT_TOKEN, build the docker image via

```shell
docker build -f Dockerfile_MOS --no-cache --build-arg GIT_TOKEN=${GIT_TOKEN} -t metocean/moana-qc:latest .
```

Then run the docker image via

for default use:
```shell
docker run -ti -v /source:/source -v /data:/data moana-qc:latest
```

or for MetOcean internal use:
```shell
docker run -ti -v /source:/source -v /data:/data metocean/moana-qc:latest`
```

`/data` is a directory where the sensor data can be found and also where the output directory will be.  If you need the docker container to access another directory, add it with the -v tag.

---
## Other repository notes

Need to work on unittests and setup.py...feel free to contribute in this space!

---
## Licensing
Please see LICENSE.md for the license under which this code can be shared.  Please consider contributing to the code under this repository whenever possible rather then forking or cloning into a new repository so all can benefit from collaborative work.  If you need to fork/clone into a new repository, please let us know so we can include any new developments as a community.

---
## Attribution Statement
Original code base by MetOcean Solutions, a Division of Meteorological Service of New Zealand Ltd, developed as part of the Moana Project. The Moana Project is funded by the New Zealand Ministry of Business, Innovation, and Employment (MBIE) Endeavour Fund.

Contributors to the current version in include: MetOcean Solutions, Berring Data Collective

The Mangōpare sensor and deck unit hardware were developed by Zebra-Tech, Ltd, Nelson, New Zealand as part of the Moana Project.  Sensors are available through https://www.zebra-tech.co.nz/

---
## Community
A fishing vessel, in-situ ocean observing quality control working group is in development through FVON (https://fvon.org/).  Please contact either the Moana Project (info@moanaproject.org) or FVON (through their website) for more information.

---


