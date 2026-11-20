# This file is part of the Justice Community Circulation Model
#
# Misc utility functions.
# 
# 
import sys
import pandas as pd
from repast4py import random

def printf(msg):
    print(msg)
    sys.stdout.flush()

def fast_choice(options:list, probs:list):
    """ Return a random sample from options using the discrete probability 
        values in prob.
        Works in a similar way to random.choices() or numpy.random.choice(),
        but with much better performance when only one object is sampled.

        Parameters
        ----------
        options : list
            List of objects from which to randomly sample one
        probs : list
            List of discrete probabilities of selecting object from options list.
    """
    x = random.default_rng.random()
    cum = 0
    for i, p in enumerate(probs):
        cum += p
        if x < cum:
            return options[i]
        
    return options[-1]

def fast_choice_uniform(options: list, probs: list):
    """ Like fast_choice, but treats `options` as the upper edges of
        contiguous bins and returns a uniform random draw within the
        selected bin's interval [options[i-1], options[i]].

        For i == 0, the lower edge defaults to 0.0.
        The fallback case returns uniform(options[-2], options[-1]).

        Parameters
        ----------
        options : list
            Sorted numeric bin edges.
        probs : list
            Discrete probability of selecting each bin (len == len(options)).
    """
    x = random.default_rng.random()
    cum = 0
    for i, p in enumerate(probs):
        cum += p
        if x < cum:
            lo = options[i - 1] if i > 0 else 0.0
            hi = options[i]
            return lo + (hi - lo) * random.default_rng.random()

    lo, hi = options[-2], options[-1]
    return lo + (hi - lo) * random.default_rng.random()

def print_run_summary(model_output_stats_file, burn_in_days):
    """Print basic run stats from the model output stats file.

        Parameters
        ----------
        model_output_stats_file : str
            model output stats file (CSV)
        burn_in_days : float
            days for burn in period to remove from stats
    """
    
    # Read the stats.csv into a pandas data frame to print basic run stats
    stats_df = pd.read_csv(model_output_stats_file)

    # Filter out collected stats during burn in
    subset_df = stats_df[stats_df["tick"] > burn_in_days]

    total_deaths = subset_df.deaths.sum()
    total_overdoses = subset_df.overdoses.sum()
    deaths_averted = subset_df.deaths_averted.sum()
    ems_calls = subset_df.ems_calls.sum()

    printf(
        f'Total Deaths: {total_deaths}, Total Overdoses: {total_overdoses},'
        f' Deaths Averted: {deaths_averted}, EMS Calls: {ems_calls}'
    )