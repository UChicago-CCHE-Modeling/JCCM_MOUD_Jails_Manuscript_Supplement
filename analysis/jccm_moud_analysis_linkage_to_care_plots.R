#
# JCCM MOUD analysis
#
# Assumes that all runs summaries have been collated into a single results CSV.
#   
#
# This code plots associations between linkage to care and OD mortality by MOUD type across 
# I and C-space parameters. 

library(data.table)
library(ggplot2)
library(ggridges)
library("scales") 

library(tidyverse)

#base_dir <- "../"
#output_dir <- "../plots_jun_2026/"
base_dir <- "D:/Projects/JCCM_Experiments/MOUD Sensitivity Analysis/jun 1 2026/"
output_dir <- base_dir

# specify date for saving files
timestamp <- format(Sys.time(), "%Y-%m-%d")

# Load the data - Option 1 - Load a single CSV containing all runs
#  Will need to subset the data below for arbitrary combinations of parameters (scenarios)
dt <- fread(paste0(base_dir, "all_runs_response_combined.csv"))


# Std Err
std <- function(x) sd(x)/sqrt(length(x))

# 95% CI
z <- 1.960




# Create a unique I-space intervention/experiment ID for each unique combination 
# of the I-Space parameters
add_i_space_label <- function(x){
  
  moud <- x["jail.moud.type"]
  acc_rate <- as.numeric(x["jail.moud.acceptance.rate"])
  scr_prob <- as.numeric(x["jail.oud.screen.probability"])
  
  accept_label <- paste0("Acc Rate: ", acc_rate)
  screen_label <- paste0("Scr Rate: ", scr_prob)
  
  exp_label <- paste0(accept_label, " - ", screen_label, " - ", moud)
  #exp_label <- paste0(moud, ": ", accept_label, " - ", screen_label)
  
  return (exp_label)
  
}

# Create a unique C-space intervention/experiment ID for each unique combination 
# of the C-Space parameters
add_c_space_label <- function(x){
  
  jail_label <- as.numeric(x["cji.jail.initial.size"])
  nalox_label <- as.numeric(x["naloxone.level.community"])
  odrate_label <- as.numeric(x["transition_NIHU*Overdose*Base_Probability"])
  
  exp_label <- paste0(jail_label, " - ", nalox_label, " - ", odrate_label)
  
  return (exp_label)
  
}


dt$moud.linkage.to.care.multiplier <- as.double(dt$moud.linkage.to.care.multiplier)

#dt$jail.moud.type <- gsub('_','\n',dt$jail.moud.type)

# For UI/visualization
dt$jail.moud.label <- dt$jail.moud.type # copy all
dt$jail.moud.label <- gsub('Buprenorphine_Sublingual','Buprenorphine (SL)',dt$jail.moud.label)
dt$jail.moud.label <- gsub('Buprenorphine_XR','Buprenorphine (XR)',dt$jail.moud.label)
dt$jail.moud.label <- gsub('Naltrexone_XR','Naltrexone (XR)',dt$jail.moud.label)

# For filtering or plot labels
dt$jail.moud.type <- gsub('Methadone','Meth',dt$jail.moud.type)
dt$jail.moud.type <- gsub('Buprenorphine_Sublingual','BupSL',dt$jail.moud.type)
dt$jail.moud.type <- gsub('Buprenorphine_XR','BupXR',dt$jail.moud.type)
dt$jail.moud.type <- gsub('Naltrexone_XR','NtXR',dt$jail.moud.type)

years = unique(dt$stop.at - dt$burnin.period.days) / 365

# At risk population is persons with CJI who are OUD (not just persons released)
# NOTE - assumes fixed parameter values across runs!
at_risk_pop_size <- unique(dt$cji.fraction.nihu + dt$cji.fraction.pwid) * unique(dt$cji.all.size)

person_years <- at_risk_pop_size * years
person_years_1k <- person_years / 1000

dt[, released_persons_od_mortality_rate := released_persons_deaths/person_years_1k]

dt$experiment_label <- apply(dt, 1, add_i_space_label)
dt$c_space_label <- apply(dt, 1, add_c_space_label)

# NOTE `transition_OU*Overdose*Base_Probability` input param is explictely converted to
#   transition_NIHU and transition_PWID in the model, so just pick one name

# rename for ease of plotting
# this is the daily probability of overdose in the population expressed as a percentage? 
dt[, od_base_prob := 100*`transition_NIHU*Overdose*Base_Probability`]


