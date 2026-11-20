# This file is part of the Justice Community Circulation Model
#
# Person agent class which defines all individuals in the JCCM.
# 
# 

from repast4py import core, schedule
from .model_statistics import Statistics, LogType
from .jccm_enums import *
from .jccm_utils import printf
from .constants import *
from .moud import *
import functools

PERSON_AGE = 'Age'
PERSON_GENDER = 'Gender'
PERSON_RACE = 'Race'
PERSON_ID = 'ID'
PERSON_CJI = 'CJI'
PERSON_OUD_STATE = 'OUD State'

class Person(core.Agent):

    """Person class is the main model agent with all person behaviors.
    
    Attributes
    ----------
    gender : enum
        the person's gender define in the Gener enum
    race : enum
        the person's race defined in the Race enum
    age : enum
        the peron's age group defined in the Age enum
    id : int        
        unique identifier of the person
    state : enum
        the person's current State type 

    cji : boolean
        if the person is criminal justice involved

    TODO add in new...    
    """
    
    # NOTE that the ID attribute is not the same as the ID attribute in person data!
    ID = 0  # repast4Py agent class ID for Person

    def __init__(self, person_data, rank):
        """Constructor
        
        Parameters
        ----------
        person_data : dict
            dictionary of data for initializing person attributes
        rank : int
            rank on which this person is created
        """
        
        self.gender = Gender(person_data[PERSON_GENDER])
        self.race = Race(person_data[PERSON_RACE])
        self.age = Age(person_data[PERSON_AGE])
        id = int(person_data[PERSON_ID])
        
        self.initial_state = StateType[person_data[PERSON_OUD_STATE]]
        self.cji = person_data[PERSON_CJI] 
        
        self.initialize_vars()

        super().__init__(id, Person.ID, rank)
       
        # TODO log person created

    def initialize_vars(self):
        self.state = self.initial_state
        self.alive = True

        self.jail_release = Jail_Release.NA
        self.jail_release_day = -1
        self.currently_incarcerated = False
        self.previously_incarcerated = False
        self.days_since_incarceration_release = -1
        self.prior_state = None
        self.jail_state = JailState.NONE
        self.current_moud:MoudType = MoudType.NONE  # The current or most previously used MOUD
        self.moud_adherent = False          # If the person is adherent to medication
        self.moud_is_therapeutic = False    # If the person has a therapeutic does of MOUD

        self.naloxone = False               # No access unless provided later
        self.reduced_tolerance = False      # Reduced tolerance to overdose
        
        # TODO need to replace with real network and check if neigbors have naloxone
        self.network_naloxone = False # Somone in social network has naloxone

        self.moud_start_day = -1
        self.stop_moud_treatment_event = None       # A repast ScheduledEvent
        self.end_moud_therapeutic_event = None      # A repast ScheduledEvent
    

    def to_str(self) -> str: 
        p_string = str(self.id) + "," + str(self.gender.value) + "," + \
            str(self.race.value) + "," + str(self.age.value) + "," + \
                str(self.state.value) + "," + str(self.cji) + "\n"

        return p_string

    def to_index(self) -> str: 
        p_string = (
            f'{self.id}, {self.gender.index},'
            f'{self.race.index}, {self.age.index},'
            f'{self.state.index}, {int(self.cji)}\n'
        )
        return p_string

    def distribute_naloxone_to_newtork(self, tick):
        """ Distribute naloxone to this person's social network.
            The current implementation assumes that one THN kit is provided
            to a single close person in this person's social network.

            TODO implement real network and set neighbor attributes
        """
        self.network_naloxone = True
        Statistics.getInstance().log_status(tick, LogType.ENROLL_TREATMENT, self, Intervention.Naloxone_Jail_Network.value)

    def receive_naloxone(self, tick:float, intervention_type:Intervention):
        """ Person receives a naloxone kit.
        """
        self.naloxone = True
        Statistics.getInstance().log_status(tick, LogType.ENROLL_TREATMENT, self, intervention_type.value)

    def administer_naloxone(self, tick):
        """ Person administers naloxone to self
        """
        self.naloxone = False  # Naloxone is consumed (can be refilled later)
        Statistics.getInstance().log_status(tick, LogType.ADMINISTER_TREATMENT, self, Intervention.Naloxone.value)

    def start_moud_treatment(self, moud:MoudType):
        self.current_moud:MoudType = moud
        self.moud_adherent = True
        
        # Assume that MOUD achieves therapeutic dosage immediately
        # TODO could include delays for e.g. methadone
        self.moud_is_therapeutic = True

        self.moud_start_day = schedule.runner().tick()

        # If there is a scheduled end of therapeutic dose because the person stopped taking medication,
        #   cancel the end of therapeutic dose event since the person is restarting before that would
        #   occur.
        if self.end_moud_therapeutic_event != None:
            self.end_moud_therapeutic_event.void()
            self.end_moud_therapeutic_event = None

    def stop_moud_treatment(self):
        """ The person stops MOUD treatment (scheduled at initiation based on treatment adherence distribution)
        """
        tick = schedule.runner().tick()

        # Determine the day on which the MOUD plasma concentration drops below the therapeutic
        #  threshold wrt to overdose risk.  Input data for end day are based on literature values
        #  for each medicatio.
        # 
        
        moud:MOUD = MOUD_Library.getInstance().get_MOUD(self.current_moud)
        therapeutic_end_day = tick + moud.therapeutic_days_after_last_dose

        # TODO make a list of treatment-based callables that we can clear on interruption events.
        # Need to interrupt this if later re-arrested or linkage adjust this
        callable =  functools.partial(self.end_moud_therapeutic_plasma_concentration)
        self.end_moud_therapeutic_event = schedule.runner().schedule_event(therapeutic_end_day, callable)

        # self.current_moud = MoudType.NONE
        self.moud_adherent = False
        moud_days_on_treatment = tick - self.moud_start_day
        Statistics.getInstance().log_status(tick, LogType.STOP_MOUD, self, f'{moud_days_on_treatment}')

        self.moud_start_day = -1

    def end_moud_therapeutic_plasma_concentration(self):
        """ Sets the MOUD therapeutic plasma concentration to false, meaning that the MOUD
            has washed out of the person's plasma and is below therapeutic threshold.
        """
        self.moud_is_therapeutic = False

        tick = schedule.runner().tick()
        Statistics.getInstance().log_status(tick, LogType.MOUD_END_THERAPEUTIC_DOSE, self)


    def cancel_stop_moud_treatment(self):
        ''' Cancel the stop moud treatment event, in case of some interventing event like re-arrest
        '''
        tick = schedule.runner().tick()

        Statistics.getInstance().log_status(tick, LogType.JAIL_CONTINUE_MOUD, self)

        self.stop_moud_treatment_event.void()
        self.stop_moud_treatment_event = None


    def step(self, tick):
        """Step behavior for Person
        
        Parameters
        ----------
        tick : float
            the current model tick
        """

        # self.age += 1.0 / 365.0   # TODO model time step 
        
        # TODO schedule the change in days since incarceration release

        if self.days_since_incarceration_release >= 0:
            self.days_since_incarceration_release += 1

            if self.days_since_incarceration_release <= 14:
                self.jail_release = Jail_Release.Week_0_2
            elif 14 < self.days_since_incarceration_release <= 28:
                self.jail_release = Jail_Release.Week_3_4
            else:
                self.jail_release = Jail_Release.Week_5

        # TODO step data props, etc
        #step_data = 1
        
        #self.state.step(tick, self, step_data)
        
    def deactivate(self, tick):
        """Deactivation (death) behavior for Person
        
        Parameters
        ----------
        tick : float
            the current model tick
        """
        
        self.alive = False

        if self.end_moud_therapeutic_event != None:
            self.end_moud_therapeutic_event.void()
            self.end_moud_therapeutic_event = None

        if self.stop_moud_treatment_event != None:
            self.stop_moud_treatment_event.void()
            self.stop_moud_treatment_event = None
    
        
    def reactivate(self):
        self.initialize_vars()

    def __lt__(self, other):
        return self.id < other.id
