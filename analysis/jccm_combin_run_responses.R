#
# Summarize the JCCM run responses and group results on intervention levels.
#   
#
# The basic workflow is:
#     1. Each run folder should have a pre-computed model response file that each 
#        contain a signle row of data with model properties and model output 
#        responses.  This response file is usually created by an R file that is 
#        executed after the model run as part of the emews workflow.
#
#
# @author Eric Tatara
#

library(data.table)

# Clear environment
rm(list=ls())

# Base experiment dir containing run folders, run_0, run_1, ...
experiment_dir <- "D:/Projects/JCCM_Experiments/MOUD Sensitivity Analysis/jun 1 2026/2026_moud_ntxxr_linkage_2"

# Load the pre-computed model response files.
load_run <- function(run_folder){
  
  path <- paste0(run_folder,"/runs_response.csv")
  
  if (file.exists(path)){
    dt <- fread(path, fill=TRUE)
  }
  else{
    dt <- NULL
  }
  
  return (dt)
  
}

# Load the individual runs response output and stack into a datatable dt
dirs <- list.dirs (path=paste0(experiment_dir,"\\runs"), recursive=FALSE)
response_dt_list <- lapply(dirs, load_run)
dt <- rbindlist(response_dt_list)  # Stack the list of tables into a single DT
response_dt_list <- NULL           # clear mem

# TODO temp fix the LOI cols 15-18

colnames(dt)[16] <- "loi.low"
colnames(dt)[17] <- "loi.med"
colnames(dt)[18] <- "loi.hig"

dt$jail.loi.fractions <- NULL

#dt$jail.loi.fractions <- c(dt$loi.low, dt$loi.med)
dt[, jail.loi.fractions := paste0(loi.low, ",", loi.med, ",", loi.hig) ]

# Strip the YAML ':' delimiter from the prop names
old_cols <- colnames(dt)
new_cols <- gsub(':', '', old_cols)

setnames(dt, old=old_cols, new=new_cols)
setkey(dt, "run")


# individual run responses to single files
fwrite(dt, paste0(experiment_dir, "\\runs_response_combined.csv"))


