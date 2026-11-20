# Survival functions for post-release MOUD time on treatment, as implied by the
# model input data/moud_time_on_treatment.csv and the sampling procedure in the
# JCCM model.
#
# Run from the data/ directory:
#   Rscript moud_km_survival.R
#
# Sampling procedure in the model (jail.py Jail.release_person and
# jccm_utils.fast_choice_uniform):
#   1. A histogram bin i is selected with probability f_i. The bins are
#      contiguous; bin i spans (days_{i-1}, days_i] with days_0 = 0.
#   2. The duration d is drawn uniformly within the selected bin.
#   3. d is multiplied by the linkage-to-care multiplier m, with a minimum of
#      1 day: d' = max(m * d, 1).
#   If the listed fractions sum to less than 1, the sampler assigns the
#   remaining probability to the last bin (fallback branch of
#   fast_choice_uniform). This applies to both buprenorphine rows, whose
#   fractions sum to 0.94.
#
# Consequences used below:
#   - S(t) equals 1 - cumsum(f) at each bin edge and is linear between edges.
#   - Under multiplier m > 0, S_m(t) = S(t / m) for t >= 1 and S_m(t) = 1 for t < 1.
#
# Outputs (written to data/):
#   moud_km_survival.png / .pdf          survival functions at m = 1 with the
#                                        published values used as model input
#   moud_km_survival_linkage.png / .pdf  survival functions at m = 0.5, 1, 2
#   moud_km_survival_summary.csv         summary statistics

library(data.table)
library(ggplot2)

# ---- Input ------------------------------------------------------------------

dt <- fread("moud_time_on_treatment.csv")
setorder(dt, moud_name, days)

# Last time point covered by the published source for each MOUD. Bins up to
# this day reproduce the published values; later bins are extrapolated.
#   Methadone:      Macmadu et al. 2021, histogram through 365 days
#   Naltrexone_XR:  Macmadu et al. 2021, histogram through 182 days
#   Buprenorphine:  Lee et al. 2018 (SL buprenorphine), cumulative survival
#                   through 126 days; used for both SL and XR buprenorphine
observed_through <- data.table(
  moud_name = c("Methadone", "Naltrexone_XR",
                "Buprenorphine_Sublingual", "Buprenorphine_XR"),
  obs_day   = c(365, 182, 126, 126),
  source    = c("Macmadu et al. 2021 (histogram)",
                "Macmadu et al. 2021 (histogram)",
                "Lee et al. 2018, SL buprenorphine (cumulative survival)",
                "Lee et al. 2018, SL buprenorphine (cumulative survival)")
)

# ---- Effective bins as sampled by the model ---------------------------------

bins <- dt[, {
  p     <- fraction
  resid <- 1 - sum(p)
  p[.N] <- p[.N] + resid          # fallback: residual mass goes to the last bin
  .(lo = c(0, days[-.N]), hi = days, f_listed = fraction, f = p,
    listed_sum = sum(fraction), residual = resid)
}, by = moud_name]

cat("Listed fraction sums and residual assigned to the last bin:\n")
print(unique(bins[, .(moud_name, listed_sum = round(listed_sum, 3),
                      residual = round(residual, 3))]))

# Survival at bin edges, including t = 0
edges <- bins[, .(t = c(0, hi), S = c(1, 1 - cumsum(f))), by = moud_name]
edges[abs(S) < 1e-9, S := 0]

# Piecewise-linear survival function for one MOUD, linkage multiplier m
surv_fun <- function(moud, m = 1) {
  e <- edges[moud_name == moud]
  base <- approxfun(e$t, e$S, method = "linear", yleft = 1, yright = 0)
  function(t) ifelse(t < 1, 1, base(t / m))
}

# Old sampler (before 2026-06-02) returned the upper edge of the selected bin
surv_upper_edge <- function(moud, t) {
  b <- bins[moud_name == moud]
  vapply(t, function(x) sum(b$f[b$hi > x]), numeric(1))
}

# ---- Summary statistics -----------------------------------------------------

report_times <- c(14, 28, 90, 182, 365, 730, 1825)

integrate_surv <- function(S, upper, step = 0.25) {
  t <- seq(0, upper, by = step)
  s <- S(t)
  sum((s[-1] + s[-length(s)]) / 2) * step
}

