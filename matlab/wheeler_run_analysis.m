function result = wheeler_run_analysis(var_name, node_path, analysis_type, params_json)
%WHEELER_RUN_ANALYSIS Run an epicAnalysis on a tree node, return JSON results.
%   result = wheeler_run_analysis(var_name, node_path, analysis_type, params_json)
%
%   analysis_type: string name of analysis function (e.g., 'RFAnalysis')
%   params_json: optional JSON string of analysis parameters

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

        % Parse optional params
        if nargin >= 4 && ~isempty(params_json)
            params = jsondecode(params_json);
        else
            params = struct();
        end

        % Run the analysis - try epicAnalysis namespace first
        try
            fn = str2func(['epicAnalysis.' analysis_type]);
            analysis = fn(node, params);
        catch
            % Fallback: try as standalone function
            fn = str2func(analysis_type);
            analysis = fn(node, params);
        end

        % Extract results into a struct
        out = struct();
        out.analysis_type = analysis_type;

        % Use dynamic property inspection
        if isstruct(analysis)
            out.results = analysis;
        elseif isobject(analysis)
            props = properties(analysis);
            for i = 1:numel(props)
                try
                    out.(props{i}) = analysis.(props{i});
                catch
                    % Skip unreadable properties
                end
            end
        end

        out.status = 'ok';
        result = jsonencode(out);
    catch ME
        result = jsonencode(struct('status', 'error', 'message', ME.message));
    end
end
