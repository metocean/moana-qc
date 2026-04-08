# Mangōpare/Moana Sensor-specific Processing

Moana sensors are designed for mounting on a range of commercial fishing and other types of gear that are deployed below the ocean's surface.  Measurement geospatial position (longitude, latitude) is based on vessel position.  There are specific processing routines that apply to these types of measurements.  This doc covers processing and file format information.

## Stationary vs mobile gear

Fishing methods (or any other deployment method) are dividing into two categories for processing: "stationary" or "mobile."  (Should be "passive" or "towed" in the future).  Towed is simply gear towed behind a moving vessel.  In this case, the sensor is always assumed to be in the same location as the vessel.  Stationary gear is gear that is detached form the vessel (i.e. potting).  All measurements in a stationary deployment are currently given the same position, which is the average between the first and last "good" location as recorded by the deck unit.  If the first or last position is not near the surface, the stationary position cannot be calculated and processing will fail (see qc test "stationary_position_check" in qc_tests_df.py).

## File Format
Currently, all QC'd files are saved in netCDF format (see wrapper.py).  If needed, additional formats can be added.  The user can choose whether to save quality flags for all individual tests or only save the overall variable and global quality flags.

## Status file
Each time the wrapper is run on a list of files, a status file (csv) is created with information on any errors that may have occurred during processing.  This file is saved in the same directory as the output quality controlled nc files.  Note that all of this is in beta, so will be improved in the future.