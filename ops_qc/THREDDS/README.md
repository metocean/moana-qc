# The Mang&omacr;pare Sensor Programme 
# Moana TD Sensor

This dataset contains temperature and pressure data obtained for the Moana Project's Mang&omacr;pare Sensor Programme (https://www.moanaproject.org/temperature-sensors), using Moana TD sensors (https://www.zebra-tech.co.nz/moana/).  Data are provided operationally, in near real-time, and this THREDDS directory is currently updated every two hours.

Only automatic quality control is included at this time, for use with measurements transmitted in near real-time.  For more information on the sensor programme, see Jakoboski et. al, 2023, in preparation, contact info@moanaproject.org, or visit the websites above.

THREDDS subsetting is not yet available, but hopefully will be in the near future.

This the very first public release of these data, and as such, we expect to make improvements as we go.  Please submit feedback to info@moanaproject.org and we will incorporate any comments as soon as we can.  We are also interested in any uses of the data, so please let us know and we will include it in our publications list on the Moana Project website.

---
## Licensing
This dataset is available for use under the Creative Commons Attribution 4.0 International License.

---
## Atrribution Statement
Data quality-control and processing provided by MetOcean Solutions, a Division of the Meteorological Service of New Zealand.  Mang&omacr;pare sensor and deck unit provided by Zebra-Tech, Ltd, Nelson, New Zealand as part of the Moana Project.  This work is a contribution to the Moana Project (www.moanaproject.org) funded by the New Zealand Ministry of Business Innovation and Employment, contract number METO1801.

---
## Acknowledgements
We would like to acknowledge all programme participants who volunteer their time and temperature measurements for the benefit of the users of the Mang&omacr;pare Sensor Programme Data.  

---
## Disclaimer
By using the data that Meteorological Service of New Zealand Limited (MetService) makes available on this platform, you agree to this disclaimer.  The data is supplied by third parties to MetService and is aggregated and anonymised by MetService.  MetService does not independently check the data to ensure it is correct, accurate, complete, current, or suitable for use.  The data is made available by MetService on as is and as available basis.  You agree that any reliance you place on the data, including any analysis of, or decision you make based on, the data (or that analysis) is at your own risk.  You agree that MetService has no responsibility or liability for the data (or for any error or omission in the data) or for how you use that data.  To the maximum extent permitted by law, MetService disclaims all warranties, conditions, guarantees, and/or representations relating to the data and how you use that data.

---
## Data Format
Currently, data are available in netCDF format.  If needed, additional formats can be added.  Each file contains coordinates, variables, and ancillary variables.  Filenames are of the format: MOANA_yyyymmdd_hhmmss_published.nc, which reflects the date and timestamp of the file offload from the sensor to the deck unit.

### Coordinates:
    TIME:
      long_name: 'time'
      standard_name: 'time'
      axis: 'T'
      valid_max: 999999.
      valid_min: 0.
      ancillary_variables: "TIME_QC"
    LATITUDE: 
      long_name: 'latitude'
      reference_datum: 'WGS84 geographic coordinate system'
      standard_name: 'latitude'
      units: 'degrees_north'
      _FillValue: 99999.
      valid_max: 90.
      valid_min: -90.
      ancillary_variables: "POSITION_QC"
    LONGITUDE:
      long_name: 'longitude'
      reference_datum: 'WGS84 geographic coordinate system'
      standard_name: 'longitude'
      units: 'degrees_east'
      _FillValue: 99999.
      valid_max: 180.
      valid_min: -180.
      ancillary_variables: "POSITION_QC"

### Variables:

    TEMPERATURE:
        long_name: 'sea temperature in-situ ITS-90 scale'
        standard_name: 'sea_water_temperature'
        _FillValue: 99999.
        coordinates: 'LONGITUDE, LATITUDE'
        units: 'degree_Celsius'
        valid_min:  -20.
        valid_max: 35.
        resolution: 0.001
        ancillary_variables: "TEMP_QC"
        observation_type = "measured"
    DEPTH:
        long_name: 'DEPTH'  
        standard_name: 'depth'
        _FillValue: 99999.
        coordinates: 'LONGITUDE, LATITUDE'
        units: 'm'
        axis: 'z'
        positive: 'down'
        valid_min:  0.
        valid_max: 1000.
        resolution: 0.1 
        ancillary_variables: "DEPTH_QC"
        observation_type = "computed"
        comment = "Depth computed using Gibbs-SeaWater toolbox (TEOS-10), from latitude and relative pressure measurements" ;
    PRESSURE:
        long_name: 'PRESSURE'  
        standard_name: 'pressure'
        _FillValue: 99999.
        coordinates: 'LONGITUDE, LATITUDE'
        units: 'dbar'
        axis: 'z'
        valid_min:  0.
        valid_max: 1000.
        resolution: 0.1 
        ancillary_variables: "PRESSURE_QC"
        observation_type = "measured"

