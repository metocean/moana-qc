Moana Sensor Quality Control Documentation

Detailed test descriptions are included in the docstrings of individual tests, as tests may change as improvements are implemented.

# Summary of Quality Control Tests

## Test Values
Each quality control test has a unique flag name and a value for each measurement in a deployment.  Tests are associated with a variable: DATETIME, LATITUDE and/or LONGITUDE, PRESSURE, and TEMPERATURE.  
For each measurement, test qc flags are aggregated into a single variable qc flag that is appropriate for the test.  These "global" qc flags are: DATETIME_QC, LOCATION_QC, PRESSURE_QC, and TEMPERATURE_QC.  The global qc flags are assigned the lowest qc value of all of the tests that relate to that variable and applied to a given measurement.  The atrribute_list.yml file maps individual test qc flags to their associated global qc flag.
Global qc flags are further aggregated into the overall qc flag called QC_FLAG (need to update this name to something more descriptive).  The simplest level of quality control filtering of a given measurement would use the QC_FLAG variable, as this represents the "worst" value of all tests performed on that measurement.

Flag values are: 0 (unassigned), 1 (good), 2 (probably good), 3 (probably bad), 4 (bad), 5 (overwritten)


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
 
May affect files with the following traits:

*Resets.
*Any sample time stamp that is newer than the download time.
*Any sample time stamp that is older than the previous time stamp.
*Any sample time stamp that is more than 5 minutes newer than the previous timestamp and the previous timestamp is more than 18.2hrs older than the download time.
This second condition allows us to determine if sufficient time had elapsed for a time offset overflow to have occurred.
*Any sample depth that is greater than 1.0m where the previous depth had been less than 1.0m and the previous timestamp is more than 18.2hrs older than the download time.
This indicates that there are potentially multiple dive events that occurred more than 18.2 hours before the download time.
*Any invalid timestamp
The list of possibly affected files is attached. He can share the Python processing code with you if you like.  We have a solution for both the reset and time overflow issue, and will release it this week to new Moana’s moving forward.

Updated info:

These rules affect the entire file:

Data from sensors with the serial number 0 or 997 and greater should be discarded for now, until 4 digit serial numbers are implemented.
Moana sensors with the firmware versions 1.09 and 1.10 had an issue with a non-zero timestamp offset being used for the first sample. This was resolved in deck unit firmware version 2.35 by ignoring the offset for the first timestamp as it must, by definition, always be zero.
Files with sample locations with 25m of the Zebra Tech workshop are discarded, as they likely have test data.
Files with no valid sample locations are discarded.
Locations of 0.0,0.0 should be considered invalid for deck unit firmware versions older than 4.06
Files with any csv format corruption.
 
These rules affect the sample where the rule was triggered all subsequent samples to the end of the file:

Samples with an invalid timestamp format.
Samples after a reset:
If the reset is the first sample and the download time is more than 65535 seconds after the reset timestamp.
If the reset is not the first sample.
Samples with a timestamp after the download.
Samples with a timestamp that is older than the previous sample’s timestamp (i.e. a negative timestamp offset).
Samples from a subsequent dive if the download time was more than 65535 seconds after the sensor surfaced from its first dive. The end of the first dive is indicated by:
A gap of more than the log interval minutes (default is 5 minutes) between samples or
A depth less than 2.0m or
A reset (as any subsequent dive sample will be stored with a relative time offset)
 
Note: increased the depth rule from 1.0m to 2.0m to better match the dive/surface logic in the sensor. This rule will trigger a number of false positives so need to think of a more specific check.

First check if the Moana firmware version is >= 2.00. This firmware has been updated to ensure correct timestamps in the following scenarios:

Samples after a reset will now have valid timestamps.
Any previously recorded samples are erased if the Moana is reset and loses track of elapsed time.
Samples from a subsequent dive will now have valid timestamps.
‘Placeholder’ samples will be logged every 12hrs between dives to maintain a contiguous series of delta times and avoid an integer overflow.