my_theme <- 
  theme_bw() +
  theme(axis.text=element_text(size=8),axis.title=element_text(size=8),legend.text=element_text(size=8))

my_legend_theme <- my_theme + theme(legend.position.inside = c(0.15, 0.8), 
                                    legend.text=element_text(size=8), 
                                    legend.background=element_blank(),
                                    legend.box.background=element_rect(colour = "black"), axis.text=element_text(size=8),
                                    axis.title=element_text(size=8))




#### AH changes start here
# grouping variables:
#jail.moud.type
#jail.moud.acceptance.rate
#jail.oud.screen.probability

#cji.jail.initial.size
#naloxone.level.community - what do values of 0,0.5, and 1 mean? 

#transition_NIHU*Overdose*Base_Probability - baseline od rate
# note: may want to change this to low, medium, high

#moud.linkage.to.care.multiplier
# question: what does a multiplier of 1, 2, etc actually translate to in terms of prevalence of linkage to care

# outcome: released_persons_od_mortality_rate

# plots

# install.packages("ggh4x")

# New facet label names for MOUD acceptance and screening rates

acc_labels <- c( "0.2" = "20%", "0.5" = "50%", "0.8" = "80%") 

scrn_labels <- c("0.5" = "50%", "0.7" = "70%", "0.9" = "90%")

# create a dataset with just the moud scenarios to add to plots
# rename rates no moud rates
# get rid of any unnecessary variables
# merge back with dt by jail size, naloxone, and od base rate
dt_no_moud <- dt %>% filter(jail.moud.type == "None") %>%
  select(jail.moud.type, 
         jail.moud.acceptance.rate, 
         jail.oud.screen.probability, 
         cji.jail.initial.size, 
         naloxone.level.community, 
         moud.linkage.to.care.multiplier, 
         od_base_prob, 
         released_persons_od_mortality_rate, 
         random.seed) %>%
  # we don't need to group by moud type, acceptance, or screening b/c these are all 0
  group_by(cji.jail.initial.size, 
           naloxone.level.community, 
           od_base_prob) %>%
    mutate(mean_rate_no_moud = mean(released_persons_od_mortality_rate), # could add median here
    sd_rate = sd(released_persons_od_mortality_rate),
    n_total = n(),
    se_rate = sd_rate/sqrt(n_total),
    # Calculate the 95% Confidence Interval (CI)
    # Use qt for the t-distribution quantile (for 95% CI, alpha = 0.05)
    # do this for quantiles instead probably
    lci_rate_no_moud = mean_rate_no_moud - qt(1 - (0.05 / 2), n_total - 1) * se_rate,
    uci_rate_no_moud = mean_rate_no_moud + qt(1 - (0.05 / 2), n_total - 1) * se_rate) %>%
  select(c(random.seed, mean_rate_no_moud, cji.jail.initial.size, naloxone.level.community, od_base_prob))

print(dt_no_moud)


dt_with_no_moud <- left_join(dt, dt_no_moud, by = c("cji.jail.initial.size", 
                                                    "naloxone.level.community", 
                                                    "od_base_prob", "random.seed"))


# this is an example plot for modifying as needed
# the function below can then be used to plot any combination of jail size, moud type, and naloxone levels

library(viridis)

p1 <- ggplot(dt_with_no_moud %>% filter(cji.jail.initial.size == 11000 & 
                                          jail.moud.type == "Meth" & 
                                          naloxone.level.community == 0.5), 
             aes(y=as.factor(moud.linkage.to.care.multiplier), 
                             x=released_persons_od_mortality_rate,
                 color = as.factor(paste0(od_base_prob,"%")),
             fill = as.factor(paste0(od_base_prob, "%")))) +
  
  # add the rate for no moud
  geom_vline(aes(xintercept = mean_rate_no_moud, color = as.factor(paste0(od_base_prob,"%"))), 
             linetype = "dashed", linewidth = 0.6) +
  geom_violin(trim = TRUE, position = position_dodge(width = 0), 
              width = 3.0, alpha = 0.6) + #, draw_quantiles = c(0.25, 0.5, 0.75)) +
  labs(y="Linkage to care multiplier", x="OD Mortality per 1000 person-years", color = "Baseline OD probability") +
  #scale_fill_discrete(name="Baseline OD Rate", guide = guide_legend(reverse=FALSE), values = colors) +
  #scale_color_discrete(name="Baseline OD Rate", guide = guide_legend(reverse=FALSE), values = colors) +
  
  #scale_fill_manual(name="Baseline OD Rate", guide = guide_legend(reverse=FALSE), values = colors) +
  #scale_color_manual(name="Baseline OD Rate", guide = guide_legend(reverse=FALSE), values = colors) +
  
  scale_fill_viridis_d(name="Baseline OD Rate", guide = guide_legend(reverse=FALSE), option = "viridis", direction = -1, begin = 0, end = 0.5) +
  scale_color_viridis_d(name="Baseline OD Rate", guide = guide_legend(reverse=FALSE), option = "viridis", direction = -1, begin = 0, end = 0.5) +
  
  scale_x_continuous(limits = c(5,45)) +
  scale_y_discrete(limits = rev) +
  my_theme + theme(legend.position = "bottom",
                   legend.text=element_text(size=12), 
                   legend.background=element_blank(),
                   axis.text=element_text(size=12),
                   axis.title=element_text(size=12),
                   strip.placement = "outside",
                   strip.background = element_blank(),
                   strip.text = element_text(size = 12), # Changes size of all facet labels
                   strip.text.y = element_text(size = 12)) + # Specifically for vertical facet labels
  #ggtitle("Buprenorphine SL") + 
  

