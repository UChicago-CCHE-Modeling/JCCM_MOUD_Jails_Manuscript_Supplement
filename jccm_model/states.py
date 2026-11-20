"""Script containing Person states"""

from enum import Enum 
from abc import ABC, abstractmethod

from repast4py import random

from .constants import *
from .person import Person
from .moud import *
from .jccm_enums import *
from .jccm_utils import fast_choice
from .model_statistics import Statistics, LogType

# String consts for state transition data
FROM_STATE = 'FROM_STATE'
TO_STATE = 'TO_STATE'
ATTRIBUTE = 'ATTRIBUTE'
VALUE = 'VALUE'
BASE_PROBABILITY = 'Base_Probability'
RISK = 'Risk'
    
class State(ABC):
    """ State
    """
    def __init__(self, state_type):
        self.state_type = state_type


    @abstractmethod
    def step(self, tick, person, step_data):
        """ should be implemented by subclasses
        """ 
        pass
    
    @abstractmethod
    def apply(self, tick, person, apply_data):
        """ should be implemented by subclasses
        """
        pass
        
    def __repr__(self):
        """ Leverages the __str__ method to describe the State.
        """
        return self.__str__()

    def __str__(self):
        """ Returns the name of the State.
        """
        return self.__class__.__name__

    
class NonOUDState(State):
    """ State for non OUD
    """

    def __init__(self, transition_data): 
        super().__init__(StateType.Non_OUD)   
        self.transition_data = transition_data

    def step(self, tick, person, step_data):
        return StateType.Non_OUD

    def apply(self, tick, person, apply_data):
        return self
    
class NIHUState(State):
    """ State for NIHU
    """
    def __init__(self, transition_data): 
        super().__init__(StateType.NIHU)
        
        self.transition_data = transition_data
        self.next_state_probs = {}

    ''' Update the state transition probabilities by modifying the base rate with effects
        multipliers that are dependent on person's properties.
    '''
    def update_transition_probabilities(self, person:Person):
        other_states_prob = 0   # The cumulative probability of all OTHER states
        
        # Update the transition probabiliy of all OTHER states
        for next_state in self.transition_data.keys():
           
            # dict of transition probability for next state
            data = self.transition_data[next_state]  
            
            # Baseline probability of transition
            base_prob = data[BASE_PROBABILITY]

            # Additional risk multiplier - could be due to OUD type
            risk = data[RISK]

            # TODO all effects multipliers
            if person.gender in data:
                gender_effect = data[person.gender]
            else: 
                gender_effect = 1

            if person.age in data:
                age_effect = data[person.age]
            else: 
                age_effect = 1

            # Apply OD increase effect only for people with reduced tolerance
            prev_incarcerated_effect = 1
            if person.reduced_tolerance:
                prev_incarcerated_effect = data[person.jail_release]

            # If the person is currently at thereapeutic levels of MOUD
            moud_effect = 1
            if next_state == StateType.Overdose:
                if person.moud_is_therapeutic is True:
                # if person.current_moud != MoudType.NONE:
                    moud = MOUD_Library.getInstance().get_MOUD(person.current_moud)
                    moud_effect = moud.od_risk

            p = base_prob * risk * gender_effect * prev_incarcerated_effect * age_effect * moud_effect
            p = min(1,p)  # max prob = 1

            self.next_state_probs[next_state] = p

            other_states_prob += p

        # Probability of remaining in current state
        other_states_prob = min(1,other_states_prob)  # max prob = 1
        self.next_state_probs[self.state_type] =  1 - other_states_prob

    def step(self, tick, person, step_data):
       
        self.update_transition_probabilities(person)

        # Select the next state based on the state transition probability for each state
        st = list(self.next_state_probs.keys())       # list of possible states
        probs = list(self.next_state_probs.values())  # list of state probs, in same order
        
        # Select the next state according to the next state probabilities
        # The python random.choices is significantly faster than numpy for small sets
        #next_state = self.random_generator.choice(st,p=probs)

        # random.choices() returns a list, but we only need the first element [0]
        #next_state = random.choices(population=st,weights=probs,k=1)[0]

        # NOTE numpy choice is extremely slow when selecting one value
        # next_state = random.default_rng.choice(st, size=1, p=probs)[0]
        next_state = fast_choice(st,probs)

        return next_state

    def apply(self, tick, person, apply_data):
        person.prior_state = person.state
        person.state = self.state_type
        Statistics.getInstance().log_status(tick, LogType.TRANSITION, person, person.state)
    
