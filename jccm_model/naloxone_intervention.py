# This file is part of the Justice Community Circulation Model
#
# Attributes and behaviors related to a naloxone intervention.
# 
# 


from repast4py import parameters, random
from .jccm_enums import *
from .constants import *

# TODO implement an abstract intervention class?

class NalxoneIntervention():
    
    """ Naloxone intervention...

        TODO...

        TODO not sure if we need to separate out the distribution intervention
             from the administer naloxone code?
    """

    def __init__(self):
        """Constructor
        
        Parameters
        ----------
        

            TODO...
        
        """

        # TODO these intervention related props could be dependent on demographics
        #      and be different for each person
        self.probability_naloxone_reversal = parameters.params[PROBABILITY_NALOXONE_REVERSAL]

        self.naloxone_level_jail = parameters.params[NALOXONE_LEVEL_JAIL]
        self.naloxone_level_community = parameters.params[NALOXONE_LEVEL_COMMUNITY]
        self.naloxone_level_jail_network = parameters.params[NALOXONE_LEVEL_JAIL_NETWORK]

        self.refill_after_use = parameters.params[NALOXONE_REFILL]  # Refill after using

    # TODO community level naloxone is used in the apply method when determining if a bystander
    #      has naloxone
    
    # def enroll_community(self, person, tick):
    #     """ Enroll the community individual in this intervention so that it is 
    #         directly available to them, and can be applied later.
    #     """

    #     # Non OUD persons are not provided with naloxone
    #     if person.state == StateType.Non_OUD: 
    #         return

    #     # Provide naloxone directly to the released individual if selected
    #     if random.random() < self.naloxone_level_community:
    #         person.receive_naloxone(tick)

    def try_provide_jail(self, person, tick):
        """ Try to provide the intervention to the person leaving jail.
        """

        # Non OUD persons are not provided with naloxone
        if person.state == StateType.Non_OUD: 
            return

        # Provide naloxone directly to the released individual if selected
        if random.default_rng.random() < self.naloxone_level_jail:
            person.receive_naloxone(tick, Intervention.Naloxone_Jail)

        # Provide nalaxone to the released individual's social network.  This is independent
        # of the person receiving naloxone directly
        if random.default_rng.random() < self.naloxone_level_jail_network:
            person.distribute_naloxone_to_newtork(tick)
