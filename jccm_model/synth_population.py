import os
import warnings
import pandas as pd

from repast4py import parameters, random

from .constants import *
from .jccm_enums import *
from .jccm_utils import printf
from .person import *

oud_column_name = "OUD State"
cji_column_name = "CJI"

def generate_snythetic_population_data(data_dir:str, cji_only:bool) -> pd.DataFrame:
    """Creates a set of person data for the synthetic population. 

    Parameters
    ----------
    data_dir : str
        the directory with the population data
    cji_only : bool
        If True, only return the CJI  persons

    Returns 
    -------
    person_data : pandas.DataFrame
        all of the person data used from which to sample new persons
    """

    cji_group_frac_file = os.path.join(data_dir,parameters.params[CJI_GROUP_FRACTIONS_FILE])
    pwid_group_frac_file = os.path.join(data_dir,parameters.params[PWID_GROUP_FRACTIONS_FILE])
    nihu_group_frac_file = os.path.join(data_dir,parameters.params[NIHU_GROUP_FRACTIONS_FILE])

    cji_size = round(parameters.params[CJI_ALL_SIZE])  # Round floats
    oud_column_name = "OUD State"
    
    cji_fractions = load_population_fractions(cji_group_frac_file)
    cji_person_data = create_persons_data_from_fractions(cji_size, cji_fractions)
    cji_person_data[oud_column_name] = StateType.Non_OUD.value
    cji_person_data[cji_column_name] = True
 
    pwid_size = round(parameters.params[PWID_POPULATION_SIZE])    # Round floats
    pwid_fractions = load_population_fractions(pwid_group_frac_file)
    pwid_person_data = create_persons_data_from_fractions(pwid_size, pwid_fractions)
    pwid_person_data[oud_column_name] = StateType.PWID.value
    pwid_person_data[cji_column_name] = False

    # printf("\nGenerating CJI PWID")
    cji_fraction_pwid = parameters.params[CJI_FRACTION_PWID]     # Round floats
    num_cji_pwid = round(cji_size * cji_fraction_pwid)

    oud_state = StateType.PWID.value
    cji_person_data = create_cji_ouds(
        cji_person_data, pwid_fractions, num_cji_pwid, oud_state)

    n = len(cji_person_data[(cji_person_data[oud_column_name] == StateType.PWID.value) ])

    # printf("Num CJI PWID input: " + str(num_cji_pwid) + ", num found: " + str(n))

    nihu_size = round(parameters.params[NIHU_POPULATION_SIZE])    # Round floats
    nihu_fractions = load_population_fractions(nihu_group_frac_file)
    nihu_person_data = create_persons_data_from_fractions(nihu_size, nihu_fractions)
    nihu_person_data[oud_column_name] = StateType.NIHU.value
    nihu_person_data[cji_column_name] = False

    # printf("\n\nGenerating CJI NIHU")
    cji_fraction_nihu = parameters.params[CJI_FRACTION_NIHU]
    num_cji_nihu = round(cji_size * cji_fraction_nihu)

    oud_state = StateType.NIHU.value
    cji_person_data = create_cji_ouds(
        cji_person_data, nihu_fractions, num_cji_nihu, oud_state)

    n = len(cji_person_data[(cji_person_data[oud_column_name] == StateType.NIHU.value) ])

    # printf("Num CJI NIHU input: " + str(num_cji_nihu) + ", num found: " + str(n))

    # Only return the CJI population
    if cji_only:
        # Only return the CJI with StateType PWID or NIHU
        # all_person_data = cji_person_data[cji_person_data[oud_column_name].isin([StateType.PWID.value,StateType.NIHU.value])].copy()
        all_person_data = cji_person_data
    else:
        # Concat all the person data dataframes
        all_person_data = pd.concat(
            [cji_person_data, pwid_person_data, nihu_person_data], ignore_index=True, sort=False)
   
    # Add an ID column from 0 to num rows
    all_person_data["ID"] = range(len(all_person_data))

    return all_person_data

def load_population_fractions(file_name):
    """Population fractions from file.  The file format is a CSV with two
        columns, "group" and "fraction".  The Group is a string encoded with
        the group demographic in the format [Gender Race AgeGroup], and the
        fraction is the 0-1 floating point value that represents the fraction
        of this group in the entire population.  The sum of the fraction column
        should be nearly 1.0 
    
    Parameters
    ----------
    file_name : str
        the file name containing the population fractions

    Returns 
    -------
    fractions_data : pandas.DataFrame
        data of demographic fractions

    """
    
    fractions_data = pd.read_csv(file_name)

    if not (0.98 <=  fractions_data.Fraction.sum() <= 1.02):
        warnings.warn(f'Population fraction is not 1.0 for {file_name}')

    return fractions_data

def create_persons_data_from_fractions(num_to_create, fractions_data) -> pd.DataFrame:
    """Creates a 
    
    Parameters
    ----------
    num_to_create : int
        the number of people to create
    fractions_data : pandas.DataFrame
        the demographic fractions data from which to generate person data
    
    Returns 
    -------
    person_data
        a data frame of persons data
    """

    df_fractions = fractions_data.copy(deep=True)

    df_fractions["Count"] = round(df_fractions["Fraction"] * num_to_create)

    person_data = pd.DataFrame()
    
    for index, row in df_fractions.iterrows():
        count = int(row["Count"])
        temp_df = pd.DataFrame(count*[row])
        person_data = pd.concat([person_data, temp_df], ignore_index=True)
    
    # person_data = person_data.reset_index()
    person_data = person_data.drop(columns=['Fraction','Count'])

    return person_data

def create_cji_ouds(
    cji_population_person_data, oud_fractions, num_persons, oud_state) -> pd.DataFrame:
    
    """Assign OUD status (eg pwid, nihu) to CJI person data based on the 
        provided CJI person data and OUD fractions data
        
    Parameters
    ----------
    cji_population_person_data : pandas.DataFrame
        CJI Persons data

    TODO

    """
    
    oud_fractions["Count"] = round(oud_fractions["Fraction"] * num_persons)

    # cji_population_person_data[oud_column_name] = False

    # For each OUD demographic subgroup, get the corresponding CJI persons data
    for index, row in oud_fractions.iterrows():
        gender = row[PERSON_GENDER]
        race = row[PERSON_RACE]
        age = row[PERSON_AGE]
        count = int(row["Count"])

        # CJI person data indices.  Get CJI Perons that match the current fraction row
        #  demographics AND who also have OUD state of NA (so we don't overwrite OUD state)
        indexes = (cji_population_person_data[PERSON_GENDER] == gender) & \
            (cji_population_person_data[PERSON_RACE] == race) & \
                (cji_population_person_data[PERSON_AGE] == age) & \
                    (cji_population_person_data[oud_column_name] == StateType.Non_OUD.value)

        subset = cji_population_person_data[indexes]

        # printf(gender + " " + race + " " + age + " " + str(count))

        if len(subset.index) <= count:
            # printf("\tOnly found " + str(len(subset.index)))
            cji_oud = subset
            cji_population_person_data.loc[cji_oud.index, oud_column_name] = oud_state

        elif len(subset.index) > 0:
            # Get a random sampling of CJI person data based on the number of
            # Set the repast default generator as the pandas sample generator
            #  CJI OUD
            cji_oud = subset.sample(n = count, random_state=random.default_rng)

            cji_population_person_data.loc[cji_oud.index, oud_column_name] = oud_state

    
    return cji_population_person_data