median_from <- function(S, upper) {
  uniroot(function(t) S(t) - 0.5, c(1, upper), tol = 1e-6)$root
}

summary_dt <- rbindlist(lapply(unique(bins$moud_name), function(moud) {
  b      <- bins[moud_name == moud]
  t_max  <- max(b$hi)
  rows <- lapply(c(0.5, 1, 2), function(m) {
    S <- surv_fun(moud, m)
    data.table(
      moud_name   = moud,
      multiplier  = m,
      median_days = median_from(S, m * t_max),
      mean_days   = integrate_surv(S, m * t_max),
      rmst_5y     = integrate_surv(S, 1825)
    )
  })
  out <- rbindlist(rows)
  S1  <- surv_fun(moud, 1)
  for (tt in report_times) out[, paste0("S_", tt) := S1(tt)]
  # Upper-edge sampler, for comparison with the pre-2026-06-02 model version
  out[, mean_upper_edge   := sum(b$f * b$hi)]
  out[, median_upper_edge := b$hi[which(cumsum(b$f) >= 0.5)[1]]]
  out[multiplier != 1, c(paste0("S_", report_times),
                         "mean_upper_edge", "median_upper_edge") := NA]
  out
}))

summary_print <- copy(summary_dt)
num_cols <- names(summary_print)[vapply(summary_print, is.numeric, logical(1))]
summary_print[, (num_cols) := lapply(.SD, round, 3), .SDcols = num_cols]
cat("\nSummary statistics (S_t columns at m = 1):\n")
print(summary_print)
fwrite(summary_print, "moud_km_survival_summary.csv")

# ---- Plot data --------------------------------------------------------------

# SL and XR buprenorphine use identical input; plot them as one series.
same_bup <- isTRUE(all.equal(
  dt[moud_name == "Buprenorphine_Sublingual", .(days, fraction)],
  dt[moud_name == "Buprenorphine_XR", .(days, fraction)],
  check.attributes = FALSE))
stopifnot(same_bup)

series <- data.table(
  moud_name = c("Methadone", "Buprenorphine_Sublingual", "Naltrexone_XR"),
  label     = c("Methadone", "SL and XR buprenorphine", "XR naltrexone")
)
series[, label := factor(label, levels = label)]
series <- merge(series, observed_through, by = "moud_name", sort = FALSE)

# Categorical slots 1-3 of the reference palette (validated all-pairs, light)
series_colors <- setNames(c("#2a78d6", "#eb6834", "#1baf7a"), levels(series$label))

panels <- data.table(
  panel = factor(c("First year after release", "Full range"),
                 levels = c("First year after release", "Full range")),
  t_end = c(365, 2920)
)

curve_dt <- rbindlist(lapply(seq_len(nrow(series)), function(i) {
  s  <- series[i]
  S  <- surv_fun(s$moud_name, 1)
  t  <- sort(unique(c(seq(0, 2920, by = 1), edges[moud_name == s$moud_name, t])))
  d  <- data.table(label = s$label, t = t, S = S(t))
  # Observed segment and extrapolated segment share the boundary point
  rbind(d[t <= s$obs_day][, part := "Published data"],
        d[t >= s$obs_day][, part := "Extrapolated"])
}))
curve_dt[, part := factor(part, levels = c("Published data", "Extrapolated"))]
curve_dt <- rbindlist(lapply(seq_len(nrow(panels)), function(j) {
  curve_dt[t <= panels$t_end[j]][, panel := panels$panel[j]]
}))

points_dt <- rbindlist(lapply(seq_len(nrow(series)), function(i) {
  s <- series[i]
  edges[moud_name == s$moud_name & t > 0 & t <= s$obs_day,
        .(label = s$label, t, S)]
}))
points_dt <- rbindlist(lapply(seq_len(nrow(panels)), function(j) {
  points_dt[t <= panels$t_end[j]][, panel := panels$panel[j]]
}))

# ---- Shared theme -----------------------------------------------------------

ink_primary   <- "#0b0b0b"
ink_secondary <- "#52514e"
grid_color    <- "#e4e3df"

base_family <- if ("Arial" %in% systemfonts::system_fonts()$family) "Arial" else ""

