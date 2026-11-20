# This file is part of the Justice Community Circulation Model
#
# Script containing JCCM Model main loop
# 
# 

from mpi4py import MPI
import sys, os, time
import numpy as np
from pathlib import Path
import functools
from timeit import default_timer as timer
#import pandas as pd
import yaml 

from repast4py.parameters import init_params
from repast4py import schedule, context, parameters, random

from .constants import *
from .jail import Jail, get_length_of_incarceration
from .moud import *
from .person import Person
from .states import *
from .jccm_enums import *
from .state_creator import create_states
from .model_statistics import Statistics, LogType
from .jccm_utils import printf, print_run_summary
from .synth_population import generate_snythetic_population_data
from .naloxone_intervention import NalxoneIntervention
from .bystander import Bystander

model = None

def write_props(dir):
    """Save the model props to a file in the output folder

        Parameters
        ----------
        dir : str
            the model output directory
    """
    
    parameters.params

    fname = os.path.join(dir,'model_props.yaml')

    with open(fname, 'w') as f:
        yaml.dump( parameters.params, f, default_flow_style=False) 

def write_initial_population(persons_df):
    """Save the model props to a file in the output folder

        Parameters
        ----------
        persons_df: pandas.DataFrame
            data frame of initial persons data
        
    """
    output_dir = parameters.params[OUTPUT_DIRECTORY]
    initial_persons_fname = os.path.join(output_dir, parameters.params[INITIAL_PERSONS_FILENAME])
    output_file_format = parameters.params[OUTPUT_FILE_FORMAT]

    if output_file_format == OUTPUT_FILE_FORMAT_CSV:
        persons_df.to_csv(f'{initial_persons_fname}.csv', index=False)
    elif output_file_format == OUTPUT_FILE_FORMAT_PARQUET:
        persons_df.to_parquet(f'{initial_persons_fname}.parquet',compression='gzip')
    elif output_file_format == OUTPUT_FILE_FORMAT_FEATHER:
        persons_df.to_feather('initial_persons.feather')

