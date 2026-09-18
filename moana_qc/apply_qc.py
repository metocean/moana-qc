"""Quality control test application module."""

from __future__ import annotations

import ast
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

import moana_qc.qc_tests_df as qc_tests
from moana_qc.utils import load_yaml


class QcApply:
    """Apply quality control tests to observational data.

    Takes xarray dataset containing Mangōpare/Moana sensor measurements and applies
    automatic quality control tests.

    Args:
        ds: xarray Dataset with coordinates and variables
        test_list: List of QC test names from qc_tests_df module to apply
        save_flags: Save all individual QC test flags (True) or only global flags (False)
        attr_file: YAML file path containing attribute information
        overwrite_flags: Overwrite existing flags (True) or skip if exists (False)
        logger: Logger instance
    """

    def __init__(
        self,
        ds: xr.Dataset,
        test_list: list[str] | None = None,
        save_flags: bool = False,
        attr_file: str | Path = "attribute_list.yml",
        overwrite_flags: bool = True,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.ds = ds
        self.test_list = test_list or []
        self.save_flags = save_flags
        self.attr_file = Path(attr_file)
        self.overwrite_flags = overwrite_flags
        self.logger = logger

        # Convert to dataframe for QC processing
        self.df = self.ds.to_dataframe().reset_index()
        self.flag_category: dict = {}
        self._success_tests: list = []
        self._tests_not_applied = []
        # initialize dataframe to hold qc flags
        self.qcdf = pd.DataFrame()

    def _run_qc_tests(self):
        """Execute QC tests from test_list on the dataset."""
        for test_name in self.test_list:
            try:
                # from qc_tests_df import *
                # needed for this to work
                # test_name()

                # use this if importing module only
                qc_test = getattr(qc_tests, test_name)
                qc_test(self)
                self._success_tests.append(test_name)
            except Exception as exc:
                self._tests_not_applied.append(test_name)
                self.logger.error(f"Could not apply QC test {test_name}.  Traceback: {exc}")

    def _merge_df_and_ds(self):
        """
        Converts pandas dataframe back to xarray, adds back in
        attributes from original ds.  Updates attributes.
        """
        try:
            if len(self.qcdf.keys()) > 0:
                # if save_flags, add all qc_flags to ds
                # otherwise, only save global qc_flag
                flag_list = self.qcdf.keys() if self.save_flags else self.global_flag_list
                for flag_name in flag_list:
                    varlist = self.ds.data_vars
                    if (
                        (flag_name in varlist)
                        and (flag_name not in self.global_flag_list)
                        and (not self.overwrite_flags)
                    ):
                        continue
                        self.logger.info(
                            f"Not applying qc flag {flag_name} since it already exists."
                        )
                    if (flag_name in varlist) and (flag_name in self.global_flag_list):
                        new = np.array(self.qcdf[flag_name], dtype=np.int8)
                        old = self.ds[flag_name]
                        self.ds[flag_name] = xr.where(old > new, old, new).astype(np.int8)
                    else:
                        self.ds[flag_name] = xr.Variable(
                            dims="DATETIME",
                            data=np.array(self.qcdf[flag_name], dtype=np.int8),
                            attrs={}
                        )
                    self._assign_qc_attributes(self.flag_attrs, flag_name, self.qc_flag_info)
                if "qc_tests_applied" in self.ds.attrs:
                    old = ast.literal_eval(self.ds.attrs["qc_tests_applied"])
                    self._success_tests = old + self._success_tests
                if "qc_tests_failed" in self.ds.attrs:
                    old = ast.literal_eval(self.ds.attrs["qc_tests_failed"])
                    self._tests_not_applied = old + self._tests_not_applied
                self.ds.attrs["qc_tests_applied"] = json.dumps(self._success_tests)
                self.ds.attrs["qc_tests_failed"] = json.dumps(self._tests_not_applied)
        except Exception as exc:
            self.logger.error(f"Could not apply attributes to qc flags. Traceback: {exc}")

    def _load_qc_attrs(self):
        """
        Loads qc variable attributes from attribute_list file
        """
        try:
            self.flag_attrs = load_yaml(self.attr_file, "qc_attr_info")
            self.qc_flag_info = load_yaml(self.attr_file, "qc_flag_info")
            for flag_name in self.qcdf:
                self.flag_category.update({flag_name: self.flag_attrs[flag_name][1]})
        except Exception as exc:
            self.logger.error(
                f"Could not load qc flag attribute data from {self.attr_file}. Traceback: {exc}"
            )

    def _assign_qc_attributes(self, flag_attrs, flag_name, flag_info):
        """
        Uses qc attributes and flag information from
        _load_qc_attrs and applies it to each flag in the
        self.ds dataset
        """
        try:
            long_name = flag_attrs[flag_name][0]
            standard_name = flag_attrs["standard_name"]
            # Parse flag values and create numpy array with same dtype as the variable
            flag_values_str = flag_info["flag_values"]
            if isinstance(flag_values_str, str):
                flag_vals_list = [int(val.strip()) for val in flag_values_str.split(',')]
            else:
                flag_vals_list = list(flag_values_str)
            # Create numpy array with same dtype as the QC flag variable
            flag_values = np.array(flag_vals_list, dtype=self.ds[flag_name].dtype)
            
            flag_meanings = flag_info["flag_meanings"]
            self.ds[flag_name].attrs.update(
                {
                    "long_name": long_name,
                    "standard_name": standard_name,
                    "flag_values": flag_values,
                    "flag_meanings": flag_meanings,
                }
            )
        except Exception as exc:
            self.logger.error(
                f"Could not assign qc attribute {flag_name} due to {exc}, check that it exists in attribute yaml."
            )

    def _global_qc_flag(self):
        """
        Individual QC tests record qc flag in flag_* column.
        Take the maximum value to determine overall qc flag
        for each measurement.
        """
        try:
            self.qcdf["QC_FLAG"] = np.zeros_like(self.df["LONGITUDE"], dtype=np.int8)
            self.qcdf["QC_FLAG"] = self.qcdf.max(axis=1).astype(np.int8)
            self.global_flag_list = ["QC_FLAG"]
            for flag_name, category in self.flag_category.items():
                if category == "None":
                    continue
                if category not in self.global_flag_list:
                    self.global_flag_list.append(category)
                if category not in list(self.qcdf.keys()):
                    self.qcdf[category] = self.qcdf[flag_name].astype(np.int8)
                    continue
                self.qcdf[category] = self.qcdf[[category, flag_name]].max(axis=1).astype(np.int8)
        except Exception as exc:
            self.logger.error(f"Unable to calculate global quality control flag. Traceback: {exc}")

    def run(self):
        try:
            if self.test_list:
                self._run_qc_tests()
            else:
                self.logger.error("No QC tests in list of tests, skipping QC")
            self._load_qc_attrs()
            self._global_qc_flag()
            self._merge_df_and_ds()
            if self._tests_not_applied:
                self.logger.error(
                    f"Unable to apply the following qc tests: {self._tests_not_applied}"
                )
            return self.ds
        except Exception as exc:
            self.logger.error(f"QC testing failed.  Traceback: {exc}")
            raise type(exc)(f"QC testing failed due to: {exc}") from exc
