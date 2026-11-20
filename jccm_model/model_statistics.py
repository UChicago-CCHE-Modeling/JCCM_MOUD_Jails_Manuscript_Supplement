# This file is part of the Justice Community Circulation Model
#
# Logger classes for storing and writing event log files.
# 
# 

import csv
import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from enum import Enum

from repast4py import parameters
from .jccm_enums import *
from .jccm_utils import printf

class LogType(Enum):
    OVERDOSE = "overdose"
    DEATH = "death"
    TRANSITION = "transition"
    JAIL_INTAKE = "jail_intake"
    JAIL_RELEASE = "jail_release"
    ADMINISTER_TREATMENT = "administer_treatment"
    ENROLL_TREATMENT = "enroll_treament"
    DEATH_AVERTED = "death_averted"
    EMS_CALLED = "ems_called"
    JAIL_OUD_SCREEN = "jail_oud_screen"
    JAIL_START_MOUD = "jail_start_moud"
    JAIL_NO_START_MOUD = "jail_no_start_moud"
    MOUD_DURATION_DRAW = "moud_duration_draw"
    STOP_MOUD = "stop_moud"
    JAIL_CONTINUE_MOUD = "jail_continue_moud"
    MOUD_END_THERAPEUTIC_DOSE = "moud_end_therapeutic_dose"
    NONFATAL_OVERDOSE_MOUD = "nonfatal_overdose_moud"
    FATAL_OVERDOSE_MOUD = "fatal_overdose_moud"

class EventCounts:
    """ EventCounts class tabulates the numeric count of discrete events between 
        each call to Statistics.record_stats().
    """
    def __init__(self):
       self.reset()
    
    def reset(self):
        """ Reset the stats counters between file writes
        """
        self.deaths = 0
        self.overdoses = 0
        self.jail_intake = 0
        self.jail_release = 0
        self.deaths_averted = 0
        self.ems_calls = 0
    
    def increment(self,log_type):
        """ Increment the stats counters depending on the type of event.
        """
        if log_type == LogType.DEATH:
            self.deaths += 1
        elif log_type == LogType.OVERDOSE:
            self.overdoses += 1
        elif log_type == LogType.JAIL_INTAKE:
            self.jail_intake += 1
        elif log_type == LogType.JAIL_RELEASE:
            self.jail_release += 1
        elif log_type == LogType.DEATH_AVERTED:
            self.deaths_averted += 1
        elif log_type == LogType.EMS_CALLED:
            self.ems_calls += 1
    
    #TODO implement additional event counts
    def getHeader(self):
        return ["deaths", "overdoses", "jail_intake", "jail_release", "deaths_averted", "ems_calls"]
    
    def getCounts(self):
        return [str(self.deaths),str(self.overdoses),str(self.jail_intake),str(self.jail_release),str(self.deaths_averted),str(self.ems_calls)]

class EventLogger:
    """ Event logger that writes to event lines to a parquet file. Each event 
        is a separate row in the pyarrow table.
    """
    def __init__(self, event_file):
        """ Constructor
        """
        self.reset()

        # Define the pyarrow table schema - column names and types
        self.event_cols = {
            "tick":pa.float32(),
            "event":pa.string(),
            "person":pa.int32(),
            "message":pa.string()}
       
        event_schema = pa.schema(self.event_cols)
        self.writer = pq.ParquetWriter(f'{event_file}_2.parquet', event_schema, compression='GZIP')

    def log_event(self, tick, log_type, person, message: str):
        """ Log the discrete event to memory using plain python lists.  Each 
            event component is stored in its corresponding component list.
        """
        self.tick.append(tick)
        self.type.append(log_type.value)
        self.person.append(person.id)
        self.message.append(message)

    def write_data(self):
        """ Write the memory stored event data to the parquet file.
        """
        data = [
            pa.array(self.tick, type=self.event_cols["tick"]),
            pa.array(self.type, type=self.event_cols["event"]),
            pa.array(self.person, type=self.event_cols["person"]),
            pa.array(self.message, type=self.event_cols["message"])        
        ]

        batch = pa.RecordBatch.from_arrays(data, list(self.event_cols.keys()))
        table = pa.Table.from_batches([batch])

        self.writer.write_table(table)

        self.reset() 


    def reset(self):
        """ Reset the python list memory storage between file writes
        """
        self.tick = []
        self.type = []
        self.person = []
        self.message = []

    def close(self):
        self.writer.close()