### Ancillary quality control variables:

    TIME_QC:
      long_name: 'Time Quality Flag'
      standard_name: 'time status_flag'
      coordinates: 'LONGITUDE, LATITUDE'
      conventions: 'FVON standard flags'
      flag_meanings:  'No QC Applied | Good | Probably Good | Probably Bad | Bad | Overwritten'
      flag_values: '0, 1, 2, 3, 4, 5' 
    POSITION_QC:
      long_name: 'Position Quality Flag'
      standard_name: 'location status_flag'
      coordinates: 'LONGITUDE, LATITUDE'
      conventions: 'FVON standard flags'
      flag_meanings:  'No QC Applied | Good | Probably Good | Probably Bad | Bad | Overwritten'
      flag_values: '0, 1, 2, 3, 4, 5'
    TEMP_QC:
      long_name: 'Temperature Quality Flag'
      standard_name: 'sea_water_temperature status_flag'
      coordinates: 'LONGITUDE, LATITUDE'
      conventions: 'FVON standard flags'
      flag_meanings:  'No QC Applied | Good | Probably Good | Probably Bad | Bad | Overwritten'
      flag_values: '0, 1, 2, 3, 4, 5' 
    DEPTH_QC:
      long_name: 'Depth Quality Flag'
      standard_name: 'depth status_flag'
      coordinates: 'LONGITUDE, LATITUDE'
      conventions: 'FVON standard flags'
      flag_meanings:  'No QC Applied | Good | Probably Good | Probably Bad | Bad | Overwritten'
      flag_values: '0, 1, 2, 3, 4, 5'
    PRESSURE_QC:
      long_name: 'Pressure Quality Flag'
      standard_name: 'pressure status_flag'
      coordinates: 'LONGITUDE, LATITUDE'
      conventions: 'FVON standard flags'
      flag_meanings:  'No QC Applied | Good | Probably Good | Probably Bad | Bad | Overwritten'
      flag_values: '0, 1, 2, 3, 4, 5'

### Global QC flag
A global QC flag indicates the overall quality of each measurement, incorporating all ancillary QC variables:

    QC_FLAG: 
      long_name: 'Global Quality Flag'
      standard_name: 'Global status_flag'
      coordinates: 'LONGITUDE, LATITUDE'
      conventions: 'FVON standard flags'
      flag_meanings:  'No QC Applied | Good | Probably Good | Probably Bad | Bad | Overwritten'
      flag_values: '0, 1, 2, 3, 4, 5'

---
## Quality control summary
"Standard" oceanographic QC tests for temperature and pressure data are applied.  Most of these are based on QARTOD or Argo tests.  A quality flag is assigned to each variable as an ancillary variable:  

Quality flag values = [0,1,2,3,4]

- QF = 0: QC not performed
- QF = 1: Test passed (good data)
- QF = 2: Test failed, but probably still good data
- QF = 3: Test failed, probably bad data
- QF = 4: Test failed, bad data
Once all tests have been performed, a "global" quality flag is calculated (the "worst" value for all tests for each measurement), called "QC_FLAG."

A list of QC tests to applied to a file are included under the `quality_control_log` attribute.

---
## Position Information
Reported measurement positions are derived from the vessel position.  Fishing methods (or any other deployment method) are dividing into two categories for processing: "stationary" or "mobile."  (Should be "passive" or "towed" in the future).  Towed is simply gear towed behind a moving vessel.  In this case, the sensor is always assumed to be in the same location as the vessel.  Stationary gear is gear that is detached form the vessel (i.e. potting).  All measurements in a stationary deployment are currently given the same position, which is the average between the first and last "good" location as recorded by the deck unit.  If the first or last position is not near the surface, the stationary position cannot be calculated and processing will fail.  

Please see the QC github repository (https://github.com/metocean/moana-qc) for additional details on position processing.

---
## Files are provided anonymously
Note that anyone who is part of the Mang&omacr;pare Sensor Programme can deploy a sensor.  This includes a wide range of vessels, including fishing, industry, research, recreational, and citizen science vessels.

---
## Other repository notes

This README.md is under development and will be updated in the near future!

---
## Community
A fishing vessel, in-situ ocean observing quality control working group is in development through FVON (https://fvon.org/).  Please contact either the Moana Project (info@moanaproject.org) or FVON (through their website) for more information.





