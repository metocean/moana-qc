import logging

import requests


class CheckFishserve:
    """
    Read FishServe database and compare to fisher metadata.
    Inputs:
        vessel_num = vessel registration number (painted on hull)
    """

    def __init__(
        self,
        vessel_num,
        logger=logging,
        apiEndpoint="https://licence.uat.kupe.fishserve.co.nz/api/vessels/get/",
        **kwargs,
    ):

        self.vesel_num = vessel_num
        self.apiEndpoint = apiEndpoint
        self.logger = logging

    def request_data(self, apiEndpoint):
        url = apiEndpoint + str(self)
        r = requests.get(url)
        return r.json()

    def run(self):
        self.request_data(self.vessel_num, self.apiEndpoint)

        pass