theme_jccm <- theme_minimal(base_size = 9, base_family = base_family) +
  theme(
    text              = element_text(color = ink_primary),
    axis.text         = element_text(color = ink_secondary),
    axis.title        = element_text(color = ink_secondary),
    strip.text        = element_text(color = ink_primary, face = "bold", hjust = 0),
    panel.grid.major  = element_line(color = grid_color, linewidth = 0.3),
    panel.grid.minor  = element_blank(),
    legend.position   = "bottom",
    legend.box        = "vertical",
    legend.spacing.y  = unit(0, "pt"),
    legend.margin     = margin(0, 0, 0, 0),
    legend.text       = element_text(color = ink_secondary),
    legend.title      = element_text(color = ink_secondary),
    panel.spacing     = unit(14, "pt"),
    plot.margin       = margin(4, 8, 4, 4)
  )

save_both <- function(p, stem, width, height) {
  ggsave(paste0(stem, ".png"), p, width = width, height = height, dpi = 300, bg = "white")
  ggsave(paste0(stem, ".pdf"), p, width = width, height = height,
         device = cairo_pdf, bg = "white")
  cat(sprintf("Saved data/%s.png and data/%s.pdf\n", stem, stem))
}

# ---- Figure 1: survival functions at m = 1 ----------------------------------

x_breaks <- function(lims) {
  if (max(lims) <= 400) c(0, 90, 182, 273, 365) else c(0, 730, 1460, 2190, 2920)
}

p1 <- ggplot() +
  geom_line(data = curve_dt,
            aes(x = t, y = S, color = label, linetype = part),
            linewidth = 0.6, lineend = "round") +
  geom_point(data = points_dt,
             aes(x = t, y = S, color = label),
             size = 1.6, stroke = 0.4, shape = 21, fill = "white") +
  facet_wrap(~ panel, scales = "free_x") +
  scale_color_manual(values = series_colors, name = NULL) +
  scale_linetype_manual(values = c("Published data" = "solid", "Extrapolated" = "22"),
                        name = NULL) +
  scale_x_continuous(breaks = x_breaks, expand = expansion(mult = c(0.01, 0.03))) +
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.2),
                     labels = scales::percent_format(accuracy = 1),
                     expand = expansion(mult = c(0, 0.02))) +
  labs(x = "Days since release", y = "Remaining on MOUD") +
  guides(color = guide_legend(order = 1, override.aes = list(shape = NA, linewidth = 0.8)),
         linetype = guide_legend(order = 2, override.aes = list(color = ink_secondary))) +
  theme_jccm

save_both(p1, "moud_km_survival", width = 6.3, height = 3.4)

# ---- Figure 2: survival functions under linkage multipliers -----------------

linkage_dt <- rbindlist(lapply(seq_len(nrow(series)), function(i) {
  s <- series[i]
  rbindlist(lapply(c(0.5, 1, 2), function(m) {
    t <- seq(0, 1825, by = 1)
    data.table(label = s$label, m = m, t = t, S = surv_fun(s$moud_name, m)(t))
  }))
}))
linkage_dt[, m := factor(m, levels = c(0.5, 1, 2), labels = c("0.5", "1", "2"))]

# Ordinal blue ramp (steps 250, 450, 650 of the reference sequential hue)
linkage_colors <- c("0.5" = "#86b6ef", "1" = "#2a78d6", "2" = "#104281")

p2 <- ggplot(linkage_dt, aes(x = t, y = S, color = m)) +
  geom_line(linewidth = 0.6, lineend = "round") +
  facet_wrap(~ label) +
  scale_color_manual(values = linkage_colors, name = "Linkage multiplier m") +
  scale_x_continuous(breaks = c(0, 365, 730, 1095, 1460, 1825),
                     expand = expansion(mult = c(0.01, 0.03))) +
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.2),
                     labels = scales::percent_format(accuracy = 1),
                     expand = expansion(mult = c(0, 0.02))) +
  labs(x = "Days since release", y = "Remaining on MOUD") +
  guides(color = guide_legend(override.aes = list(linewidth = 0.8))) +
  theme_jccm

save_both(p2, "moud_km_survival_linkage", width = 6.3, height = 2.8)
