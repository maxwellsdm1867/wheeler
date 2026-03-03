function result = wheeler_load_data(filepath, splitters)
%WHEELER_LOAD_DATA Load a .mat file, build epicTreeTools tree, return JSON summary.
%   result = wheeler_load_data(filepath, splitters) loads the file using
%   loadEpicTreeData, creates an epicTreeTools tree, optionally splits it,
%   stores the tree in the base workspace, and returns a JSON summary.
%
%   splitters is a cell array of key path strings, e.g. {'cellInfo.type'}

    try
        if ~isfile(filepath)
            result = jsonencode(struct('status', 'error', ...
                'message', sprintf('File not found: %s', filepath)));
            return;
        end

        % Load the data
        [~, fname, ~] = fileparts(filepath);
        var_name = matlab.lang.makeValidName(fname);

        treeData = loadEpicTreeData(filepath);

        % Create epicTreeTools root node
        tree = epicTreeTools(treeData);

        % Build tree with splitters if provided
        if nargin >= 2 && ~isempty(splitters)
            tree.buildTree(splitters);
        end

        % Store in base workspace for subsequent calls
        assignin('base', var_name, tree);

        % Build summary
        summary = struct();
        summary.var_name = var_name;
        summary.filepath = filepath;

        allEpochs = tree.getAllEpochs(false);
        summary.epoch_count = numel(allEpochs);

        selectedEpochs = tree.getAllEpochs(true);
        summary.selected_count = numel(selectedEpochs);

        % Get children info
        children = struct('split_value', {}, 'epoch_count', {});
        n_children = tree.childrenLength();
        if n_children > 0
            for i = 1:n_children
                child = tree.childAt(i);
                children(i).split_value = string(child.splitValue);
                childEpochs = child.getAllEpochs(false);
                children(i).epoch_count = numel(childEpochs);
            end
        end
        summary.children = children;
        summary.is_leaf = tree.isLeaf;
        summary.status = 'ok';

        result = jsonencode(summary);
    catch ME
        result = jsonencode(struct('status', 'error', 'message', ME.message));
    end
end
