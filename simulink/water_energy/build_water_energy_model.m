function path = build_water_energy_model(outputDirectory)
% Real discrete reservoir-controller-electricity model, constructed using blocks.
name = 'water_energy_model';
if bdIsLoaded(name), close_system(name,0); end
new_system(name);
set_param(name,'SolverType','Fixed-step','Solver','FixedStepDiscrete','FixedStep','1',...
    'StopTime','60','ReturnWorkspaceOutputs','on');
add_block('simulink/Sources/Step',[name '/Demand'],'Time','10','Before','140','After','210','SampleTime','1');
add_block('simulink/Sources/Constant',[name '/Target'],'Value','650');
add_block('simulink/Discrete/Unit Delay',[name '/Volume'],'InitialCondition','600','SampleTime','1');
add_block('simulink/Math Operations/Sum',[name '/Deficit'],'Inputs','+-');
add_block('simulink/Math Operations/Gain',[name '/Refill'],'Gain','0.5');
add_block('simulink/Math Operations/Sum',[name '/RequestedFlow'],'Inputs','++');
add_block('simulink/Discontinuities/Saturation',[name '/PumpCapacity'],'LowerLimit','0','UpperLimit','300');
add_block('simulink/Math Operations/Sum',[name '/NetFlow'],'Inputs','+-');
add_block('simulink/Math Operations/Gain',[name '/MinutesToHours'],'Gain','1/60');
add_block('simulink/Math Operations/Sum',[name '/NextVolume'],'Inputs','++');
add_block('simulink/Discontinuities/Saturation',[name '/StorageBounds'],'LowerLimit','0','UpperLimit','1000');
add_block('simulink/Math Operations/Gain',[name '/PumpPower'],'Gain','0.6');
add_block('simulink/Sinks/To Workspace',[name '/VolumeLog'],'VariableName','volume_log','SaveFormat','Timeseries');
add_block('simulink/Sinks/To Workspace',[name '/PowerLog'],'VariableName','power_log','SaveFormat','Timeseries');
links = {'Target/1','Deficit/1'; 'Volume/1','Deficit/2'; 'Deficit/1','Refill/1';...
 'Refill/1','RequestedFlow/1'; 'Demand/1','RequestedFlow/2'; 'RequestedFlow/1','PumpCapacity/1';...
 'PumpCapacity/1','NetFlow/1'; 'Demand/1','NetFlow/2'; 'NetFlow/1','MinutesToHours/1';...
 'MinutesToHours/1','NextVolume/1'; 'Volume/1','NextVolume/2'; 'NextVolume/1','StorageBounds/1';...
 'StorageBounds/1','Volume/1'; 'PumpCapacity/1','PumpPower/1'; 'Volume/1','VolumeLog/1'; 'PumpPower/1','PowerLog/1'};
for i=1:size(links,1), add_line(name,links{i,1},links{i,2},'autorouting','on'); end
Simulink.BlockDiagram.arrangeSystem(name);
path = fullfile(outputDirectory,[name '.slx']);
save_system(name,path);
end