ggh4x::facet_nested("MOUD Acceptance Probability" + jail.moud.acceptance.rate ~
                    "OUD Screening Probability" + jail.oud.screen.probability,
                    labeller = labeller(jail.oud.screen.probability = scrn_labels,   
                    jail.moud.acceptance.rate = acc_labels))

show(p1)

#ggsave(paste0(output_dir, timestamp, "_MOUD_Linkage_BupSL.png"), p1, dpi = 400, width=10, height=8)


# Another option is boxplots with geom_point to display replicates; this might not show up well
p2 <- ggplot(dt %>% filter(cji.jail.initial.size == 6000 & jail.moud.type =="BupXR"), 
             aes(y=as.factor(moud.linkage.to.care.multiplier),  
                 x=released_persons_od_mortality_rate, 
                 color = as.factor(paste0(od_base_prob,"%")))) +
  geom_boxplot(outlier.shape = NA, size = 0.8, position = position_dodge(width = 0)) + 
  geom_point(position=position_jitterdodge(jitter.width=2.0, dodge.width = 0, seed = 1), 
             pch=19, size=0.8, alpha=0.15, aes( 
               group=factor(paste0(od_base_prob,"%")))) +
  labs(y="Linkage to care multiplier", x="OD Mortality per 1000py", color = "Baseline OD probability") +
  scale_fill_discrete(name="Baseline OD Rate", guide = guide_legend(reverse=TRUE)) +
  scale_x_continuous(limits = c(10,45)) +
  scale_y_discrete(limits = rev) +
  #scale_color_viridis_d() +
  my_theme + theme( 
    legend.position = "bottom",
    legend.text=element_text(size=14), 
    legend.background=element_blank(),
    axis.text=element_text(size=14),
    axis.title=element_text(size=14),
    strip.placement = "outside",
    strip.background = element_blank(),
    strip.text = element_text(size = 14), # Changes size of all facet labels
    strip.text.y = element_text(size = 14)) + # Specifically for vertical facet labels
  ggtitle("Buprenorphine XR") + 
  
  ggh4x::facet_nested("MOUD Acceptance Probability" + jail.moud.acceptance.rate ~
                        "OUD Screening Probability" + jail.oud.screen.probability,
                      labeller = labeller(jail.oud.screen.probability = scrn_labels,   
                                          jail.moud.acceptance.rate = acc_labels))
show(p2)



##########

# Make a function for plotting
# need to pecify the output directory and/or the datestamp in the function for saving?
# we should have the output directory be an input probably TO DO