class AggregateStats:
    """ AggregatesStats class tabulates aggregate data for the Person agent population
    """

    def __init__(self):
        self.reset()
      
    def reset(self):
        self.jail_population = 0
        self.num_nihu = 0
        self.num_pwid = 0
        self.num_non_oud = 0

    def update(self, persons):
        """ Update the aggregate stats accross all persons in the list.
        """
        for p in persons:
            if p.currently_incarcerated:
                self.jail_population += 1

            if p.state == StateType.NIHU:
                self.num_nihu += 1
            elif p.state == StateType.Non_OUD:
                self.num_non_oud += 1
            elif p.state == StateType.PWID:
                self.num_pwid += 1    

    #TODO implement additional event counts
    def getHeader(self):
        return ["jail_population", "State.NIHU", "State.PWID", "State.Non_OUD"]
    
    def getCounts(self):
        return [str(self.jail_population),str(self.num_nihu),str(self.num_pwid),str(self.num_non_oud)]


class Statistics:
    """Statistics class records changes in all agent attributes and compiles
    additional summary aggregate statistics.
    
    Attributes
    ----------
    __instance : Statistics
        Statistics singleton
    events_writer : csv.writer
        CSV writer for events log data
    stats_writer : csv.writer
        CSV writer for stats log data
    
    """
    
    __instance = None
   
    @staticmethod 
    def getInstance():
        return Statistics.__instance
   
    def __init__(self):
        """Constructor
        
        Parameters
        ----------
        
        """
        
        Statistics.__instance = self
        
        output_dir = parameters.params['output.directory']

        events_fname = os.path.join(output_dir, parameters.params['event.filename'])
        stats_fname = os.path.join(output_dir, parameters.params['stats.filename'])

        self.event_counts = EventCounts()
        self.aggregate_stats = AggregateStats()
        
        # TODO return to the parquet file logger later.  It turns out that
        #      simply converting the CSV file to parquet post run results in
        #      a 50% smaller parquet file, probably due to more efficient 
        #      compression of the complete table (or maybe pandas doing something?).
        # self.event_logger = EventLogger(events_fname)

        self.event_file = open(f'{events_fname}.csv','w', newline='')
        self.stats_file = open(f'{stats_fname}.csv','w', newline='')
        
        self.event_writer = csv.writer(self.event_file)
        self.stats_writer = csv.writer(self.stats_file)
        
        # Write headers
        self.event_writer.writerow(["tick","event","person","message"])
        self.stats_writer.writerow(["tick"] + self.event_counts.getHeader() + 
            self.aggregate_stats.getHeader())
        
        self.log_events = []    # clear the event log cache
        

    def log_status(self, tick, log_type, person, message: str = ''):
        """Record the status change in the log cache
        
        Parameters
        ----------
        tick : float
            the model tick
        log_type : LogType
            the log type enum
        person : Person
            the person whose event to be logged
        message : str
            an optional message
        """
        
        # Each line is a list of strings
        line = [str(tick), str(log_type.value), str(person.id), message]
        
        # Add the current line to the event log list to be written later
        self.log_events.append(line)

        # TODO return to the parquet file logger later.
        # self.event_logger.log_event(tick, log_type, person, message)
                
        self.event_counts.increment(log_type)
        
    def record_stats(self, tick, persons):
        """Writes any cached stats to file for each of the event loggers.
        
        Parameters
        ----------
        tick : float
            the model tick
        persons : list
            a list of persons for which to log stats
        """

        # Update the persons agent population aggregate stats
        self.aggregate_stats.update(persons)
        
        # Write the list of all cached discrete events that have occured since
        #   the previous tick
        self.event_writer.writerows(self.log_events)
        
        # Write the summary stats and aggregate stats for this tick
        self.stats_writer.writerow([str(tick)] + self.event_counts.getCounts() + 
            self.aggregate_stats.getCounts())
        
        # clear caches
        self.log_events = []
        self.event_counts.reset()
        self.aggregate_stats.reset()
        
        # Flushing files ensures incremental save
        self.event_file.flush()
        self.stats_file.flush()

        # TODO return to the parquet file logger later.
        # self.event_logger.write_data()
            
    def close(self):
        """Flush and close the log files
        """
        self.event_file.flush()
        self.event_file.close()

        self.stats_file.flush()
        self.stats_file.close()

        # TODO return to the parquet file logger later.
        # self.event_logger.close()

        __instance = None
        