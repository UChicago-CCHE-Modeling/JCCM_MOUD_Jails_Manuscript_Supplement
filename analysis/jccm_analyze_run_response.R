#
# Analyze JCCM model run response variables
#
# !! IMPORTANT !! - This file is used by the emews workflow to calculate each
#    run response.  Make sure changes are appropriate.
#
# Returns a single row data frame containing all of the run properties and summary
# statistics for the run, e.g. total number of overdoses, deaths, etc.  This
# function is called by the swift-t script at the conclusion of a model run.  For
# analysis purposes, a second R script is then run manually to load all of the
# individual run response CSV files and calculate means across stochastic replicates
# and various visualization or tabular results.
#

# Tabulate the response variables for the specified run folder.
# Returns a single row data table with the run properties and response variables
tabulate_run <- function(run_folder, use_parquet, warm_up = 0){
  library(data.table)
  
  if (use_parquet){
	library(arrow)
  }
  
  stats_prefix <- "stats"
  events_prefix <- "events"
  persons_prefix <- "initial_persons"
  
  # Each run can have multiple output files since each rank will have a separate file.
  stats_files <- list.files(path=run_folder, pattern = paste0('^', stats_prefix))
  events_files <- list.files(path=run_folder, pattern = paste0('^', events_prefix))
  persons_files <- list.files(path=run_folder, pattern = paste0('^', persons_prefix))
  
  if (!file.exists(paste0(run_folder,'/',stats_files))){
    warning(paste0("File doesnt exist! ", paste0(run_folder,'/',stats_files)))
  }
  else{
    
    print(paste0("Loading ", run_folder ))
    tryCatch({
      
      # Read the model.props for optional storing of parameter values
      # First col is the prop names, second col is the prop values
      propsRead <- fread(paste0(run_folder,"/model_props.yaml"), fill=TRUE)
      
      # Strip the YAML ':' delimiter from the prop names
      propsRead$V1 <- gsub(':','',propsRead$V1)
      props <- propsRead[,1]
      props$Value <- propsRead[,2]
      colnames(props)<-c("Name", "Value")
      
      # Data table of one observation of n props to merge with response values
      props_dt <- transpose(props, make.names = "Name")
      
      # There may be multiple results files for differnt ranks, so combine
      # Table of model stats
      # stats_list <- list()
      # for (f in stats_files){
      #   path <- paste0(run_folder,'/',f)
      #   table <- fread(path)
      #   
      #   stats_list[[f]] <- table
      # }
      # stats_dt <- rbindlist(stats_list)  # Stack the list of tables into a single DT
      
      # Table of events
      events_list <- list()
      for (f in events_files){
        path <- paste0(run_folder,'/',f)
        
        if (use_parquet){
          table <- read_parquet(path)  # data frame 
        } else{
          table <- fread(path)
        }
        events_list[[f]] <- table
      }
      events_dt <- rbindlist(events_list)  # Stack the list of tables into a single DT
      
      # Table of persons 
      persons_list <- list()
      for (f in persons_files){
        path <- paste0(run_folder,'/',f)
        
        if (use_parquet){
          table <- read_parquet(path)  # data frame
        } else{
          table <- fread(path)
        }
        persons_list[[f]] <- table
      }
      persons_dt <- rbindlist(persons_list)  # Stack the list of tables into a single DT
      
      # Collect the person IDs for various subgroups to count events specific to each
      
      male_persons_ids <- persons_dt[Gender == "Male"]$ID
      female_persons_ids <- persons_dt[Gender == "Female"]$ID
      
      black_persons_ids <- persons_dt[Race == "Black"]$ID
      white_persons_ids <- persons_dt[Race == "NHWhite"]$ID
      hispanic_persons_ids <- persons_dt[Race == "Hispanic"]$ID
      race_other_persons_ids <- persons_dt[Race == "Other"]$ID
      
      age_18_persons_ids <- persons_dt[Age == "18-24"]$ID
      age_25_persons_ids <- persons_dt[Age == "25-34"]$ID
      age_35_persons_ids <- persons_dt[Age == "35-44"]$ID
      age_45_persons_ids <- persons_dt[Age == "45+"]$ID
      
      #overdoses <- sum(stats_dt$overdoses)
      #deaths <- sum(stats_dt$deaths)
      
      # Use the events table to calculate all statistics.  If the warm up period
      #  is provided, use it to filter all events prior during the warm up.
      
      events_dt <- events_dt[tick > warm_up]
      
      setkey(events_dt, event, person)
      
      overdose_events <- events_dt[event == "overdose"]
      death_events <- events_dt[event == "death"]
      death_averted_events <- events_dt[event == "death_averted"]
      naloxone_distributed_events <- events_dt[event == "enroll_treament"]
      ems_events <- events_dt[event == "ems_called"]
      
      jail_release_events <- events_dt[event == "jail_release"]
      jail_release_non_oud <- jail_release_events[message == "JailState.NON_OUD"]
      jail_release_moud <- jail_release_events[message == "JailState.OUD_MOUD"]
      jail_release_moud_wait_screen <- jail_release_events[message == "JailState.WAIT_FOR_OUD_SCREEN"]
      jail_release_moud_wait_moud <- jail_release_events[message == "JailState.WAIT_FOR_MOUD"]
      
      jail_release_non_oud_all <- nrow(jail_release_non_oud)
      jail_release_moud_all <- nrow(jail_release_moud)
      jail_release_moud_wait_screen_all <- nrow(jail_release_moud_wait_screen)
      jail_release_moud_wait_moud_all <- nrow(jail_release_moud_wait_moud)
      
      overdoses_all <- nrow(overdose_events)
      deaths_all <- nrow(death_events)
      deaths_averted_all <- nrow(death_averted_events)
      naloxone_distributed_all <- nrow(naloxone_distributed_events)
      ems_calls <- nrow(ems_events)
      
      response_dt <- data.table(overdoses_all=overdoses_all, deaths_all=deaths_all, 
                                deaths_averted_all=deaths_averted_all,
                                naloxone_distributed_all=naloxone_distributed_all,
                                ems_calls=ems_calls,
                                jail_release_non_oud_all=jail_release_non_oud_all,
                                jail_release_moud_all=jail_release_moud_all,
                                jail_release_moud_wait_screen_all=jail_release_moud_wait_screen_all,
                                jail_release_moud_wait_moud_all=jail_release_moud_wait_moud_all)
      
      setkey(death_events, person)
      setkey(overdose_events, person)
      
      # MOUD treatment duration 
      stop_moud_events <- events_dt[event == "stop_moud"]
      response_dt$mean_moud_time_on_treatment <- mean(as.numeric(stop_moud_events$message))
      
      # Death events
      response_dt$deaths_male <- nrow(death_events[person %in% male_persons_ids])  
      response_dt$deaths_female <- nrow(death_events[person %in% female_persons_ids])
      
      response_dt[, deaths_black := nrow(death_events[person %in% black_persons_ids])]
      response_dt[, deaths_white := nrow(death_events[person %in% white_persons_ids])]
      response_dt[, deaths_hispanic := nrow(death_events[person %in% hispanic_persons_ids])]
      response_dt[, deaths_race_other := nrow(death_events[person %in% race_other_persons_ids])]

      response_dt[, deaths_age_18 := nrow(death_events[person %in% age_18_persons_ids])]
      response_dt[, deaths_age_25 := nrow(death_events[person %in% age_25_persons_ids])]
      response_dt[, deaths_age_35 := nrow(death_events[person %in% age_35_persons_ids])]
      response_dt[, deaths_age_45 := nrow(death_events[person %in% age_45_persons_ids])]

      # Overdose events
      response_dt[, overdoses_male := nrow(overdose_events[person %in% male_persons_ids])]
      response_dt[, overdoses_female := nrow(overdose_events[person %in% female_persons_ids])]

      response_dt[, overdoses_black := nrow(overdose_events[person %in% black_persons_ids])]
      response_dt[, overdoses_white := nrow(overdose_events[person %in% white_persons_ids])]
      response_dt[, overdoses_hispanic := nrow(overdose_events[person %in% hispanic_persons_ids])]
      response_dt[, overdoses_race_other := nrow(overdose_events[person %in% race_other_persons_ids])]

      response_dt[, overdoses_age_18 := nrow(overdose_events[person %in% age_18_persons_ids])]
      response_dt[, overdoses_age_25 := nrow(overdose_events[person %in% age_25_persons_ids])]
      response_dt[, overdoses_age_35 := nrow(overdose_events[person %in% age_35_persons_ids])]
      response_dt[, overdoses_age_45 := nrow(overdose_events[person %in% age_45_persons_ids])]
      
      
      # Subset events for persons who are released from jail
      released_persons_ids <- events_dt[event == "jail_release"]$person
      released_persons_events <- events_dt[person %in% released_persons_ids]

      released_persons_death_events <- released_persons_events[event == "death"]
      released_persons_overdose_events <- released_persons_events[event == "overdose"]
      released_persons_death_averted_events <- released_persons_events[event == "death_averted"]
      
      # Naloxone can be distributed to released persons through a jail intervention, or
      #   jail network intervention, and released persons can also obtain refills, so we need
      #   to differentiate between the various modes.
      
      released_persons_naloxone_distributed_events <- released_persons_events[event == "enroll_treament"]
      
      naloxone_jail_events <- released_persons_naloxone_distributed_events[message == "Naloxone_Jail"]
      naloxone_jail_network_events <- released_persons_naloxone_distributed_events[message == "Naloxone_Jail_Network"]
      
      setkey(released_persons_death_events, person)
      setkey(released_persons_overdose_events, person)
      
      # Death events
      response_dt[, released_persons_deaths := nrow(released_persons_death_events)]
      response_dt[, released_persons_overdoses := nrow(released_persons_overdose_events)]
      response_dt[, released_persons_deaths_averted := nrow(released_persons_death_averted_events)]
      
      response_dt[, naloxone_distributed_jail := nrow(naloxone_jail_events)]
      response_dt[, naloxone_distributed_jail_network := nrow(naloxone_jail_network_events)]

      response_dt[, released_persons_deaths_male := nrow(released_persons_death_events[person %in% male_persons_ids])]
      response_dt[, released_persons_deaths_female := nrow(released_persons_death_events[person %in% female_persons_ids])]

      response_dt[, released_persons_deaths_black := nrow(released_persons_death_events[person %in% black_persons_ids])]
      response_dt[, released_persons_deaths_white := nrow(released_persons_death_events[person %in% white_persons_ids])]
      response_dt[, released_persons_deaths_hispanic := nrow(released_persons_death_events[person %in% hispanic_persons_ids])]
      response_dt[, released_persons_deaths_race_other := nrow(released_persons_death_events[person %in% race_other_persons_ids])]

      response_dt[, released_persons_deaths_age_18 := nrow(released_persons_death_events[person %in% age_18_persons_ids])]
      response_dt[, released_persons_deaths_age_25 := nrow(released_persons_death_events[person %in% age_25_persons_ids])]
      response_dt[, released_persons_deaths_age_35 := nrow(released_persons_death_events[person %in% age_35_persons_ids])]
      response_dt[, released_persons_deaths_age_45 := nrow(released_persons_death_events[person %in% age_45_persons_ids])]

      # Overdose events
      response_dt[, released_persons_overdoses_male := nrow(released_persons_overdose_events[person %in% male_persons_ids])]
      response_dt[, released_persons_overdoses_female := nrow(released_persons_overdose_events[person %in% female_persons_ids])]

      response_dt[, released_persons_overdoses_black := nrow(released_persons_overdose_events[person %in% black_persons_ids])]
      response_dt[, released_persons_overdoses_white := nrow(released_persons_overdose_events[person %in% white_persons_ids])]
      response_dt[, released_persons_overdoses_hispanic := nrow(released_persons_overdose_events[person %in% hispanic_persons_ids])]
      response_dt[, released_persons_overdoses_race_other := nrow(released_persons_overdose_events[person %in% race_other_persons_ids])]

      response_dt[, released_persons_overdoses_age_18 := nrow(released_persons_overdose_events[person %in% age_18_persons_ids])]
      response_dt[, released_persons_overdoses_age_25 := nrow(released_persons_overdose_events[person %in% age_25_persons_ids])]
      response_dt[, released_persons_overdoses_age_35 := nrow(released_persons_overdose_events[person %in% age_35_persons_ids])]
      response_dt[, released_persons_overdoses_age_45 := nrow(released_persons_overdose_events[person %in% age_45_persons_ids])]

      
      # Append run info
      run_dt <- cbind(props_dt, response_dt)
      #response_tableList[[d]]  <- run_dt
      
      return (run_dt)
    }, 
    warning = function(w) {
      print(paste0("Error loading file: ", path, " ", w))
    },
    error = function(e) {
      print(paste0("Error loading file: ", path, " ", e))
    }, 
    finally = {
    }
    )
  }
}
