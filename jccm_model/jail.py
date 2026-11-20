# This file is part of the Justice Community Circulation Model
#
# Jail class which defines all jail-related attributes and behaviors.
# 
# 

from .model_statistics import Statistics, LogType
from .person import Person
from .jccm_enums import *
from .jccm_utils import fast_choice_uniform, fast_choice, printf
from .moud import *
from .constants import *
import functools
from repast4py import schedule, random, parameters

import numpy as np

class Jail:
    """ Jail class

    Attributes
    ----------
    TODO

    """

    def __init__(self, cji_persons:list, interventions:list = []):
        
        self.initial_size = parameters.params[CJI_JAIL_INITIAL_SIZE]
        self.default_daily_intake = parameters.params[CJI_JAIL_DAILY_INTAKE]
        self.overdose_tolerance_days = parameters.params[CJI_OVERDOSE_TOLERANCE_DAYS]

        self.interventions = interventions
        self.incarcerated_population = []
        
        # initial_jail_pop = random.sample(cji_persons,jail_size)
        initial_jail_pop = random.default_rng.choice(cji_persons, size=self.initial_size, replace=False)

        # Check for duplicates in random sample
        # u,c = np.unique(initial_jail_pop, return_counts=True)
        # dup = u[c > 1]
        # print(f'Jail init: {dup}')
       
        self.intake_persons(initial_jail_pop, 0)

        self.moud_type = MoudType.NONE   # The type of MOUD offered

        self.initialize_moud_programs()

    def initialize_moud_programs(self):
        # TODO offer additional MOUD or multiple simultaneous

        self.moud_type = MoudType(parameters.params[JAIL_MOUD_TYPE])

        printf(f'Jail MOUD type: {self.moud_type.value}')

    def intake_persons(self, person_list, tick):
        for p in person_list:
            self.intake_person(p, tick)

    def generate_new_daily_intake(self, arrest_candidates, tick):
        """ Determine how many new persons to intake at the current
            tick to keep the jail population size constant.
        """

        new_intake_num = 0
        if self.default_daily_intake > 0:
            new_intake_num = self.default_daily_intake
        else:
            new_intake_num = self.initial_size - len(self.incarcerated_population)

        count = 0
        persons_to_intake = []
        if new_intake_num > 0:
            arrest_sample_size = 500
            if tick == 0:
                arrest_sample_size = 2 * self.initial_size

            idxs = random.default_rng.choice(range(len(arrest_candidates)), arrest_sample_size, replace=False)
            sample = [arrest_candidates[i] for i in idxs]

            # TODO nummpy choice is slow with large arrays!
            # sample = random.default_rng.choice(cji_persons, arrest_sample_size, replace=False)

            # Check for duplicates in random sample
            # u,c = np.unique(sample, return_counts=True)
            # dup = u[c > 1]
            # print(f'Jail t = {tick}: {dup}')

            # Check each candidate person and add to list to intake
            for person in sample:
                # If the person is on MOUD, adjust their rearrest risk
                # This approach assumes that MOUD *reduces* rearrest probability
                # relative to the non-MOUD group
                # if person.current_moud != MoudType.NONE:
                if person.moud_adherent is True:
                    moud:MOUD = MOUD_Library.getInstance().get_MOUD(person.current_moud)

                    if random.default_rng.random() < moud.rearrest_risk:
                        persons_to_intake.append(person)
                        count += 1

                # Non-MOUD persons 100% chance of rearrest if randomly selected
                else:
                    persons_to_intake.append(person)
                    count += 1

                # Found enough new person to intake then stop
                if count >= new_intake_num:
                    break

        self.intake_persons(persons_to_intake, tick)

    def intake_person(self, person:Person, tick):
        Statistics.getInstance().log_status(tick, LogType.JAIL_INTAKE, person, '')

        self.incarcerated_population.append(person)

        # Determine the length of incarceration and schedule the release date.

        lengh_incarc_type_fraction = parameters.params['jail.loi.fractions']
        
        length_of_incarceration_days = get_length_of_incarceration(lengh_incarc_type_fraction)

        # Person has reduced overdose tolerance if incarcerated over a threshold 
        # number of days
        person.reduced_tolerance = False
        if length_of_incarceration_days > self.overdose_tolerance_days:
            person.reduced_tolerance = True

        # Release from jail day.  NOTE event occurs with last priority, e.g. end of day
        release_day = tick + length_of_incarceration_days
        person.jail_release_day = release_day
        callable =  functools.partial(self.release_person, person, release_day)
        schedule.runner().schedule_event(release_day, callable, schedule.PriorityType.LAST)

        # TODO set person jail attributes
        person.currently_incarcerated = True
        person.days_since_incarceration_release = -1
       
        # Take away naloxone if sent to jail 
        person.naloxone = False

        if person.moud_adherent is True:
        # if person.current_moud != MoudType.NONE:
            person.cancel_stop_moud_treatment()     # Person continues MOUD in jail automatically
            person.jail_state = JailState.OUD_MOUD 

        else:  # Schedule OUD screening event.
            # NOTE screening event only occurs if the release day is <= then the screening day
            
            # Draw wait time for OUD screening
            
            # TODO MOUD do we want the wait time to be random between runs, but the same for
            #      everyone, or really random for each person
            wait_time = parameters.params[JAIL_OUD_SCREEN_WAIT_TIME_DAYS]
            # wait_time = random.default_rng.integers(0,max_wait_time,1)[0]
            
            # TODO MOUD just keep the wait time constant for everyone
            oud_screen_day = tick + wait_time

            person.jail_state = JailState.WAIT_FOR_OUD_SCREEN

            if oud_screen_day <= release_day:
                callable =  functools.partial(self.screen_for_oud, person, oud_screen_day)
                schedule.runner().schedule_event(oud_screen_day, callable)

    def screen_for_oud(self,person:Person,tick):
        """Screen person for Opioid Use Disorder (OUD)

        Parameters
        ----------
        person : Person
            the person to screen.
        tick : float
            the current model tick
        """

        # TODO
        # If the person is currently on MOUD treatment, screening probabiltity is 100%
        # if person.current_moud != MoudType.NONE:
        #     pass

        # Probability of detecting OUD in persons with OUD
        oud_detect_probability = parameters.params[JAIL_OUD_SCREEN_PROBABILITY]

        # NOTE assumes zero chance of false positive OUD diagnosis
        is_oud = False  # Test result if the person is detected to be OUD
        
        if person.state == StateType.Non_OUD:
            is_oud = False
        else:
            if random.default_rng.random() < oud_detect_probability:
                is_oud = True
            else:
                is_oud = False      # This result is a simulated false negative

        Statistics.getInstance().log_status(tick, LogType.JAIL_OUD_SCREEN, person, is_oud)

        # TODO More advanced Rules for initiating MOUD
        #   XR - if last injection less than n days ago, then...
        
        # If the person is identified as OUD
        if is_oud:
            # If MOUD is available, then wait to to start MOUD
            if self.moud_type != MoudType.NONE:
                person.jail_state = JailState.WAIT_FOR_MOUD
        
                # NOTE screening event only occurs if the release day is <= then the screening day
                # Draw wait time for OUD screening
                # TODO MOUD do we want the wait time to be random between runs, but the same for
                #      everyone, or really random for each person

                # Look up the wait time for a specific MOUD type from the MOUD data dict
                moud:MOUD = MOUD_Library.getInstance().get_MOUD(self.moud_type)
                moud_wait_time = moud.jail_wait_time

                # TODO MOUD just keep the wait time constant for everyone
                moud_start_day = tick + moud_wait_time

                if moud_start_day <= person.jail_release_day:
                    callable =  functools.partial(self.start_moud, person, self.moud_type, moud_start_day)
                    schedule.runner().schedule_event(moud_start_day, callable)
            
            # If MOUD is not available, then simply note we have an OUD person with no jail-based treatment options
            else:
                person.jail_state = JailState.OUD_NO_MOUD

        # Person is non OUD and therefore no jail-based treatment needed.
        else:
            person.jail_state = JailState.NON_OUD


    def start_moud(self, person:Person, moud_type:MoudType, tick):

        moud:MOUD = MOUD_Library.getInstance().get_MOUD(moud_type)

        # If the person accepts to start MOUD in jail
        if random.default_rng.random() <= moud.jail_accept_rate:
            person.start_moud_treatment(moud_type)

            person.jail_state = JailState.OUD_MOUD
            Statistics.getInstance().log_status(tick, LogType.JAIL_START_MOUD, person, moud.name)

        # The person DOES NOT accept to start MOUD in jail
        else:
            # person.current_moud = MoudType.NONE
            person.moud_adherent = False
            person.jail_state = JailState.OUD_NO_MOUD
            Statistics.getInstance().log_status(tick, LogType.JAIL_NO_START_MOUD, person, moud.name)

        # TODO start tracking time on MOUD for tolerance loss ?


    def release_person(self, person:Person, tick):
        """ Person leaves jail

        Parameters
        ----------
        person : Person
            the person leaving jail
        tick : float
            the current model tick

        """
        self.incarcerated_population.remove(person)
        Statistics.getInstance().log_status(tick, LogType.JAIL_RELEASE, person, person.jail_state)

        person.currently_incarcerated = False
        person.jail_release_day = -1
        person.days_since_incarceration_release = 0
        person.jail_release = Jail_Release.Week_0_2
        person.previously_incarcerated = True
        person.jail_state = JailState.NONE

        # TODO MOUD Linkage to care
        
        # Determine the time on treatment
        # if person.current_moud != MoudType.NONE:
        if person.moud_adherent is True:
            moud:MOUD = MOUD_Library.getInstance().get_MOUD(person.current_moud)

            # Determine the time on treatment (days) based on the input historgram data
            days_on_treatment = fast_choice_uniform(moud.time_on_treatment[MOUD_TIME_DAYS],
                                            moud.time_on_treatment[MOUD_TIME_FRACTION])
            
            # Linkage to care effect can extend the days on treament
            linkage_to_care_multiplier = parameters.params[MOUD_LINKAGE_TO_CARE_MULTIPLIER]

            # Days on treatment can be increased or decreased based on the multiplier value,
            #  and we'd like to use a min of 1 day to account for receiving treatment at release.
            days_on_treatment *= linkage_to_care_multiplier
            days_on_treatment = max(days_on_treatment, 1)

            # Log the random sample value, which can be different from the actual time if the event is canceled later.
            Statistics.getInstance().log_status(tick, LogType.MOUD_DURATION_DRAW, person, f'{days_on_treatment}')

            # Need to interrupt this if later re-arrested or linkage adjust this
            moud_stop_day = tick + days_on_treatment
            callable =  functools.partial(person.stop_moud_treatment)

            person.stop_moud_treatment_event = schedule.runner().schedule_event(moud_stop_day, callable)

        # Try to provide the person an interventions (probability based
        # Not all people leaving jail will be eligible or want the intervention
        # The success of receving or starting the intervention is dependent on
        # each intervention type and person parameters.
        # TODO define separate intake and release interventions, e.g. MOUD in jail?
        for intervention in self.interventions:
            intervention.try_provide_jail(person, tick)

        