create_plots_by_moud_type <- function(data, jail_size, moud_type, naloxone_level, output_dir){
  
  # Facet label names for MOUD acceptance and screening rates
  acc_labels <- c( "0.2" = "20%", "0.5" = "50%", "0.8" = "80%")
  scrn_labels <- c("0.5" = "50%", "0.7" = "70%", "0.9" = "90%")

  # Descriptive y-axis labels for the linkage to care multiplier
  ltc_labels <- c("0" = "None", "0.5" = "Reduced", "1" = "Baseline", "2" = "Increased")
  
  # add date for saving
  timestamp <- format(Sys.time(), "%Y-%m-%d")
  
  output_dir <- output_dir

plot_data <- data %>% filter(cji.jail.initial.size == jail_size &
                                          jail.moud.type == moud_type &
                                          naloxone.level.community == naloxone_level) %>%
  # map the three discrete od_base_prob values to relative baseline labels
  mutate(od_base_label = factor(od_base_prob,
                                levels = sort(unique(od_base_prob)),
                                labels = c("Low", "Medium", "High")))

p <- ggplot(plot_data,
             aes(y=as.factor(moud.linkage.to.care.multiplier),
                 x=released_persons_od_mortality_rate,
                 color = od_base_label,
                 fill = od_base_label)) +

  # add the rate for no moud
  geom_vline(aes(xintercept = mean_rate_no_moud, color = od_base_label),
             linetype = "dashed", linewidth = 0.6) +
#  geom_violin(trim = TRUE, position = position_dodge(width = 0), 
#              width = 3.0, alpha = 0.6) + #, draw_quantiles = c(0.25, 0.5, 0.75)) +
  geom_density_ridges(scale = 0.7, alpha = 0.6, rel_min_height = 0.01) +
  labs(y="Linkage to care", x="OD Mortality per 1000 person-years") +
  scale_fill_discrete(name="Population OD Rate:", guide = guide_legend(reverse=FALSE)) +
  scale_color_discrete(name="Population OD Rate:", guide = guide_legend(reverse=FALSE)) +
  scale_x_continuous(limits = c(10,45)) +
  scale_y_discrete(limits = rev, labels = ltc_labels, expand = c(0.1,0)) +
  my_theme + theme(legend.position = "bottom",
                   legend.text=element_text(size=14),
                   legend.title=element_text(size=14, face="plain"), # match category label font
                   legend.key.spacing.x=unit(0.5, "cm"), # more horizontal space between items
                   legend.background=element_blank(),
                   axis.text=element_text(size=14),
                   axis.title=element_text(size=14),
                   strip.placement = "outside",
                   strip.background = element_blank(),
                   strip.text = element_text(size = 14), # Changes size of all facet labels
                   strip.text.y = element_text(size = 14)) + # Specifically for vertical facet labels
  #ggtitle(moud_type) + # we will add the labels later 
  
  # format is rows ~ columns
  ggh4x::facet_nested("MOUD Acceptance Probability" + jail.moud.acceptance.rate ~
                        "OUD Screening Probability" + jail.oud.screen.probability,
                      labeller = labeller(jail.oud.screen.probability = scrn_labels,   
                                          jail.moud.acceptance.rate = acc_labels))

full_filename <-paste0(output_dir, timestamp, "_moud_ltc_", moud_type, "_jail_size_", jail_size, "_nlx_lvl_", naloxone_level, ".png")

ggsave(filename = full_filename, plot = p, dpi = 400, width=10, height=8)

return(p)
show(p)

}

# create and save the plots
# this is done in one function but we could split it into 2 separate functions
# specify jail size, moud type,and community naloxone level
# plots are saved with these in the filename to identify which is which so titles and footnotes can be adjusted later
# alternatively could add titles and footnotes to the plots here
# each scenario has 40 replicates
create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 6000, moud_type = "BupSL", naloxone_level = 0.5, output_dir = output_dir) 
create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 6000, moud_type = "BupXR", naloxone_level = 0.5, output_dir = output_dir) 
create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 6000, moud_type = "Meth", naloxone_level = 0.5, output_dir = output_dir) 
create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 6000, moud_type = "NtXR", naloxone_level = 0.5, output_dir = output_dir) 

#create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 4000, moud_type = "BupSL", naloxone_level = 0.5, output_dir = output_dir) 
#create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 4000, moud_type = "BupXR", naloxone_level = 0.5, output_dir = output_dir) 
#create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 4000, moud_type = "Meth", naloxone_level = 0.5, output_dir = output_dir) 
#create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 4000, moud_type = "NtXR", naloxone_level = 0.5, output_dir = output_dir) 


#create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 11000, moud_type = "BupSL", naloxone_level = 0.5, output_dir = output_dir) 
#create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 11000, moud_type = "BupXR", naloxone_level = 0.5, output_dir = output_dir) 
#create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 11000, moud_type = "Meth", naloxone_level = 0.5, output_dir = output_dir) 
#create_plots_by_moud_type(data = dt_with_no_moud, jail_size = 11000, moud_type = "NtXR", naloxone_level = 0.5, output_dir = output_dir) 


#########


# An example using patchwork package if we wanted to create separate plots and then put them together here
# We will this in overleaf instead for flexibility

library(patchwork)

multi_plot <- p1 + p2

