function result = wheeler_get_responses(var_name, node_path, stream_name)
%WHEELER_GET_RESPONSES Extract response data from a tree node as JSON.
%   result = wheeler_get_responses(var_name, node_path, stream_name)
%   navigates to the node, calls epicTreeTools.getSelectedData for the
%   given stream, computes summary stats, and returns JSON.
%   Traces are downsampled to max 500 points.

    try
        tree = evalin('base', var_name);

        % Navigate to node
        node = tree;
        if ~isempty(node_path) && strlength(string(node_path)) > 0
            parts = strsplit(node_path, '/');
            for i = 1:numel(parts)
                child = node.childBySplitValue(parts{i});
                if isempty(child)
                    numVal = str2double(parts{i});
                    if ~isnan(numVal)
                        child = node.childBySplitValue(numVal);
                    end
                end
                if isempty(child)
                    result = jsonencode(struct('status', 'error', ...
                        'message', sprintf('Node not found: %s', parts{i})));
                    return;
                end
                node = child;
            end
        end

        % Get response data using epicTreeTools static method
        [data, ~, sampleRate] = epicTreeTools.getSelectedData(node, stream_name);

        resp = struct();
        resp.stream_name = stream_name;
        resp.n_epochs = size(data, 1);
        resp.n_samples = size(data, 2);
        resp.sample_rate = sampleRate;

        % Compute mean and SEM traces
        mean_trace = mean(data, 1, 'omitnan');
        sem_trace = std(data, 0, 1, 'omitnan') / sqrt(resp.n_epochs);

        % Downsample to max 500 points
        max_pts = 500;
        if resp.n_samples > max_pts
            idx = round(linspace(1, resp.n_samples, max_pts));
            mean_trace = mean_trace(idx);
            sem_trace = sem_trace(idx);
        end

        resp.mean_trace = mean_trace;
        resp.sem_trace = sem_trace;

        % Summary statistics
        baseline_pts = min(50, numel(mean_trace));
        resp.baseline_mean = mean(mean_trace(1:baseline_pts), 'omitnan');
        [~, peak_idx] = max(abs(mean_trace - resp.baseline_mean));
        resp.peak_amplitude = mean_trace(peak_idx) - resp.baseline_mean;
        if sampleRate > 0
            resp.peak_time_ms = (peak_idx / sampleRate) * 1000;
        else
            resp.peak_time_ms = peak_idx;
        end

        resp.status = 'ok';
        result = jsonencode(resp);
    catch ME
        result = jsonencode(struct('status', 'error', 'message', ME.message));
    end
end
