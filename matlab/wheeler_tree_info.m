function result = wheeler_tree_info(var_name, node_path)
%WHEELER_TREE_INFO Get info about a tree node as JSON.
%   result = wheeler_tree_info(var_name, node_path) navigates to the node
%   at the given path (e.g., "OnP/0.5") using childBySplitValue and
%   returns its properties.
%
%   var_name: name of the tree variable in the base workspace
%   node_path: slash-separated path to navigate, or "" for root

    try
        tree = evalin('base', var_name);

        % Navigate to node
        node = tree;
        if nargin >= 2 && ~isempty(node_path) && strlength(string(node_path)) > 0
            parts = strsplit(node_path, '/');
            for i = 1:numel(parts)
                child = node.childBySplitValue(parts{i});
                if isempty(child)
                    % Try numeric match
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

        info = struct();

        allEpochs = node.getAllEpochs(false);
        info.epoch_count = numel(allEpochs);

        selectedEpochs = node.getAllEpochs(true);
        info.selected_count = numel(selectedEpochs);

        if ~isempty(node.splitValue)
            info.split_value = string(node.splitValue);
        else
            info.split_value = 'root';
        end

        % Children
        child_names = {};
        n_children = node.childrenLength();
        info.is_leaf = node.isLeaf;
        if n_children > 0
            for i = 1:n_children
                child = node.childAt(i);
                child_names{end+1} = string(child.splitValue); %#ok<AGROW>
            end
        end
        info.children = child_names;

        % Depth
        info.depth = node.depth();

        info.status = 'ok';
        result = jsonencode(info);
    catch ME
        result = jsonencode(struct('status', 'error', 'message', ME.message));
    end
end