multi_plot <- multi_plot +
  plot_layout(guides = "collect") +
  plot_annotation(
    title = '',
    tag_levels = 'A',
    caption = "Based on initial jail population of 6000.\nLinkage to care multiplier of 1 = baseline level; 2 = 2x baseline, 0.5 = 1/2 baseline, 0 = no linkage to care.") & 
  theme(legend.position = 'bottom',  # Apply bottom legend position to all
    plot.caption = element_text(hjust = 0), # Center the caption horizontally
    plot.caption.position = "plot" # Align the caption to the entire plot area
  )

show(multi_plot)


#################

###############

# plotting differences

# check 
# this should have all combinations of the grouped variables, 3915 observations
dt %>%
  group_by(jail.moud.type, jail.moud.acceptance.rate, jail.oud.screen.probability, cji.jail.initial.size, naloxone.level.community, 
           moud.linkage.to.care.multiplier, od_base_prob) %>%
  summarise(n = n()) %>%
  mutate(pct=(n/sum(n))*100) 

dt2 <- dt %>%
  select(jail.moud.type, 
         jail.moud.acceptance.rate, 
         jail.oud.screen.probability, 
         cji.jail.initial.size, 
         naloxone.level.community, 
         moud.linkage.to.care.multiplier, 
         od_base_prob, 
         released_persons_od_mortality_rate, 
         random.seed) %>%
  group_by(jail.moud.type, 
           jail.moud.acceptance.rate, 
           jail.oud.screen.probability, 
           cji.jail.initial.size, 
           naloxone.level.community, 
           od_base_prob) %>%
  mutate(group_id = cur_group_id()) # add grouping variable for merging on in next steps so we don't have to merge by so many variables


# select data for reference category for calculating differences
# here we are setting the baseline for comparisons at the LTC multiplier of 1
# if we want to change the reference category do this here
reference_data <- dt2 %>%
  filter(moud.linkage.to.care.multiplier == 1) %>%
  rename(ref.oud.mortality.rate=released_persons_od_mortality_rate) %>%
  ungroup() %>%
  select(c(random.seed, ref.oud.mortality.rate, group_id)) 

# just a check
# there should be 3915 observations and each one has 40 replicates
dt2 %>%
  group_by(group_id, moud.linkage.to.care.multiplier) %>%
  summarise(n = n()) %>%
  mutate(pct=(n/sum(n))*100) 

dt4 <- left_join(dt2, reference_data, by = c("group_id", "random.seed")) %>%
  mutate(diff = released_persons_od_mortality_rate - ref.oud.mortality.rate,
         rr = released_persons_od_mortality_rate / ref.oud.mortality.rate)

# Summarize the difference
summary_diff <- dt4 %>% 
  group_by(#group_id, # do we need group id here? 
           moud.linkage.to.care.multiplier, 
           jail.moud.type, 
           jail.moud.acceptance.rate, 
           jail.oud.screen.probability, 
           cji.jail.initial.size, 
           naloxone.level.community, 
           od_base_prob) %>%
  summarize(
    mean_rate = round(mean(released_persons_od_mortality_rate), 3),
    sd_rate = round(sd(released_persons_od_mortality_rate), 3),
    n_total = n(),
    se_rate = round(sd_rate/sqrt(n_total), 3),
    # Calculate the 95% Confidence Interval (CI)
    # Use qt for the t-distribution quantile (for 95% CI, alpha = 0.05)
    lci_rate = round((mean_rate - qt(1 - (0.05 / 2), n_total - 1) * se_rate), 3),
    uci_rate = round((mean_rate + qt(1 - (0.05 / 2), n_total - 1) * se_rate), 3),
    # add the median and iqr
    median_rate = round(median(released_persons_od_mortality_rate, na.rm = TRUE), 3), 
    q1_rate = round(quantile(released_persons_od_mortality_rate, 0.25, na.rm = TRUE), 3),
    q3_rate = round(quantile(released_persons_od_mortality_rate, 0.75, na.rm = TRUE), 3),
    # same for difference calculations
    mean_diff = round(mean(diff, na.rm = TRUE), 3),
    sd_diff = round(sd(diff, na.rm = TRUE), 3),
    se_diff = round(sd_diff / sqrt(n_total), 3),
    lci_diff =round((mean_diff - qt(1 - (0.05 / 2), n_total - 1) * se_diff), 3),
    uci_diff = round((mean_diff + qt(1 - (0.05 / 2), n_total - 1) * se_diff), 3),
    # use median and iqr for reporting
    median_diff = round(median(diff, na.rm = TRUE), 3), 
    q1_diff = round(quantile(diff, 0.25, na.rm = TRUE), 3),
    q3_diff = round(quantile(diff, 0.75, na.rm = TRUE), 3),
    med_excess_deaths_1yr = round((median_diff/1000)*at_risk_pop_size),
    q1_excess_deaths_1yr = round((q1_diff/1000)*at_risk_pop_size),
    q3_excess_deaths_1yr = round((q3_diff/1000)*at_risk_pop_size),
    med_excess_deaths_5yr = med_excess_deaths_1yr*5,
    q1_excess_deaths_5yr = q1_excess_deaths_1yr*5,
    q3_excess_deaths_5yr =  q3_excess_deaths_1yr*5,
    # same for ratio calcs
    mean_rr = round(mean(rr, na.rm = TRUE), 3),
    median_rr = round(median(rr, na.rm = TRUE), 3), 
    q1_rr = round(quantile(rr, 0.25, na.rm = TRUE), 3),
    q3_rr = round(quantile(rr, 0.75, na.rm = TRUE), 3)
  ) #%>%
  #ungroup()

