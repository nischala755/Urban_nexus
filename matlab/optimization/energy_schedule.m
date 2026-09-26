function result = energy_schedule(base, tariffs, flexible, capacity)
% Enumerate a one-hour task within allowed slots. No extra toolbox required.
base = base(:)'; tariffs = tariffs(:)';
assert(numel(base)==numel(tariffs) && ~isempty(base));
result = struct('feasible',false,'slot',-1,'objective',Inf);
for i = 1:numel(base)
    if base(i)+flexible > capacity, continue; end
    load = zeros(size(base)); load(i) = flexible;
    objective = sum(load.*tariffs)+0.1*max(base+load)+2*(i-1);
    if objective < result.objective
        result = struct('feasible',true,'slot',i-1,'objective',objective,'load_kw',load);
    end
end
end
