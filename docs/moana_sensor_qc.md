# Moana Sensor Quality Control Documentation

Detailed test descriptions are included in the docstrings of individual tests, as tests may change as improvements are implemented.

## Summary of Quality Control Tests

As the data is being delivered in a near-real-time basis these quality control tests are automatic. All the variables (Temperature, Depth, Longitude, Latitude and Time) and their associated Quality Control Flag (QC_Flag, <variable>_QC) are included in the files that are being delivered and are compliant to GTS standards (WMO, 2020). Given the mangōpare sensor's manufacture specifications and the parameters expected from near-real-time data the quality control process identifies if the measurements are within the accepted range. As per the "standard" oceanographic tests the highest quality data is going to be represented by a QC_Flag value of 1, while the bad data will present a QC_Flag value of 4 (WMO, 2020; U.S. Integrated Ocean Observing System, 2020; Wong et al. 2021). 

Quality control tests are applied to temperature, pressure, time, and position and an overall quality flag is calculated for each variable (the "worst" value for all tests associated with each variable).  Once all tests have been performed, a "global" quality flag is calculated (the "worst" value for all tests for each measurement, incorporating all variables).  A higher quality control flag value cannot be overwritten by a lower value.  If needed, additional quality flags may be added in the future and will be recorded here.

## Recommended Mangōpare QC tests

These are loose recommendations, depending on application, region, and any recent developments.
Currently recommended qc tests in order:

- test_list_1: ['impossible_date', 'impossible_location', 'impossible_speed', 'timing_gap', 'global_range', 'remove_ref_location', 'spike', 'temp_drift', 'stationary_position_check', 'reset_code_check', 'check_timestamp_overflow']
- test_list_2: ['start_end_dist_check']

Stationary_position_check could go in either list, depending on whether this test should be applied to both mobile and stationary gear, or only stationary gear.  Please see [data processing](https://github.com/metocean/moana-qc/docs/moana_sensor_qc.md) documentation for more information on mobile and stationary gear.

## Test Values

Each quality control test has a unique flag name and a value for each measurement in a deployment.  Tests are associated with a variable: DATETIME, LATITUDE and/or LONGITUDE, PRESSURE, and TEMPERATURE.  
For each measurement, test qc flags are aggregated into a single variable qc flag that is appropriate for the test.  These "global" qc flags are: DATETIME_QC, LOCATION_QC, PRESSURE_QC, and TEMPERATURE_QC.  The global qc flags are assigned the lowest qc value of all of the tests that relate to that variable and applied to a given measurement.  The atrribute_list.yml file maps individual test qc flags to their associated global qc flag.
Global qc flags are further aggregated into the overall qc flag called QC_FLAG (need to update this name to something more descriptive).  The simplest level of quality control filtering of a given measurement would use the QC_FLAG variable, as this represents the "worst" value of all tests performed on that measurement.

Quality flag values = [0,1,2,3,4,5]

- QF = 0: QC not performed, unassigned
- QF = 1: Test passed (good data)
- QF = 2: Test failed, but probably still good data
- QF = 3: Test failed, probably bad data
- QF = 4: Test failed, bad data
- QF = 5: Overwritten

## General Quality Control Tests

| Test Name                 | Method Name               | Flag Name              | Variable QC Flag | Recommended | Flag Values |
|---------------------------|---------------------------|------------------------|------------------|-------------|-------------|
| Impossible Date           | impossible_date           | flag_impossible_date   | DATETIME_QC      | yes         | 1, 4         |
| Impossible Location       | impossible_location       | flag_impossible_loc    | LOCATION_QC      | yes         | 1, 4 |
| Remove Reference Location | remove_ref_location       | flag_ref_loc           | LOCATION_QC      | yes         | 1, 4 |
| Timing Gap                | timing_gap                | flag_timing_gap        | DATETIME_QC      | yes         | 1, 4 |
| Datetime Increasing       | datetime_increasing       | flag_datetime_inc      | DATETIME_QC      | yes         | 1, 4 |
| Position on Land          | position_on_land          | flag_land              | LOCATION_QC      | no          | 1, 3 |
| Temperature Global Range  | global_range              | flag_global_range_temp | TEMPERATURE_QC   | yes         | 1, 3 |
| Pressure Global Range     | global_range              | flag_global_range_pres | PRESSURE_QC      | yes         | 1, 3, 4 |
| Temperature Spike         | spike                     | flag_spike_temp        | TEMPERATURE_QC   | yes         | 1, 3 |
| Pressure Spike            | spike                     | flag_spike_pres        | PRESSURE_QC      | yes         | 1, 3 |
| Temperature Stuck Value   | stuck_value               | flag_stuck_value_temp  | TEMPERATURE_QC   | yes         | 1, 3 |
| Pressure Stuck Value      | stuck_value               | flag_stuck_value_pres  | PRESSURE_QC      | yes         | 1, 3 |
| Rate of Change            | rate_of_change_test       | flag_roc               | PRESSURE_QC      | yes         | 1, 3 |
| Temperature Drift         | temp_drift                | flag_temp_drift        | TEMPERATURE_QC   | yes         | 1, 3 |
| Climatology               | climatology_test          | flag_clima             | TEMPERATURE_QC   | no          | 1, 3 |

## Fishing Specific and/or Moana Specific Tests
| Test Name                 | Method Name               | Flag Name              | Variable QC Flag | Recommended |  Flag Values |
|---------------------------|---------------------------|------------------------|------------------|-------------|--------------|
| Stationary Position Check | stationary_position_check | flag_surf_loc          | LOCATION_QC      | yes         | 1, 2, 3 |
| Start End Distance Check  | start_end_dist_check      | flag_dist              | LOCATION_QC      | yes         | 1, 2, 3 |
| Sensor Reset              |                           | flag_dist              | LOCATION_QC      | yes         | 1, 4 |

# Historical Hardware Corrections

## Background Information

 The timestamp arises when a Moana comes out of a dive, and then sits in the dry state without being offloaded for more than 18.2 hours, and then goes back into a dive event. This results in the times of the second and subsequent dives being inaccurate.

Moana sensors with the firmware versions 1.09 and 1.10 had an issue with a non-zero timestamp offset being used for the first sample. This was resolved in deck unit firmware version 2.35 by ignoring the offset for the first timestamp as it must, by definition, always be zero.
Locations of 0.0,0.0 should be considered invalid for deck unit firmware versions older than 4.06
 
These rules affect the sample where the rule was triggered all subsequent samples to the end of the file:

Samples after a reset:
If the reset is the first sample and the download time is more than 65535 seconds after the reset timestamp.
If the reset is not the first sample.
Samples with a timestamp after the download.
Samples with a timestamp that is older than the previous sample’s timestamp (i.e. a negative timestamp offset).
Samples from a subsequent dive if the download time was more than 65535 seconds after the sensor surfaced from its first dive.

First check if the Moana firmware version is >= 2.00. This firmware has been updated to ensure correct timestamps in the following scenarios:

Samples after a reset will now have valid timestamps.
Any previously recorded samples are erased if the Moana is reset and loses track of elapsed time.
Samples from a subsequent dive will now have valid timestamps.
‘Placeholder’ samples will be logged every 12hrs between dives to maintain a contiguous series of delta times and avoid an integer overflow.