# recode 0 and 1 values to NA for plotting (may or may not want this)
summary_diff1 <- summary_diff %>%
  mutate(mean_diff = ifelse(mean_diff == 0.000, NA, mean_diff),
         se_diff = ifelse(se_diff == 0.000, NA, se_diff),
         lci_diff = ifelse(lci_diff == 0.000, NA, lci_diff), 
         uci_diff = ifelse(uci_diff == 0.000, NA, uci_diff),
         median_diff = ifelse(median_diff == 0.000, NA, median_diff),
         q1_diff = ifelse(q1_diff == 0.000, NA, q1_diff), 
         q3_diff = ifelse(q3_diff == 0.000, NA, q3_diff),
         median_rr = ifelse(median_rr == 1.000, NA, median_rr),
         q1_rr = ifelse(q1_rr == 1.000, NA, q1_rr), 
         q3_rr = ifelse(q3_rr == 1.000, NA, q3_rr),
         )


##############################
# create forest plots

library(grid)
library(forestploter)

# how to change font?
# how to merge values that are the same across rows

# Define theme
tm <- forest_theme(base_size = 8,
                   # Confidence interval point shape, line type/color/width
                   ci_pch = 15,
                   ci_col = "black",
                   ci_fill = "black",
                   ci_alpha = 0.8,
                   ci_lty = 1,
                   ci_lwd = 1.5,
                   ci_Theight = 0.0, # Set a T end at the end of CI 
                   # Reference line width/type/color
                   refline_gp = gpar(lwd = 1, lty = "dashed", col = "grey20"),
                   # Vertical line width/type/color
                   vertline_lwd = 1,
                   vertline_lty = "dashed",
                   vertline_col = "grey20",
                   # Change summary color for filling and borders
                   summary_fill = "#4575b4",
                   summary_col = "#4575b4",
                   # adjust col width
                   col_width = unit(c(0.5, 0.5, 0.5, 4, 2), "inches"), # not sure if this is working
                   # align text; set hjust and x
                   colhead = list(fg_params = list(hjust = 0.5, x = 0.5)),
                   #rowhead = list(fg_params = list(hjust = 0.5, x = 0.5)),
                   core = list(fg_params = list(hjust = 0.5, x = 0.5)), # Align body text
                   mar = unit(c(2, 2, 2, 2), "mm"), # Adjust margins (bottom, left, top, right) in mm - not working
                  # Footnote font size/face/color
                   footnote_gp = gpar(cex = 0.6, fontface = "italic", col = "black"))



