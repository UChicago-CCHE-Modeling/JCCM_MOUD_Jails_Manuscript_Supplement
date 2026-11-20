# This file is part of the Justice Community Circulation Model
#
# Medication to treat Opioid Use Disorder
# 

import os
import pandas as pd

from .jccm_enums import *
from .constants import *

from repast4py import parameters

MOUD_TYPE = 'moud_type'
MOUD_JAIL_WAIT_TIME = 'moud_jail_wait_time'
MOUD_JAIL_ACCEPT_RATE = 'moud_jail_accept_rate'
MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE = 'moud_therapeutic_days_after_last_dose'
MOUD_TIME_ON_TREATMENT = 'moud.time.on.treatment'
MOUD_OD_RISK = 'moud.od.risk'
MOUD_REARREST_RISK = 'moud.rearrest.risk'

MOUD_TIME_NAME = 'moud_name'
MOUD_TIME_DAYS = 'days'
MOUD_TIME_FRACTION = 'fraction'

class MOUD():

    def __init__(self, moud_data:dict):
        

        # TODO impact on overdose/use
        # TODO impact on recidivism

        # NOTE protected properties since we don't want to ever overwrite these
        self._type = moud_data[MOUD_TYPE]
        self._name = self.type.value
        self._jail_wait_time = moud_data[MOUD_JAIL_WAIT_TIME]
        self._jail_accept_rate = moud_data[MOUD_JAIL_ACCEPT_RATE]
        self._therapeutic_days_after_last_dose = moud_data[MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE]
        self._od_risk = moud_data[MOUD_OD_RISK]
        self._rearrest_risk = moud_data[MOUD_REARREST_RISK]
        
        # Time on treatment is a dict of days->[] and probs->[] that correspond
        # to the histogram data for time on treatment.
        # TODO warn if missing in the input CSV file
        self._time_on_treatment = moud_data[MOUD_TIME_ON_TREATMENT]

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def type(self) -> MoudType:
        return self._type
    
    @property
    def jail_wait_time(self) -> float:
        return self._jail_wait_time
    
    @property
    def jail_accept_rate(self) -> float:
        return self._jail_accept_rate
    
    @property
    def therapeutic_days_after_last_dose(self) -> float:
        return self._therapeutic_days_after_last_dose
    
    @property
    def time_on_treatment(self) -> dict:
        return self._time_on_treatment
    
    @property
    def od_risk(self) -> float:
        return self._od_risk
    
    @property
    def rearrest_risk(self) -> float:
        return self._rearrest_risk

    def __str__(self):
        """ Returns the name of the MOUD.
        """
        return self.name

class MOUD_Library:
    """ Library of available MOUD medications.
    
    Attributes
    ----------
    __instance : MOUD_Library
        MOUD_Library singleton
    
    
    """
    
    __instance = None
   
    @staticmethod 
    def getInstance():
        return MOUD_Library.__instance
   
    def __init__(self):
        """Constructor
        
        Parameters
        ----------
        
        """
        
        MOUD_Library.__instance = self

        data_dir = parameters.params[DATA_DIR]
        time_on_treatment_file = os.path.join(data_dir,parameters.params[MOUD_TIME_ON_TREATMENT_FILE])
        time_treat_dict = load_moud_time_treatment(time_on_treatment_file)

        # TODO load medicine specific data via CSV and SA params like wait time should be the same for all meds

        moud_data_list = [
            {MOUD_TYPE:MoudType.Methadone,
            MOUD_JAIL_WAIT_TIME:parameters.params[JAIL_MOUD_WAIT_TIME_DAYS],
            MOUD_JAIL_ACCEPT_RATE:parameters.params[JAIL_MOUD_ACCEPTANCE_RATE],
            MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE:parameters.params[MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE_METHADONE],
            MOUD_TIME_ON_TREATMENT:time_treat_dict[MoudType.Methadone],
            MOUD_OD_RISK:parameters.params[MOUD_OD_RISK],
            MOUD_REARREST_RISK:parameters.params[MOUD_REARREST_RISK]},
            
            {MOUD_TYPE:MoudType.Buprenorphine_Sublingual,
            MOUD_JAIL_WAIT_TIME:parameters.params[JAIL_MOUD_WAIT_TIME_DAYS],
            MOUD_JAIL_ACCEPT_RATE:parameters.params[JAIL_MOUD_ACCEPTANCE_RATE],
            MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE:parameters.params[MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE_SLBUP],
            MOUD_TIME_ON_TREATMENT:time_treat_dict[MoudType.Buprenorphine_Sublingual],
            MOUD_OD_RISK:parameters.params[MOUD_OD_RISK],
            MOUD_REARREST_RISK:parameters.params[MOUD_REARREST_RISK]},
            
            {MOUD_TYPE:MoudType.Buprenorphine_XR,
            MOUD_JAIL_WAIT_TIME:parameters.params[JAIL_MOUD_WAIT_TIME_DAYS],
            MOUD_JAIL_ACCEPT_RATE:parameters.params[JAIL_MOUD_ACCEPTANCE_RATE],
            MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE:parameters.params[MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE_XRBUP],
            MOUD_TIME_ON_TREATMENT:time_treat_dict[MoudType.Buprenorphine_XR],
            MOUD_OD_RISK:parameters.params[MOUD_OD_RISK],
            MOUD_REARREST_RISK:parameters.params[MOUD_REARREST_RISK]},
            
            {MOUD_TYPE:MoudType.Naltrexone_XR,
            MOUD_JAIL_WAIT_TIME:parameters.params[JAIL_MOUD_WAIT_TIME_DAYS],
            MOUD_JAIL_ACCEPT_RATE:parameters.params[JAIL_MOUD_ACCEPTANCE_RATE],
            MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE:parameters.params[MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE_XRNTX],
            MOUD_TIME_ON_TREATMENT:time_treat_dict[MoudType.Naltrexone_XR],
            MOUD_OD_RISK:parameters.params[MOUD_OD_RISK],
            MOUD_REARREST_RISK:parameters.params[MOUD_REARREST_RISK]}
        ]

        self.moud_dict = {data[MOUD_TYPE]:MOUD(data) for data in moud_data_list}

    def get_MOUD(self, moud_type:MoudType) -> MOUD:
        return self.moud_dict[moud_type]

def load_moud_time_treatment(file_name) -> dict:
    """ Create a dict of MOUD name to dict of days on treatment and fraction on treatment
    """

    time_treat_data = pd.read_csv(file_name)

    time_treat_dict = {}
    for moud in MoudType:
        # Filter DF by MOUD name
        moud_df = time_treat_data[time_treat_data[MOUD_TIME_NAME] == moud.value]

        # Create a dict for each moud with the time on treatment days and probs
        moud_dict = {MOUD_TIME_DAYS:moud_df[MOUD_TIME_DAYS].tolist(), MOUD_TIME_FRACTION:moud_df[MOUD_TIME_FRACTION].tolist()}

        time_treat_dict[moud] = moud_dict

    return time_treat_dict