"""Script containing the StateCreator class"""

from .constants import *
from .states import *
from .jccm_enums import *
from .jccm_utils import printf
import pandas as pd
import os
import warnings
from repast4py import parameters
        
TRANSITION_PROP_PREFIX = "transition_"

def create_states(data_dir):
    """Create each state instance and return a list.

    Parameters
    ----------
    data_dir : str
        The model input data folder
    

    Returns 
    -------
    states
        a list of State instances
    """
    states = {}

    state_transition_data_file = parameters.params[STATE_TRANSITION_DATA_FILENAME]
    state_transition_effects_filename = os.path.join(data_dir,state_transition_data_file)

    transition_data = pd.read_csv(state_transition_effects_filename)
    transition_data_dict = create_transition_data(transition_data)

    update_transition_data_dict(transition_data_dict)
    
    # TODO this could be made more generic via a single state constructor 
    state_data = transition_data_dict[StateType.NIHU.value]
    states[StateType.NIHU] = NIHUState(state_data)
    
    state_data = transition_data_dict[StateType.Non_OUD.value]
    states[StateType.Non_OUD] = NonOUDState(state_data)
    
    state_data = transition_data_dict[StateType.PWID.value]
    states[StateType.PWID] = PWIDState(state_data)
    
    state_data = transition_data_dict[StateType.Overdose.value]
    states[StateType.Overdose] = OverdoseState(state_data)
    
    state_data = {}  # Death is a terminal state
    states[StateType.Death] = DeathState(state_data)

    return states

def update_transition_data_dict(transition_data_dict):
    """Update the state transition probabilities data from values defined in
    the props data.  Any property that starts with the reserved TRANSITION_PROP_PREFIX
    will be treated as a transition rate and will be assigned to the appropriate 
    "from" -> "to" state mapping in the transition data.

    Props should be in the format:

        transition_NIHU*Overdose*Gender.Female = 1

    Parameters
    ----------
    transition_data_dict
        a dict of transition data betwee "from" and "to" states.
    """

    for p in parameters.params:
        if p.startswith(TRANSITION_PROP_PREFIX):
            val = parameters.params[p]

            # Split the property on '*', similar to the transition rate data file comma
            # NOTE avoid using comma-delimitter since JSON splits on comma in the swift workflow.
            trans_data = p.split("*")

            from_state = trans_data[0].split(TRANSITION_PROP_PREFIX)[1]     # FROM state
            to_state = trans_data[1]                                        # TO state
            attr_str = trans_data[2]                                        # Attribute

            attr = attr_str

            # Convert attribute strings into Enums when applicable.  Attributes can be
            #  tokenized on '.' and should be in the format Enum.enum
            parts = attr_str.split('.')
            if len(parts) == 2:
                enum_class = globals()[parts[0]]      # Enum class
                attr = enum_class(parts[1])           # Enum value
                
            printf(f'Updating transiton probability: {from_state} -> {to_state} {attr} = {val}')

            # TODO needs key/value validation
            # TODO maybe it's just better if we crash ?

            # if from_state not in transition_data_dict:
            #     warnings.warn(f'From state {from_state} not found in transition data.')
            #     continue

            transition_data_dict[from_state][StateType(to_state)][attr] = float(val)
            

def create_transition_data(transition_data):
    """Creates a dict of transition data for the given state and data. 
    
    Parameters
    ----------
    transition_data : pandas.DataFrame
        The data for all state transitions.

    Returns 
    -------
    transition_data_dict
        a dict of transition data betwee "from" and "to" states.  The first level key is
        the "from" state and values are a dict of transitionss whos keys will be all states "to"
        which the "from" state may transition.  Values will be a dict of attribute/value
        pairs that are used to calculate the probability of each transition, e.g.
    
        StateType.FROM ->

        {StateType.TO_1 : {BASE_PROBABILITY:0.1, Gender.Male:2.0, Gender.Female:1.0}, 
            StateType.TO_2 : {BASE_PROBABILITY:0.01, Gender.Male:1.0, Gender.Female:1.0}}

        Attributes that correspond to enums must be tokenized on '.' and should be in the 
            format Enum.enum
    """
    # printf('Generating States Data')

    transition_data_dict = {} # Transition data dict using str keys

    # Unique list of "from" state values in the data
    from_states_list = pd.unique(transition_data[FROM_STATE])

    for from_state in from_states_list:    
        # printf(f'From State: {from_state}')

        # Dict of "to" state transition probabilities for the current "from" state
        from_trans_data_dict = {}

        # Transition data for the 'from' state
        state_trans_data = transition_data[transition_data[FROM_STATE] == from_state]

        # Unique list of "to" states corresponding to the current "from" state
        to_states_list = pd.unique(state_trans_data[TO_STATE])  # all unique 'to' states

        for ts_str in to_states_list:
            # printf(f'\tTo State: {ts_str}')

            ts_data = state_trans_data[state_trans_data[TO_STATE] == ts_str]

            # Get a dict of the 'to' state attribute/value column rows
            ts_string_dict = ts_data.set_index(ATTRIBUTE)[VALUE].to_dict()

            ts_data_dict = {}  # Transition data dict using Enum keys

            # Convert attribute strings into Enums when applicable.  Attributes can be
            #  tokenized on '.' and should be in the format Enum.enum
            for key in ts_string_dict:
                parts = key.split('.')
                
                val = ts_string_dict[key]
                # print(str(key) + ":" + str(val) )

                # printf(f'\t\t: {key} : {val}')

                if len(parts) == 2:
                    enum_class = globals()[parts[0]]      # Enum class
                    new_key_val = enum_class(parts[1])    # Enum value
                    ts_data_dict[new_key_val] = val
                else:
                    ts_data_dict[key] = val  

            # store the transition data for each "to" state
            from_trans_data_dict[StateType(ts_str)] = ts_data_dict

        transition_data_dict[from_state] = from_trans_data_dict
        

    return transition_data_dict