create_dataset_for_forest_plots <- function(data, jail_size, moud_type, naloxone_level, od_base){

  
fp_data <- data %>% filter(jail.moud.type == moud_type &
                           naloxone.level.community == naloxone_level &
                           cji.jail.initial.size == jail_size &
                           od_base_prob == od_base) %>%
  

  mutate(`OD mortality per 1000py \n Median (IQR)` = sprintf("%.2f [%.2f, %.2f]",
                                     median_rate, q1_rate, q3_rate), # you want the mean and 95% CI replace this with the relevant variabels and rename
        rate_diff_ci = sprintf("%.2f [%.2f, %.2f]",
                               mean_diff, lci_diff, uci_diff),
        `5-year excess or averted deaths \n Median (IQR)` = sprintf("%.0f [%.0f, %.0f]",
                                                            med_excess_deaths_5yr, q1_excess_deaths_5yr, q3_excess_deaths_5yr), 
        
        `5-year excess or averted deaths \n Median (IQR)` = ifelse(`5-year excess or averted deaths \n Median (IQR)` == "0 [0, 0]", "Reference", 
                                                                    `5-year excess or averted deaths \n Median (IQR)`),
        # Add a blank column for the plot area (must be named and number of reps at least as long as the number of rows in the table)
        `Rate difference* \n Median (IQR)`  = paste0(rep(" ", 36), collapse = " "),
        `OUD Screening \n probability` = jail.oud.screen.probability,
        `MOUD Acceptance \n probability` = jail.moud.acceptance.rate,
        `Post-release \n MOUD Linkage` = moud.linkage.to.care.multiplier) %>%
    select(c(`OUD Screening \n probability`, 
             `MOUD Acceptance \n probability`,
              `Post-release \n MOUD Linkage`,
             mean_diff, 
             lci_diff, 
             uci_diff,
             median_diff, 
             q1_diff, 
             q3_diff, 
             `OD mortality per 1000py \n Median (IQR)`,
                `Rate difference* \n Median (IQR)`,
             #rate_diff_ci,
             od_base_prob,
             `5-year excess or averted deaths \n Median (IQR)`,
             jail.moud.type))

# add labels for forest plots
fp_data$`MOUD Acceptance \n probability` <- 
  factor(fp_data$`MOUD Acceptance \n probability`,
    levels = c(0.2, 0.5, 0.8),
    labels = c("20%", "50%", "80%"))
   
fp_data$`OUD Screening \n probability` <- 
  factor(fp_data$`OUD Screening \n probability`,
    levels = c(0.5, 0.7, 0.9),
    labels = c("50%", "70%", "90%"))

fp_data$`Post-release \n MOUD Linkage` <- 
  factor(fp_data$`Post-release \n MOUD Linkage`,
    levels = c(0.0, 0.5, 1.0, 2.0),
    labels = c("No linkage", "Reduce linkage by 50%", "Current linkage (Reference)",
               "Double linkage"))

fp_data <- as.data.frame(fp_data) %>%
  arrange(`OUD Screening \n probability`, `MOUD Acceptance \n probability`, `Post-release \n MOUD Linkage`)
return(fp_data) 
}

# function to create and save forest plots using the dataset we just created
create_forest_plots <- function(df){
  
fp <-
  forestploter::forest(df[, c(6:8, 16, 15, 18)], # specify the columns you want to plot other than the mean and lower and upper ci which are used to create the ci plot
         est = df$median_diff,
         lower = df$q1_diff, 
         upper = df$q3_diff, 
         sizes = 0.4,
         ci_column = 4,
         #estimate_col_name = "Rate Difference vs. current linkage (Median, IQR)",
         ref_line = 0, # indicates no effect, set at 0 for differences and 1 for RRs
         arrow_lab = c("Reduced mortality", "Increased mortality"),
         xlim = c(-3.5, 11.25),
         ticks_at = c(-2, 0, 2, 4, 6, 8, 10),
         footnote = "* Rate difference compared to current linkage scenario.",
         #justify = c(0.5, 0.5, 0, 0.5, 0.5),
         theme = tm)


# adjust shading so every other group of scenarios is shaded
fp1 <- edit_plot(fp, 
                 row = c(1:4, 9:12, 17:20, 25:28, 33:36),
                 col = 1:ncol(df), # Apply to all columns in that row
                 which = "background", 
                 gp = gpar(fill = "grey92")) # Use a hex code or color name


fp1 <- edit_plot(fp1, 
                 row = c(5:8, 13:16, 21:24, 29:32),
                 col = 1:ncol(df), # Apply to all columns in that row
                 which = "background", 
                 gp = gpar(fill = "white")) # Use a hex code or color name


fp1 <- edit_plot(fp1, 
                 col = 3,
                 #gp = gpar(),
                 which = "text",
                 hjust = unit(0, "npc"),
                 x = unit(0, "npc"))

fp1 <- edit_plot(fp1, 
                 col = 3:4,
                 #gp = gpar(),
                 part = "header",
                 hjust = unit(0, "npc"),
                 x = unit(0, "npc"))


fp1 <- add_border(fp1, 
                row = 1, part = "header", where = "bottom", gp = gpar(lwd = 1))

fp1 <- add_border(fp1, 
                  row = 1, part = "header", where = "top", gp = gpar(lwd = 1))



moud_type <- unique(df$jail.moud.type)
jail_size <- unique(df$cji.jail.initial.size)
naloxone_level <- unique(df$naloxone.level.community)
od_base <- unique(df$od_base_prob)

#full_filename <-paste0(output_dir, timestamp, "_forest_plot_", df$jail.moud.type, "_jail_size_", df$cji.jail.initial.size, "_nlx_lvl_", df$naloxone.level.community, "_od_base_", df$od_base_prob, ".pdf")
full_filename <-paste0(output_dir, timestamp, "_forest_plot_", moud_type, "_jail_size_", jail_size, "_nlx_lvl_", naloxone_level, "_od_base_", od_base, ".pdf")


ggsave(filename = full_filename, plot = fp1, dpi = 400, width=9.5, height=8.5)

return(fp1)
show(fp1)

}

