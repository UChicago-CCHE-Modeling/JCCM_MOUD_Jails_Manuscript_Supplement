# This file is part of the Justice Community Circulation Model
#
# Attributes and behaviors related to bystander logic
# 
# 

from repast4py import parameters, random
from .model_statistics import Statistics, LogType
from .jccm_enums import *
from .constants import *

# TODO implement an abstract intervention class?

class Bystander():
    
    """ Bystander Logic...

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
        self.probability_bystander = parameters.params[PROBABILITY_BYSTANDER]
        self.probability_naloxone_administer = parameters.params[PROBABILITY_NALOXONE_ADMINISTRATION]
        self.probability_ems = parameters.params[PROBABILITY_EMS]
        
        self.naloxone_level_community = parameters.params[NALOXONE_LEVEL_COMMUNITY]

        self.refill_after_use =  parameters.params[NALOXONE_REFILL]  # Refill after using

    def apply(self, person, tick) -> tuple:
        """ Perform bystander logic when a bystander is present.  This step assumes
            that an active bystander has witnessed an overdose event.

            The person argument is the person experiencing the overdose.  Bystander agents
            are not explicitely modelled.

            Returns a tuple of bool conditions (naloxone_administered, ems_called)
        """

        # The default conditions are that:
        #   1. naloxone is not administered
        #   2. EMS is not called
        naloxone_administered = False
        ems_called = False

        # Next check if naloxone is available
        #  - Does this person posses naloxne?
        #  - Does the bystander posses naloxone?
        #     - Community level
        #     - Local network of person (probability)
        #  - If naloxone is available, does the bystander administer it?
        
        #  - TODO EMS 

        # Naloxone can be individually tracked for the person experiencing the OD
        #  and from the person's network.
        # Community level naloxone can onlt be tracked statistically, and we assume
        # that the dose use by the individual will be refilled

        # Bystander has naloxone either from community level distribution or
        #   from distribution to individuals with network distribution.
        community_naloxone = (random.default_rng.random() < self.naloxone_level_community)
        naloxone = person.naloxone or community_naloxone or person.network_naloxone 

        # TODO we could log which naloxone was used but this would overcomplicate logging

        # Probability that available naloxone is actually administered
        if (naloxone and random.default_rng.random() < self.probability_naloxone_administer):
            
            # NOTE person logs administration of naloxone
            person.administer_naloxone(tick)
            
            naloxone_administered = True
            
            # Assume that EMS is always called when naloxone is used
            # TODO This could be parameterized as well, but per Coffin 2013, the probability was 1.0
            # ems_called = True

        # Probability that EMS is called
        if (random.default_rng.random() < self.probability_ems):
            ems_called = True

        if (ems_called):
            Statistics.getInstance().log_status(tick, LogType.EMS_CALLED, person, "")
        
        return naloxone_administered, ems_called;