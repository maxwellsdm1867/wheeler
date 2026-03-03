function result = wheeler_list_data(data_dir)
%WHEELER_LIST_DATA List .mat files in the given directory as JSON.
%   result = wheeler_list_data(data_dir) returns a JSON array of file info
%   with name, bytes, and date fields.

    try
        if ~isfolder(data_dir)
            result = jsonencode(struct('status', 'error', ...
                'message', sprintf('Directory not found: %s', data_dir)));
            return;
        end

        files = dir(fullfile(data_dir, '*.mat'));
        file_list = struct('name', {}, 'bytes', {}, 'date', {});

        for i = 1:numel(files)
            file_list(i).name = files(i).name;
            file_list(i).bytes = files(i).bytes;
            file_list(i).date = files(i).date;
        end

        if isempty(file_list)
            result = jsonencode(struct('files', {{}}, 'count', 0));
        else
            result = jsonencode(struct('files', {file_list}, 'count', numel(file_list)));
        end
    catch ME
        result = jsonencode(struct('status', 'error', 'message', ME.message));
    end
end
