"""Tests for wheeler.depscanner module."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from wheeler.depscanner import DependencyMap, scan_script


@pytest.fixture
def tmp_script(tmp_path: Path):
    """Helper: write a .py file and return its path."""
    def _write(content: str, name: str = "script.py") -> Path:
        p = tmp_path / name
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return p
    return _write


class TestScanImports:
    def test_simple_import(self, tmp_script):
        p = tmp_script("import numpy\n")
        result = scan_script(p)
        assert "numpy" in result.imports

    def test_import_alias(self, tmp_script):
        p = tmp_script("import numpy as np\n")
        result = scan_script(p)
        assert "numpy" in result.imports

    def test_from_import(self, tmp_script):
        p = tmp_script("from scipy.io import loadmat\n")
        result = scan_script(p)
        assert "scipy.io" in result.imports

    def test_multiple_imports(self, tmp_script):
        p = tmp_script("""\
            import numpy as np
            import pandas as pd
            from pathlib import Path
            from scipy.io import loadmat
        """)
        result = scan_script(p)
        assert set(result.imports) == {"numpy", "pandas", "pathlib", "scipy.io"}

    def test_deduplicates_imports(self, tmp_script):
        p = tmp_script("""\
            import numpy
            import numpy
        """)
        result = scan_script(p)
        assert result.imports.count("numpy") == 1


class TestScanDataFiles:
    def test_csv_string_literal(self, tmp_script):
        p = tmp_script("""\
            path = "data/neurons.csv"
        """)
        result = scan_script(p)
        assert len(result.data_files) == 1
        assert result.data_files[0]["path"] == "data/neurons.csv"

    def test_mat_file(self, tmp_script):
        p = tmp_script("""\
            f = "experiment_01.mat"
        """)
        result = scan_script(p)
        assert any(d["path"] == "experiment_01.mat" for d in result.data_files)

    def test_npy_file(self, tmp_script):
        p = tmp_script("""\
            arr = "results/output.npy"
        """)
        result = scan_script(p)
        assert any(d["path"] == "results/output.npy" for d in result.data_files)

    def test_pd_read_csv(self, tmp_script):
        p = tmp_script("""\
            import pandas as pd
            df = pd.read_csv("data/spikes.csv")
        """)
        result = scan_script(p)
        assert len(result.data_files) == 1
        assert result.data_files[0]["path"] == "data/spikes.csv"
        assert result.data_files[0]["context"] == "pd.read_csv"

    def test_np_load(self, tmp_script):
        p = tmp_script("""\
            import numpy as np
            arr = np.load("weights.npy")
        """)
        result = scan_script(p)
        assert any(d["path"] == "weights.npy" for d in result.data_files)
        assert any(d["context"] == "np.load" for d in result.data_files)

    def test_scipy_loadmat(self, tmp_script):
        p = tmp_script("""\
            import scipy.io
            data = scipy.io.loadmat("cell_data.mat")
        """)
        result = scan_script(p)
        assert any(d["path"] == "cell_data.mat" for d in result.data_files)

    def test_non_data_string_ignored(self, tmp_script):
        p = tmp_script("""\
            msg = "hello world"
            label = "neuron type A"
        """)
        result = scan_script(p)
        assert result.data_files == []

    def test_deduplicates_data_files(self, tmp_script):
        p = tmp_script("""\
            import pandas as pd
            f = "data.csv"
            df = pd.read_csv("data.csv")
        """)
        result = scan_script(p)
        # Should appear once, with the more informative context
        assert len(result.data_files) == 1
        assert result.data_files[0]["path"] == "data.csv"

    def test_h5py_file(self, tmp_script):
        p = tmp_script("""\
            import h5py
            f = h5py.File("recording.h5")
        """)
        result = scan_script(p)
        assert any(d["path"] == "recording.h5" for d in result.data_files)


class TestScanFunctionCalls:
    def test_simple_call(self, tmp_script):
        p = tmp_script("""\
            print("hello")
        """)
        result = scan_script(p)
        assert "print" in result.function_calls

    def test_method_call(self, tmp_script):
        p = tmp_script("""\
            import numpy as np
            x = np.array([1, 2, 3])
        """)
        result = scan_script(p)
        assert "np.array" in result.function_calls

    def test_deduplicates_calls(self, tmp_script):
        p = tmp_script("""\
            print("a")
            print("b")
        """)
        result = scan_script(p)
        assert result.function_calls.count("print") == 1

    def test_nested_attribute_call(self, tmp_script):
        p = tmp_script("""\
            import scipy.io
            data = scipy.io.loadmat("test.mat")
        """)
        result = scan_script(p)
        assert "scipy.io.loadmat" in result.function_calls


class TestScanIntegration:
    def test_realistic_script(self, tmp_script):
        p = tmp_script("""\
            \"\"\"Analyze retinal ganglion cell responses.\"\"\"
            import numpy as np
            import pandas as pd
            from scipy.io import loadmat
            from pathlib import Path

            data = loadmat("recordings/parasol_data.mat")
            spikes = pd.read_csv("processed/spike_times.csv")

            rates = np.mean(data["responses"], axis=0)
            result = np.save("output/firing_rates.npy", rates)
        """)
        result = scan_script(p)

        # Imports
        assert "numpy" in result.imports
        assert "pandas" in result.imports
        assert "scipy.io" in result.imports
        assert "pathlib" in result.imports

        # Data files
        paths = {d["path"] for d in result.data_files}
        assert "recordings/parasol_data.mat" in paths
        assert "processed/spike_times.csv" in paths
        assert "output/firing_rates.npy" in paths

        # Function calls
        assert "pd.read_csv" in result.function_calls
        assert "np.mean" in result.function_calls
        assert "np.save" in result.function_calls

    def test_to_dict(self, tmp_script):
        p = tmp_script("import numpy\n")
        result = scan_script(p)
        d = result.to_dict()
        assert "script_path" in d
        assert "imports" in d
        assert "data_files" in d
        assert "function_calls" in d
        assert isinstance(d["imports"], list)


class TestScanErrors:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            scan_script("/nonexistent/path/script.py")

    def test_syntax_error(self, tmp_script):
        p = tmp_script("def broken(\n")
        with pytest.raises(SyntaxError):
            scan_script(p)

    def test_empty_file(self, tmp_script):
        p = tmp_script("")
        result = scan_script(p)
        assert result.imports == []
        assert result.data_files == []
        assert result.function_calls == []
