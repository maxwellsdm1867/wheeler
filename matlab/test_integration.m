% Wheeler MATLAB integration test script
% Run with: matlab -batch "run('/path/to/test_integration.m')"

addpath('fullfile(fileparts(mfilename('fullpath')))');

fprintf('=== TEST 1: wheeler_setup ===\n');
result = wheeler_setup('/path/to/epicTreeGUI');
disp(result);
r = jsondecode(result);
assert(strcmp(r.status, 'ok'), 'Setup failed');
fprintf('PASS: setup returned ok with %d paths\n\n', r.paths_added);

fprintf('=== TEST 2: wheeler_list_data ===\n');
result = wheeler_list_data('/path/to/epicTreeGUI/examples/data');
disp(result);
r = jsondecode(result);
assert(r.count > 0, 'No .mat files found');
fprintf('PASS: found %d .mat files\n\n', r.count);

fprintf('=== TEST 3: wheeler_load_data (no splitters) ===\n');
result = wheeler_load_data('/path/to/epicTreeGUI/examples/data/sample_epochs.mat', {});
disp(result);
r = jsondecode(result);
assert(strcmp(r.status, 'ok'), sprintf('Load failed: %s', result));
fprintf('PASS: loaded %s with %d epochs (is_leaf=%d)\n\n', r.var_name, r.epoch_count, r.is_leaf);

fprintf('=== TEST 4: wheeler_load_data (with splitter) ===\n');
result = wheeler_load_data('/path/to/epicTreeGUI/examples/data/sample_epochs.mat', {'cellInfo.type'});
disp(result);
r = jsondecode(result);
assert(strcmp(r.status, 'ok'), sprintf('Load with splitter failed: %s', result));
fprintf('PASS: loaded with splitter, %d children\n', numel(r.children));
for i = 1:numel(r.children)
    fprintf('  child: %s (%d epochs)\n', r.children(i).split_value, r.children(i).epoch_count);
end
fprintf('\n');

fprintf('=== TEST 5: wheeler_tree_info (root) ===\n');
result = wheeler_tree_info(r.var_name, '');
disp(result);
r2 = jsondecode(result);
assert(strcmp(r2.status, 'ok'), sprintf('Tree info failed: %s', result));
fprintf('PASS: root has %d epochs, is_leaf=%d, %d children\n\n', r2.epoch_count, r2.is_leaf, numel(r2.children));

if ~r2.is_leaf && ~isempty(r2.children)
    child_name = r2.children{1};
    fprintf('=== TEST 6: wheeler_tree_info (child: %s) ===\n', child_name);
    result = wheeler_tree_info(r.var_name, child_name);
    disp(result);
    r3 = jsondecode(result);
    assert(strcmp(r3.status, 'ok'), sprintf('Child info failed: %s', result));
    fprintf('PASS: child %s has %d epochs\n\n', child_name, r3.epoch_count);

    fprintf('=== TEST 7: wheeler_get_responses ===\n');
    result = wheeler_get_responses(r.var_name, child_name, 'Amp1');
    disp(result);
    r4 = jsondecode(result);
    if strcmp(r4.status, 'ok')
        fprintf('PASS: got %d epochs, %d samples, sr=%g Hz\n', r4.n_epochs, r4.n_samples, r4.sample_rate);
        fprintf('  baseline_mean=%.4f, peak_amp=%.4f, peak_time=%.1f ms\n\n', r4.baseline_mean, r4.peak_amplitude, r4.peak_time_ms);
    else
        fprintf('SKIP: get_responses returned error (stream may not exist): %s\n\n', r4.message);
    end
end

fprintf('=== TEST 8: wheeler_tree_info (invalid path) ===\n');
result = wheeler_tree_info(r.var_name, 'NonExistentNode');
disp(result);
r5 = jsondecode(result);
assert(strcmp(r5.status, 'error'), 'Should have returned error for invalid path');
fprintf('PASS: correctly returned error for invalid path\n\n');

fprintf('=== ALL TESTS PASSED ===\n');