class PWIDState(State):
    """ State for PWID
    """

    def __init__(self, transition_data):
        super().__init__(StateType.PWID) 
        self.transition_data = transition_data
        self.next_state_probs = {}

    ''' Update the state transition probabilities by modifying the base rate with effects
        multipliers that are dependent on person's properties.
    '''
    def update_transition_probabilities(self, person):
        other_states_prob = 0   # The cumulative probability of all OTHER states
        
        # Update the transition probabiliy of all OTHER states
        for next_state in self.transition_data.keys():
           
            # dict of transition probability for next state
            data = self.transition_data[next_state]  
            
            # Baseline probability of transition
            base_prob = data[BASE_PROBABILITY]

            # Additional risk multiplier - could be due to OUD type
            risk = data[RISK]

            # TODO all effects multipliers
            if person.gender in data:
                gender_effect = data[person.gender]
            else: 
                gender_effect = 1

            if person.age in data:
                age_effect = data[person.age]
            else: 
                age_effect = 1

            # Apply OD increase effect only for people with reduced tolerance
            prev_incarcerated_effect = 1
            if person.reduced_tolerance:
                prev_incarcerated_effect = data[person.jail_release]

            # If the person is currently at thereapeutic levels of MOUD
            moud_effect = 1
            if next_state == StateType.Overdose:
                if person.moud_is_therapeutic is True:
                # if person.current_moud != MoudType.NONE:
                    moud = MOUD_Library.getInstance().get_MOUD(person.current_moud)
                    moud_effect = moud.od_risk    

            # TODO multiply all effects that are added to a list so we don't need
            #      to specify each one
            p = base_prob * risk * prev_incarcerated_effect * gender_effect * age_effect * moud_effect
            p = min(1,p)  # max prob = 1

            self.next_state_probs[next_state] = p

            other_states_prob += p

        # Probability of remaining in current state
        other_states_prob = min(1,other_states_prob)  # max prob = 1
        self.next_state_probs[self.state_type] =  1 - other_states_prob

    def step(self, tick, person, step_data):

        self.update_transition_probabilities(person)

        # Select the next state based on the state transition probability for each state
        st = list(self.next_state_probs.keys())       # list of possible states
        probs = list(self.next_state_probs.values())  # list of state probs, in same order
        
        # Select the next state according to the next state probabilities
        # The python random.choices is significantly faster than numpy for small sets
        # next_state = self.random_generator.choice(st,p=probs)

        # random.choices() returns a list, but we only need the first element [0]
        #next_state = random.choices(population=st,weights=probs,k=1)[0]

        # NOTE numpy choice is extremely slow when selecting one value
        # next_state = random.default_rng.choice(st, size=1, p=probs)[0]
        next_state = fast_choice(st,probs)

        return next_state

    def apply(self, tick, person, apply_data):
        person.prior_state = person.state
        person.state = self.state_type
        Statistics.getInstance().log_status(tick, LogType.TRANSITION, person, person.state)
        

