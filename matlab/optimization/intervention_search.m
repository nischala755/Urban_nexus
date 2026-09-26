function index = intervention_search(magnitudes, objectives, feasible)
% Hard gate, then lexicographic resource magnitude before weighted objective.
indices = find(feasible(:));
if isempty(indices), index = -1; return; end
table = [magnitudes(indices(:)), objectives(indices(:)), indices(:)];
table = sortrows(table,[1 2 3]);
index = table(1,3)-1; % Stable zero-based JSON interface.
end