class Model:
    """The JCCM Model class.

    """
    def __init__(self, comm: MPI.Intracomm):
        self.comm = comm
        self.context = context.SharedContext(comm)
        self.rank = self.comm.Get_rank()
        
        # TODO model out file name for non-distributed runs, eg ME runs
        self.run_number = 0
        if 'run' in parameters.params: self.run_number = parameters.params['run']

        start = timer()

        # Sample the random instance lots of times to check for proper seeding.
        random.default_rng.random(10000)
        d = random.default_rng.random(1)

        printf(f'JCCM Model Initialization... Run # {self.run_number}.  Random seed: {parameters.params[RANDOM_SEED]}, rand = {d}')

        # Schedule the model step interval and end time
        self.runner = schedule.init_schedule_runner(comm)
        self.runner.schedule_repeating_event(1, 1, self.step)
        self.runner.schedule_stop(parameters.params[STOP_AT])
        
        output_dir = parameters.params[OUTPUT_DIRECTORY]

        # Burn in is used to achive a steady-state initial condition prior
        # Currently burn in does not affect model behavior and is only used when
        # filtering basic stats out prin.  The burn-in period can also be used by
        # the R script for output analysis
        #
        # TODO make sure the burn-in in model.props is passed to the R script in emews.
        self.burnin_period_days = parameters.params[BURNIN_PERIOD_DAYS]

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        data_dir = parameters.params[DATA_DIR]

        self.states = create_states(data_dir)
  
        Statistics()
        MOUD_Library()

        #if self.rank == 0:
        #    printf('MPI ranks: ' + str(num_proc))
        #    printf(f'Seed: {seed}')
        
        # Synthetic population generator returns a data frame
        cji_only = parameters.params[CJI_ONLY]
        all_person_data = generate_snythetic_population_data(data_dir,cji_only)

        # Create the Person instances from the data
        initial_persons = []
        for index, row in  all_person_data.iterrows():
            p = Person(row, self.rank)
        
            initial_persons.append(p)
            self.context.add(p)

        # Initialize interventions
        self.interventions = []
        # TODO need a more general intervention specification, e.g. list of available
        #      interventions from data (probably not)
        self.naloxone_intervention = NalxoneIntervention()
        self.bystander = Bystander()
        self.interventions.append(self.naloxone_intervention) 
        
        # Initialize local jail population
        self.cji_persons = []
        for p in initial_persons:
            if p.cji == True:
                self.cji_persons.append(p)
        
        self.jail = Jail(self.cji_persons, self.interventions)

        # TODO model out file name includes rank for distributed runs
        # event_fname = os.path.join(output_dir, props['event.filename'] + "_" + str(self.rank) + ".csv")
        # stats_fname = os.path.join(output_dir, props['stats.filename'] + "_" + str(self.rank) + ".csv")
        
        write_initial_population(all_person_data)

        if self.rank == 0:        
            write_props(output_dir)

        callable =  functools.partial(self.at_end)
        self.runner.schedule_end_event(callable)

        d = random.default_rng.random(1)
        printf(f'JCCM Model Initialization Complete. Run # {self.run_number}.  Random seed: {parameters.params[RANDOM_SEED]}, rand = {d}')
        
        stop = timer()
        printf("Model init time: " + str(stop - start) + "s.")
        
    def step(self):
        """Main model step behavior.  This method controls the sequence of model
        behavior such as person steps.
        """
        
        tick =  self.runner.schedule.tick
    
        inactive_persons = []
        for person in self.context.agents(Person.ID):
            if person.alive:
                if not person.currently_incarcerated:
        
                    # TODO We dont step Non_OUD (CJI) for now since there is nothing
                    #      for them to do in the statechart
                    if person.state != StateType.Non_OUD:
                        state = self.states[person.state]
                        next_state = state.step(tick, person, {})

                        # If there is a state change, apply the new state
                        if person.state != next_state:
                            self.states[next_state].apply(tick,person,{
                                STATE_TRANSITION_DATA_NALOXONE_INTERVENTION:self.naloxone_intervention,
                                STATE_TRANSITION_DATA_BYSTANDER:self.bystander})
                        
                        # If the person state is Death, apply it here
                        # TODO this is because the overdose state isnt a true state
                        # but perhaps this should be changed so that either the death
                        # state or prior state is returned for non-fatal overdose.
                        if person.state == StateType.Death:
                            self.states[StateType.Death].apply(tick,person,{})


                # TODO decide if person.step should be in the state step
                person.step(tick)
                
            else:
                inactive_persons.append(person)
            
        # recycle agents upon death to maintain a constant population
        for ip in inactive_persons:
            # self.remove_agent(ip)
            ip.reactivate()

        arrest_candidates = [p for p in self.cji_persons if not p.currently_incarcerated and p.alive]

        self.jail.generate_new_daily_intake(arrest_candidates, tick)

        Statistics.getInstance().record_stats(tick, self.context.agents(Person.ID))
        
            
    def run(self):
        self.runner.execute()            
                
    def remove_agent(self, agent):
        self.context.remove(agent)

    def calc_counts(self):
        person_count = np.zeros(1, dtype='int64')
        counts = {Person.ID : 0}
        self.context.get_counts(counts)
        self.comm.Reduce(np.array([counts[Person.ID]], dtype='int64'), person_count, op=MPI.SUM, root=0)
      
        return (person_count[0])

    def at_end(self):
        """Behaviors to be executed at model end, such as clean up.
        """

        events_filename = Statistics.getInstance().event_file.name
        stats_filename = Statistics.getInstance().stats_file.name

        Statistics.getInstance().close()

        print_run_summary(stats_filename, self.burnin_period_days)

        if (self.rank == 0):
            printf("Run Ended.")

        # TODO converting the events CSV to parquet pos run is more efficient for
        #      compressing to smaller file size compared with the on-the-fly
        #      JCCM pyarrow logger.
        # NOTE CSV is written by default

        output_file_format = parameters.params[OUTPUT_FILE_FORMAT]
        if output_file_format == OUTPUT_FILE_FORMAT_PARQUET:
            # Convert the events CSV to parquet and delete the CSV
            event_df = pd.read_csv(events_filename)
            event_df.to_parquet(events_filename.replace('.csv','.parquet')) #,compression='gzip')
            os.remove(events_filename)  # delete the csv file
        elif output_file_format == OUTPUT_FILE_FORMAT_FEATHER:
            event_df.to_feather('events.feather')
            os.remove(events_filename)  # delete the csv file

