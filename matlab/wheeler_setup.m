function result = wheeler_setup(epicTreeGUI_root)
%WHEELER_SETUP Add epicTreeGUI and wheeler/matlab to MATLAB path.
%   result = wheeler_setup(epicTreeGUI_root) adds epicTreeGUI source
%   directories and the wheeler matlab directory to the path.
%   Returns JSON string with status and paths_added count.
%
%   Note: This adds paths directly rather than running epicTreeGUI's
%   install.m, which has an interactive prompt incompatible with batch mode.

    try
        % Validate input
        if ~isfolder(epicTreeGUI_root)
            result = jsonencode(struct('status', 'error', ...
                'message', sprintf('Directory not found: %s', epicTreeGUI_root)));
            return;
        end

        paths_added = 0;

        % Add epicTreeGUI paths (mirrors install.m without the interactive prompt)
        pathsToAdd = {
            epicTreeGUI_root, ...
            fullfile(epicTreeGUI_root, 'src'), ...
            fullfile(epicTreeGUI_root, 'src', 'tree'), ...
            fullfile(epicTreeGUI_root, 'src', 'gui'), ...
            fullfile(epicTreeGUI_root, 'src', 'splitters'), ...
            fullfile(epicTreeGUI_root, 'src', 'utilities') ...
        };

        configDir = fullfile(epicTreeGUI_root, 'src', 'config');
        if isfolder(configDir)
            pathsToAdd{end+1} = configDir;
        end

        for i = 1:numel(pathsToAdd)
            if isfolder(pathsToAdd{i})
                addpath(pathsToAdd{i});
                paths_added = paths_added + 1;
            end
        end

        % Add wheeler/matlab to path
        wheeler_matlab = fileparts(mfilename('fullpath'));
        if ~isempty(wheeler_matlab)
            addpath(wheeler_matlab);
            paths_added = paths_added + 1;
        end

        result = jsonencode(struct('status', 'ok', 'paths_added', paths_added));
    catch ME
        result = jsonencode(struct('status', 'error', 'message', ME.message));
    end
end
