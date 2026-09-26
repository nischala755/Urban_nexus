function run_validation(inputPath, outputPath, modelDirectory)
% Entry point invoked by Python. Output is produced only by actual MATLAB/Simulink.
root = fileparts(fileparts(mfilename('fullpath')));
addpath(genpath(fullfile(root,'matlab')));
addpath(genpath(fullfile(root,'simulink')));
input = jsondecode(fileread(inputPath));
assert(input.schema_version == 1);
assert(license('test','Simulink'),'A licensed Simulink installation is required');
if ~isfolder(modelDirectory), mkdir(modelDirectory); end
build_water_energy_model(modelDirectory);
water = sim('water_energy_model');
build_traffic_control_model(modelDirectory);
traffic = sim('traffic_control_model');
schedule = energy_schedule(input.energy_base_kw,input.tariffs,input.flexible_kwh,input.capacity_kw);
output = struct('schema_version',1,'model_version','offline-parity/1.0',...
 'producer','MATLAB+Simulink','runtime_version',version,...
 'input_fingerprint',input.input_fingerprint,...
 'water_volume_m3',water.volume_log.Data(:)',...
 'pump_kw',water.power_log.Data(:)',...
 'traffic_queue',traffic.queue_log.Data(:)',...
 'forecast',energy_forecast(input.history),...
 'schedule_slot_zero_based',schedule.slot,...
 'selected_index_zero_based',intervention_search(input.magnitudes,input.objectives,input.feasible));
fid = fopen(outputPath,'w'); assert(fid ~= -1);
cleanup = onCleanup(@() fclose(fid));
fprintf(fid,'%s',jsonencode(output));
close_system('water_energy_model',0); close_system('traffic_control_model',0);
end
