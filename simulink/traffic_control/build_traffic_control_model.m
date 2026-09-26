function path = build_traffic_control_model(outputDirectory)
% Fluid queue driven by arrivals and green-time service capacity.
name = 'traffic_control_model';
if bdIsLoaded(name), close_system(name,0); end
new_system(name);
set_param(name,'SolverType','Fixed-step','Solver','FixedStepDiscrete','FixedStep','1',...
 'StopTime','60','ReturnWorkspaceOutputs','on');
add_block('simulink/Sources/Step',[name '/Arrivals'],'Time','10','Before','20','After','40','SampleTime','1');
add_block('simulink/Sources/Constant',[name '/GreenService'],'Value','30');
add_block('simulink/Discrete/Unit Delay',[name '/Queue'],'InitialCondition','10','SampleTime','1');
add_block('simulink/Math Operations/Sum',[name '/Balance'],'Inputs','++-');
add_block('simulink/Discontinuities/Saturation',[name '/NonnegativeQueue'],'LowerLimit','0','UpperLimit','inf');
add_block('simulink/Sinks/To Workspace',[name '/QueueLog'],'VariableName','queue_log','SaveFormat','Timeseries');
add_line(name,'Queue/1','Balance/1'); add_line(name,'Arrivals/1','Balance/2');
add_line(name,'GreenService/1','Balance/3'); add_line(name,'Balance/1','NonnegativeQueue/1');
add_line(name,'NonnegativeQueue/1','Queue/1'); add_line(name,'Queue/1','QueueLog/1');
Simulink.BlockDiagram.arrangeSystem(name);
path = fullfile(outputDirectory,[name '.slx']); save_system(name,path);
end
