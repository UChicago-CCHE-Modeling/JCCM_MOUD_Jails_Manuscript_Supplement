# This file is part of the Justice Community Circulation Model
#
# Model constants

DATA_DIR = "data.dir"

BURNIN_PERIOD_DAYS = 'burnin.period.days'

CJI_ONLY = 'cji.only'
CJI_ALL_SIZE = 'cji.all.size'
CJI_FRACTION_PWID = 'cji.fraction.pwid'
CJI_FRACTION_NIHU = 'cji.fraction.nihu'
CJI_JAIL_INITIAL_SIZE = 'cji.jail.initial.size'
CJI_JAIL_DAILY_INTAKE = 'cji.jail.daily.intake'
CJI_OVERDOSE_TOLERANCE_DAYS = 'cji.overdose.tolerance.days'

CJI_GROUP_FRACTIONS_FILE = 'cji.group.fractions.file'

INITIAL_PERSONS_FILENAME = 'initial.persons.filename'

JAIL_OUD_SCREEN_WAIT_TIME_DAYS = 'jail.oud.screen.wait.time.days'
JAIL_OUD_SCREEN_PROBABILITY = 'jail.oud.screen.probability'

JAIL_MOUD_WAIT_TIME_DAYS = 'jail.moud.wait.time.days'
JAIL_MOUD_ACCEPTANCE_RATE = 'jail.moud.acceptance.rate'

JAIL_LOI_FRACTIONS = 'jail.loi.fraction'

OUTPUT_DIRECTORY = 'output.directory'
OUTPUT_FILE_FORMAT = 'output.file.format'
OUTPUT_FILE_FORMAT_CSV = 'csv'
OUTPUT_FILE_FORMAT_PARQUET = 'parquet'
OUTPUT_FILE_FORMAT_FEATHER = 'feather'

PROBABILITY_BYSTANDER = 'probability.bystander'
PROBABILITY_NALOXONE_ADMINISTRATION = 'probability.naloxone.administer'
PROBABILITY_NALOXONE_REVERSAL = 'probability.naloxone.reversal'
PROBABILITY_EMS = 'probability.ems'

MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE_METHADONE = 'moud.therapeutic.days.after.last.dose.methadone'
MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE_SLBUP = 'moud.therapeutic.days.after.last.dose.slbup'
MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE_XRBUP = 'moud.therapeutic.days.after.last.dose.xrbup'
MOUD_THERAPEUTIC_DAYS_AFTER_LAST_DOSE_XRNTX ='moud.therapeutic.days.after.last.dose.xrntx'

MOUD_TIME_ON_TREATMENT_FILE = 'moud.time.on.treatment.file'
MOUD_LINKAGE_TO_CARE_MULTIPLIER = 'moud.linkage.to.care.multiplier'

JAIL_MOUD_TYPE = 'jail.moud.type'
MOUD_OD_RISK = 'moud.od.risk'
MOUD_REARREST_RISK = 'moud.rearrest.risk'

NALOXONE_LEVEL_JAIL = 'naloxone.level.jail'
NALOXONE_LEVEL_JAIL_NETWORK = 'naloxone.level.jail.network'
NALOXONE_LEVEL_COMMUNITY = 'naloxone.level.community'
NALOXONE_REFILL = 'naloxone.refill'

NIHU_POPULATION_SIZE = 'nihu.population.size'
NIHU_GROUP_FRACTIONS_FILE = 'nihu.group.fractions.file'
PWID_GROUP_FRACTIONS_FILE = 'pwid.group.fractions.file'
PWID_POPULATION_SIZE = 'pwid.population.size'

RANDOM_SEED = 'random.seed'

STATE_TRANSITION_DATA_FILENAME = 'state.transition.data.filename'
STATE_TRANSITION_DATA_NALOXONE_INTERVENTION = "naloxone_intervention"
STATE_TRANSITION_DATA_BYSTANDER = "bystander"

STOP_AT = 'stop.at'