def replace_input_param_names() -> None:
    """ TODO This is a temporary workaround for simplifying the input parameters that don't change
             between NIHU and PWID, but the model requires that the individual NIHU and PWID states
             have their own transition probability mulutpliers and we just want to use a single "OU"
             parameter that applies to both, since we don't have current data to support different
             values, assuming the values would be different.
    """

    NIHU_OD_BASE_PROB = 'transition_NIHU*Overdose*Base_Probability'
    NIHU_OD_GENDER = 'transition_NIHU*Overdose*Gender.Female'
    NIHU_OD_JAIL_0_2 = 'transition_NIHU*Overdose*Jail_Release.Week_0_2'
    NIHU_OD_JAIL_3_4 = 'transition_NIHU*Overdose*Jail_Release.Week_3_4'
    NIHU_OD_JAIL_5 = 'transition_NIHU*Overdose*Jail_Release.Week_5'
    NIHU_OU_OD_AGE_25_34 = 'transition_NIHU*Overdose*Age.25-34'
    NIHU_OD_AGE_35_44 = 'transition_NIHU*Overdose*Age.35-44'
    NIHU_OD_AGE_45 = 'transition_NIHU*Overdose*Age.45+'

    PWID_OD_BASE_PROB = 'transition_PWID*Overdose*Base_Probability'
    PWID_OD_GENDER = 'transition_PWID*Overdose*Gender.Female'
    PWID_OD_JAIL_0_2 = 'transition_PWID*Overdose*Jail_Release.Week_0_2'
    PWID_OD_JAIL_3_4 = 'transition_PWID*Overdose*Jail_Release.Week_3_4'
    PWID_OD_JAIL_5 = 'transition_PWID*Overdose*Jail_Release.Week_5'
    PWID_OU_OD_AGE_25_34 = 'transition_PWID*Overdose*Age.25-34'
    PWID_OD_AGE_35_44 = 'transition_PWID*Overdose*Age.35-44'
    PWID_OD_AGE_45 = 'transition_PWID*Overdose*Age.45+'

    OU_OD_BASE_PROB = 'transition_OU*Overdose*Base_Probability'
    OU_OD_GENDER = 'transition_OU*Overdose*Gender.Female'
    OU_OD_JAIL_0_2 = 'transition_OU*Overdose*Jail_Release.Week_0_2'
    OU_OD_JAIL_3_4 = 'transition_OU*Overdose*Jail_Release.Week_3_4'
    OU_OD_JAIL_5 = 'transition_OU*Overdose*Jail_Release.Week_5'
    OU_OD_AGE_25_34 = 'transition_OU*Overdose*Age.25-34'
    OU_OD_AGE_35_44 = 'transition_OU*Overdose*Age.35-44'  #NOTE Age.45+

    if OU_OD_BASE_PROB in parameters.params:
        parameters.params[NIHU_OD_BASE_PROB] = parameters.params[OU_OD_BASE_PROB]
        parameters.params[PWID_OD_BASE_PROB] = parameters.params[OU_OD_BASE_PROB]
        parameters.params.pop(OU_OD_BASE_PROB)
    
    if OU_OD_GENDER in parameters.params:
        parameters.params[NIHU_OD_GENDER] = parameters.params[OU_OD_GENDER]
        parameters.params[PWID_OD_GENDER] = parameters.params[OU_OD_GENDER]
        parameters.params.pop(OU_OD_GENDER)

    if OU_OD_JAIL_0_2 in parameters.params:
        parameters.params[NIHU_OD_JAIL_0_2] = parameters.params[OU_OD_JAIL_0_2]
        parameters.params[PWID_OD_JAIL_0_2] = parameters.params[OU_OD_JAIL_0_2]
        parameters.params.pop(OU_OD_JAIL_0_2)
    
    if OU_OD_JAIL_3_4 in parameters.params:
        parameters.params[NIHU_OD_JAIL_3_4] = parameters.params[OU_OD_JAIL_3_4]
        parameters.params[PWID_OD_JAIL_3_4] = parameters.params[OU_OD_JAIL_3_4]
        parameters.params.pop(OU_OD_JAIL_3_4)
    
    if OU_OD_JAIL_5 in parameters.params:
        parameters.params[NIHU_OD_JAIL_5] = parameters.params[OU_OD_JAIL_5]
        parameters.params[PWID_OD_JAIL_5] = parameters.params[OU_OD_JAIL_5]
        parameters.params.pop(OU_OD_JAIL_5)
    
    if OU_OD_AGE_25_34 in parameters.params:
        parameters.params[NIHU_OU_OD_AGE_25_34] = parameters.params[OU_OD_AGE_25_34]
        parameters.params[PWID_OU_OD_AGE_25_34] = parameters.params[OU_OD_AGE_25_34]
        parameters.params.pop(OU_OD_AGE_25_34)

    if OU_OD_AGE_35_44 in parameters.params:
        parameters.params[NIHU_OD_AGE_35_44] = parameters.params[OU_OD_AGE_35_44]
        parameters.params[PWID_OD_AGE_35_44] = parameters.params[OU_OD_AGE_35_44]
        parameters.params[NIHU_OD_AGE_45] = parameters.params[OU_OD_AGE_35_44]
        parameters.params[PWID_OD_AGE_45] = parameters.params[OU_OD_AGE_35_44]
        parameters.params.pop(OU_OD_AGE_35_44)
    
    


def run(mpi4py_comm, config_file, additional_params):
    """Run the JCCM model with provided parameters
        
        Parameters
        ----------
        mpi4py_comm : mpi4py.MPI.Intracomm
            An MPI communicator instance
        config_file : str
            The model config (props) file that contains model property
            names and values delimitted by a '=' symbol.
        additional_params str
            String of aditional params in JSON string format, e.g.
            '{"Name":"Joe", "Age":34}'

    """
    
    global result
    result = "None."

    init_params(config_file, additional_params)
    
    # NOTE repast4py random.init() will set the numpy generator seed using the random.seed parameter

    # The config_file parent is the default data dir
    # TODO it would be better to set the data dir in the config file perhaps
    config_path = Path(config_file)
    data_dir = str(config_path.parent)

    parameters.params[DATA_DIR] = data_dir

    replace_input_param_names()

    global model
    model = Model(mpi4py_comm)

    if model.rank == 0:
        start = timer()

    model.run()

    if model.rank == 0:
        stop = timer()
        printf("Model run time: " + str(stop - start) + "s.")

    # global result
    result = "Done." # NOTE returned to swift-t to indicate run finished.
  
def get():
    global result
    return result