def get_length_of_incarceration(lengh_incarc_type_fraction):
    """
    
    """
    # determine the person lengh of incarceration
    # 25% spend 1-2 days incarcerated
    # 25% spend 3-12 days incarcerated
    # 50% spend 13-365 days incarcerated

    # TODO optionally determine based on person demographics

    # TODO person OUD multiplier on length
    # TODO minimum stay ajustment

    
    MEDIAN_LENGTH_DAYS = 12  # From Cook Co. Jail survey (Olson 2012)

    length_of_incarceration_days = 0

    incarceration_time = ['short', 'med', 'long']
    #lengh_incarc_type_fraction = [0.25, 0.25, 0.5]
            
    incarceration_length = random.default_rng.choice(incarceration_time, size=1, p=lengh_incarc_type_fraction)

    if incarceration_length == 'short':
        length_of_incarceration_days = random.default_rng.integers(1,3,1)[0]

    elif incarceration_length == 'med':
        length_of_incarceration_days = random.default_rng.integers(3,(MEDIAN_LENGTH_DAYS-1),1)[0]

    # Use a weibull (0 to ~8) to draw from days 13-365
    else:
        length_of_incarceration_days = int((MEDIAN_LENGTH_DAYS-1)+(365)*(random.default_rng.weibull(1, 1))/4.0)

    return length_of_incarceration_days

