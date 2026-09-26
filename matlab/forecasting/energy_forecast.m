function prediction = energy_forecast(values)
% Identical persistence-versus-linear-trend rolling-origin selection as Python.
values = values(:)';
assert(numel(values) >= 3 && all(isfinite(values)) && all(values >= 0));
errors = zeros(2, numel(values)-2);
for i = 3:numel(values)
    errors(1,i-2) = abs(values(i)-values(i-1));
    errors(2,i-2) = abs(values(i)-trend(values(1:i-1)));
end
if mean(errors(1,:)) <= mean(errors(2,:))
    prediction = values(end);
else
    prediction = trend(values);
end
end

function result = trend(values)
v = values(max(1,end-5):end);
x = 0:numel(v)-1;
slope = sum((x-mean(x)).*(v-mean(v)))/sum((x-mean(x)).^2);
result = max(0,mean(v)+slope*(numel(v)-mean(x)));
end
