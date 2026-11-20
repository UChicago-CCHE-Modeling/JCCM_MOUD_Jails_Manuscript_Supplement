#
# Generate the UPF for JCCM intervention parameter strategies and sensitivity
# analysis.
#

library(data.table)
library(jsonlite)

# Contextual Parameters

#naloxone.level.jail <- c(0, 0.5, 1.0)
#naloxone.level.jail <- c(0.5)

`transition_OU*Overdose*Base_Probability` <- c(0.00043, 0.00066, 0.00086)
naloxone.level.community <- c(0, 0.5, 1.0)

jail.size <- c(4000, 6000, 11000)

jail.loi.fractions <- list(c(0.25, 0.25, 0.50))

# Institutional Parameters
jail.oud.screen.probability <- c(0.5, 0.7, 0.9)
moud.linkage.to.care.multiplier <- c(0, 1, 1.5, 2)

#jail.moud.wait.time.days <- c(1, 2, 3)
jail.moud.acceptance.rate <- c(0.2, 0.5, 0.8)

#jail.moud.type <- 'None'
#jail.moud.type <- 'Buprenorphine_Sublingual'
#jail.moud.type <- 'Methadone'
#jail.moud.type <- 'Buprenorphine_XR'
jail.moud.type <- 'Naltrexone_XR'

if (jail.moud.type == 'None'){
  jail.moud.acceptance.rate <- c(0) 
  jail.oud.screen.probability <- c(0) 
}

# use sorted = F to properly include vector entries
dt <- CJ(`naloxone.level.community` = naloxone.level.community,
         `cji.jail.initial.size` = jail.size,
         #`naloxone.level.jail` = naloxone.level.jail,
         `transition_OU*Overdose*Base_Probability` = `transition_OU*Overdose*Base_Probability`,
          `jail.oud.screen.probability` = jail.oud.screen.probability,
         `moud.linkage.to.care.multiplier` = moud.linkage.to.care.multiplier,

         `jail.moud.acceptance.rate` = jail.moud.acceptance.rate,
        `jail.moud.type` = jail.moud.type,
        `jail.loi.fractions` = jail.loi.fractions,
         
sorted = F)

dt[, experiment := .I]  # Provide a unique experiment ID for each row

# Convert input data.table row to a JSON line
dt_row_to_json <- function(row){
  return (toJSON(as.list(row), auto_unbox=TRUE, digits=NA))
}

# return a new data table with n replicates rows of the argument row
dt_replicates <- function(row, n_replicates){

  # NOTE will break if LOI is not used
  # TODO special handling of the jail LOI fractions vector, since it is otherwise
  #      being split up into different rows and we want the vector as one row cell.
  #      The problem is that as.data.table() below doesnt handle the vector properly.
  
  r2 <- row$jail.loi.fractions     # separate the LOI vector
  row$jail.loi.fractions <- NULL   # delete the LOI vector
  
  dt <- as.data.table(row)
  dt <- dt[rep(dt[, .I], n_replicates)]    
  
  dt[, random.seed := seq(n_replicates)]
  dt[, jail.loi.fractions := list(r2)]
  
  return (dt)
}

# Create the new data table with n stochastic replicates of each morris row
dt_reps_list <- apply(dt, MARGIN = 1, dt_replicates, n_replicates = 40)
dt_reps <- rbindlist(dt_reps_list)

# Insert a run number column of unique values
runs <- data.table(run=seq(nrow(dt_reps)))  
dt_reps <- cbind(runs, dt_reps)


# Convert the data table to an array of JSON lines and write to UPF file
upf_json <- apply(dt_reps, MARGIN = 1, dt_row_to_json)
writeLines(upf_json, "upf_json.txt")

# # Divides the input array x into n chunks
# chunk2 <- function(x,n) split(x, cut(seq_along(x), n, labels = FALSE)) 
# 
# parts <- chunk2(upf_json, 4)
# 
# for (i in 1:length(parts)){
#   writeLines(parts[[i]], paste0("upf_intervention_feb_06_22_part_",i,".txt"))
# }