class OverdoseState(State):
    """ State for Overdose
    """

    def __init__(self, transition_data):
        super().__init__(StateType.Overdose) 
        self.transition_data = transition_data
        self.next_state_probs = {}
        
    ''' Update the state transition probabilities by modifying the base rate with effects
        multipliers that are dependent on person's properties.
    '''
    def update_transition_probabilities(self, tick, person):
        other_states_prob = 0   # The cumulative probability of all OTHER states
        
        # Update the transition probabiliy of all OTHER states
        for next_state in self.transition_data.keys():
           
            # dict of transition probability for next state
            data = self.transition_data[next_state]  
            base_prob = data[BASE_PROBABILITY]

            # TODO multiply all effects that are added to a list so we don't need
            #      to specify each one
            p = base_prob
            p = min(1,p)  # max prob = 1
            
            self.next_state_probs[next_state] = p

            other_states_prob += p

        # Probability of remaining in current state
        other_states_prob = min(1,other_states_prob)  # max prob = 1
        self.next_state_probs[self.state_type] =  1 - other_states_prob

    def step(self, tick, person, step_data):
        """ Overdose state doesn't step because it is not a persistant state.
            Instead will immediately decide on fatal vs non-fatal overdose 
            during the apply method.

        """
        pass

    def apply(self, tick, person:Person, apply_data):
        person.prior_state = person.state
        person.state = self.state_type

        # TODO Need a more extensible 'intervention' action to be applied in states?

        naloxone_intervention = apply_data[STATE_TRANSITION_DATA_NALOXONE_INTERVENTION]
        bystander = apply_data[STATE_TRANSITION_DATA_BYSTANDER]

        # The next actual state
        next_state = None

        # The next state if an intervention is applied.  Compare the intervention next state
        # to the natural next state to determine if a death is averted.
        intervention_next_state = None

        # During an overdose event, interventions can only be applied when a bystander
        # is present
        naloxone_administered = False
        ems_called = False

        if random.default_rng.random() <= bystander.probability_bystander:
            # Check if naloxone was administered or if EMS is called
            naloxone_administered, ems_called = bystander.apply(person,tick)  

        # If naloxone is administered by a lay bystander (not EMS), the 
        #   probability of survival is constant (~95%)
        if naloxone_administered:
            if random.default_rng.random() < naloxone_intervention.probability_naloxone_reversal:
                # If OD is reversed, remain in OD state until set below
                intervention_next_state = StateType.Overdose
            else:
                intervention_next_state = StateType.Death

        # Calculate the next state without an intervention, EVEN if the intervention is
        #  applied above, so that averted deaths can be recorded.
        self.update_transition_probabilities(tick, person)

        # Select the next state based on the state transition probability for each state
        st = list(self.next_state_probs.keys())       # list of possible states
        probs = list(self.next_state_probs.values())  # list of state probs, in same order
        
        # Select the next state according to the next state probabilities
        # The python random.choices is significantly faster than numpy for small sets
        # next_state = self.random_generator.choice(st,p=probs)

        # random.choices() returns a list, but we only need the first element [0]
        #next_state_without_intervention = random.choices(population=st,weights=probs,k=1)[0]

        # NOTE numpy choice is extremely slow when selecting one value
        # next_state_without_intervention = random.default_rng.choice(st, size=1, p=probs)[0]
        next_state_without_intervention = fast_choice(st,probs)

        # If EMS is called, the probability of survival is assumed to be the same as lay
        # naloxone administration (~95%)
        # Here we deteremine the next state without intervention with EMS since EMS
        # is not part of the naloxone intervention, but can affect the overdose survival
        # and will affect the attribution of deaths averted via naloxone.
        if ems_called:
            if random.default_rng.random() < naloxone_intervention.probability_naloxone_reversal:
                # If OD is reversed, remain in OD state until set below
                next_state_without_intervention = StateType.Overdose
            else:
                next_state_without_intervention = StateType.Death

        # If an intervention next state is determined...
        if intervention_next_state is not None:
            next_state = intervention_next_state
            
            # Log the sequence of events that have occured
            # An averted death is an overdose that was refersed by application of naloxone via
            # bystander, but not one that occurs when naloxone was only administered by EMS.
            if (intervention_next_state == StateType.Overdose and 
                    next_state_without_intervention == StateType.Death): 
                
                Statistics.getInstance().log_status(tick, LogType.DEATH_AVERTED, person, "")

        # Otherwise use the non-intervention next state    
        else:
            next_state = next_state_without_intervention

        # If Death occurs from overdose, set the person state to Death
        if next_state == StateType.Death:
            person.state = StateType.Death
            Statistics.getInstance().log_status(tick, LogType.OVERDOSE, person, "Fatal")
            Statistics.getInstance().log_status(tick, LogType.DEATH, person, "")

            if person.moud_start_day > 0:
                moud_days_on_treatment = tick - person.moud_start_day
                Statistics.getInstance().log_status(tick, LogType.FATAL_OVERDOSE_MOUD, person, f'{moud_days_on_treatment}')
        
        # Otherwise set the person state to the prior (pre-overdose) state
        else:
            person.state = person.prior_state
            Statistics.getInstance().log_status(tick, LogType.OVERDOSE, person, "Non-fatal")

            if person.moud_start_day > 0:
                moud_days_on_treatment = tick - person.moud_start_day
                Statistics.getInstance().log_status(tick, LogType.NONFATAL_OVERDOSE_MOUD, person, f'{moud_days_on_treatment}')

            # TODO Here we only record a generic "Naloxone" intervention which is assumed
            #      to be obtained via community-level distribution
            
            if naloxone_administered and naloxone_intervention.refill_after_use:
                person.receive_naloxone(tick, Intervention.Naloxone)  # Log that the person was resupplied after using


class DeathState(State):
    """ State for Death
    """

    def __init__(self, transition_data):
        super().__init__(StateType.Death) 
        self.transition_data = transition_data

    def step(self, tick, person, step_data):
       """ Death state cannot step further 
       """
       pass

    def apply(self, tick, person, apply_data):

        # printf(f'Apply Death {tick}  :  {person}')

        person.prior_state = person.state
        person.state = self.state_type
        # TODO log death here or in person.deactivate?  ****BUT NOT BOTH****
        # Statistics.getInstance().log_status(tick, LogType.DEATH, person, "")
        person.deactivate(tick)