fp_data_bupsl <- create_dataset_for_forest_plots(data = summary_diff, jail_size = 6000, moud_type = "BupSL", naloxone_level = 0.5, od_base = 0.066)
fp_data_bupxr <- create_dataset_for_forest_plots(data = summary_diff, jail_size = 6000, moud_type = "BupXR", naloxone_level = 0.5, od_base = 0.066)
fp_data_meth <- create_dataset_for_forest_plots(data = summary_diff, jail_size = 6000, moud_type = "Meth", naloxone_level = 0.5, od_base = 0.066)
fp_data_ntxr <- create_dataset_for_forest_plots(data = summary_diff, jail_size = 6000, moud_type = "NtXR", naloxone_level = 0.5, od_base = 0.066)


create_forest_plots(fp_data_bupsl)
create_forest_plots(fp_data_bupxr)
create_forest_plots(fp_data_meth)
create_forest_plots(fp_data_ntxr)




###################
# this is just for testing the functions above

fp_data <- summary_diff %>% filter(jail.moud.type == "BupSL" &
                             naloxone.level.community == 0.5 &
                             cji.jail.initial.size == 6000 &
                             od_base_prob == 0.066) %>%
  mutate(`OD mortality per 1000py \n Median (IQR)` = sprintf("%.2f [%.2f, %.2f]",
                                                             median_rate, q1_rate, q3_rate), # you want the mean and 95% CI replace this with the relevant variabels and rename
         rate_diff_ci = sprintf("%.2f [%.2f, %.2f]",
                                mean_diff, lci_diff, uci_diff),
         `5-year excess or averted deaths \n Median (IQR)` = sprintf("%.0f [%.0f, %.0f]",
                                                                     med_excess_deaths_5yr, q1_excess_deaths_5yr, q3_excess_deaths_5yr), 
         
         `5-year excess or averted deaths \n Median (IQR)` = ifelse(`5-year excess or averted deaths \n Median (IQR)` == "0 [0, 0]", "Reference", 
                                                                    `5-year excess or averted deaths \n Median (IQR)`),
         # Add a blank column for the plot area (must be named and number of reps at least as long as the number of rows in the table)
         `Rate difference* \n Median (IQR)`  = paste0(rep(" ", 36), collapse = " "),
         `OUD Screening \n probability` = jail.oud.screen.probability,
         `MOUD Acceptance \n probability` = jail.moud.acceptance.rate,
         `Post-release \n MOUD Linkage` = moud.linkage.to.care.multiplier) %>%
  select(c(`OUD Screening \n probability`, 
           `MOUD Acceptance \n probability`,
           `Post-release \n MOUD Linkage`,
           mean_diff, 
           lci_diff, 
           uci_diff,
           median_diff, 
           q1_diff, 
           q3_diff, 
           `OD mortality per 1000py \n Median (IQR)`,
           `Rate difference* \n Median (IQR)`,
           #rate_diff_ci,
           od_base_prob,
           `5-year excess or averted deaths \n Median (IQR)`))


fp <-
  forestploter::forest(fp_data[, c(1:3, 11, 10, 12)], # specify the columns you want to plot other than the mean and lower and upper ci which are used to create the ci plot
                       est = fp_data$median_diff,
                       lower = fp_data$q1_diff, 
                       upper = fp_data$q3_diff, 
                       sizes = 0.4,
                       ci_column = 4,
                       #estimate_col_name = "Rate Difference vs. current linkage (Median, IQR)",
                       ref_line = 0, # indicates no effect, set at 0 for differences and 1 for RRs
                       arrow_lab = c("Reduced mortality", "Increased mortality"),
                       xlim = c(-3.5, 11.25),
                       ticks_at = c(-2, 0, 2, 4, 6, 8, 10),
                       footnote = "* Rate difference compared to current linkage scenario.",
                       #justify = c(0.5, 0.5, 0, 0.5, 0.5),
                       theme = tm)
plot(fp)
