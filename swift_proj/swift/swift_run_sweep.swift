import io;
import sys;
import files;
import launch;
import python;
import stats;
import string;
import unix;
import R;

string emews_root = getenv("EMEWS_PROJECT_ROOT");
string turbine_output = getenv("TURBINE_OUTPUT");

string config_file = argv("config_file");
string param_file = argv("f"); // e.g. -f="model_params.txt";

string rout_file = argv("rout_file");

// Code for running the JCCM Model
string jccm_model_code =
"""
import turbine_helpers  # From latest swift-t built with python support
import jccm_model as jccm
import os

props = '%s'  # arg 1 is the model.props
params = '%s' # arg 2 is the json params

mpi4py_comm = turbine_helpers.get_task_comm()

try:
    jccm.run(mpi4py_comm, props, params)
except Exception as err:
   print(f"Unexpected {err=}, {type(err)=}")

""";

string r_response_code_test = """
print(.libPaths())

library(data.table)

string.res <- "R done."
""";

// R run response variable calculation code
// TODO pass the use_parquet bool value from the props (or deprecate use)
string r_response_code = """

library(data.table)

# Source the analysis R code functions
source("%s") # 

instance_dir <-"%s"
use_parquet <- F
warm_up_ticks <- 90

# The model return value of "Done." or "None.", depending on termination status.
model_out <- "%s"

string.res <- "R none."

if (model_out == "'Done.'") {

    # return a single row data.table with the run props and response variables
    run_response <- tabulate_run(instance_dir, use_parquet=use_parquet, warm_up=warm_up_ticks)

    fwrite(run_response, paste0(instance_dir, "/runs_response.csv"))

    # No need to actually return any data since it's just saved to file
    string.res <- "R done."
} else {
    write(0, paste0(instance_dir, "/run_failed.txt"))
}

string.res

""";

(string v) run_model(){
    string param_lines[] = file_lines(input(param_file));
    string z[];
    
    foreach json_model_params, i in param_lines{
        printf(json_model_params);
        
        string instance = "%s/runs/run_%d/" % (turbine_output, i);
        
        mkdir(instance) => {

            // Additional params to insert into the model json params string
            string add_ons = "\"output.directory\" : \"%s\", "  % (instance);
                
            // Insert the additional JSON name:value pairs into the line sent to the model
            string prefix = substring(json_model_params, 0, 1);
            string suffix = substring(json_model_params, 1, strlen(json_model_params) - 1);
            string model_params = "%s %s %s" % (prefix, add_ons, suffix);
            
            // TODO get par from command line
            
            // Use swift-python  (return is string)
            string model_code = jccm_model_code % (config_file, model_params);

            // TODO use the single line for a plain sweep, or...
			// z[i] = @par=1 python_parallel_persist(model_code, "repr(jccm.get())");
            
            // use this block for running the R script post run for analysis
			model_out = @par=1 python_parallel_persist(model_code, "repr(jccm.get())") =>
                
                printf(model_out) => 

                code = r_response_code % (rout_file, instance, model_out) =>
                
					// Run the R code to compute and return the objetive value tuples 
					z[i] = R(code, "string.res");


        }
    }
    
    // Join return strings
    v = join(z);
}

main {
    //printenv();
    v = run_model();
    printf("v = %s", v);
}
