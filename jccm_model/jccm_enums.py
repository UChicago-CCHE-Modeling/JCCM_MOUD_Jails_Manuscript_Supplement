# This file is part of the Justice Community Circulation Model
#
# JCCM Enum classes
# 
# Uses the aenum 'advanced enumerations' library to define multi value
#  tuples for each, to support compact logging.
#

from enum import Enum

class StateType(Enum):
    Non_OUD   = "Non_OUD"
    NIHU = "NIHU"
    PWID  = "PWID"
    Death   = "Death"
    Overdose = "Overdose"

class Gender(Enum):    
    Male   = "Male"
    Female = "Female"
    Transgender  = "Transgender"

class Race(Enum):
    NHWhite  = "NHWhite"
    Black    = "Black"
    Hispanic = "Hispanic"
    Other    = "Other"

class Age(Enum):   
    Age_18_24 = "18-24"
    Age_25_34 = "25-34"
    Age_35_44 = "35-44"
    Age_45_plus = "45+"

class Employment(Enum):
    Full = "Full"
    Part = "Part"
    Un = "Un"

class Housing(Enum):
    Homeless = "Homeless"
    Housed = "Housed"

class Jail_Release(Enum):
    Week_0_2 = "Week_0_2"
    Week_3_4 = "Week_3_4"
    Week_5 = "Week_5"
    NA = "NA"

class Intervention(Enum):
    Naloxone = "Naloxone"
    Naloxone_Jail = "Naloxone_Jail"
    Naloxone_Jail_Network = "Naloxone_Jail_Network"

class MoudType(Enum):
    Methadone = "Methadone"
    Buprenorphine_Sublingual = "Buprenorphine_Sublingual"
    Buprenorphine_XR = "Buprenorphine_XR"
    Naltrexone_XR = "Naltrexone_XR"
    NONE = "None"

class JailState(Enum):
    NONE = "none"
    WAIT_FOR_OUD_SCREEN = "wait_for_oud_screen"
    NON_OUD = "non_oud"
    WAIT_FOR_MOUD = "wait_for_moud"
    OUD_NO_MOUD = "oud_no_moud"
    OUD_MOUD = "oud_moud"