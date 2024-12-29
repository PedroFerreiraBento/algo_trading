import os
import pandas as pd
import pytest
from algo_trading.data_storage import DataStorage

@pytest.fixture
def sample_dataframe():
    """Fixture to provide a sample DataFrame."""
    data = {
        "col1": [1, 2, 3],
        "col2": ["A", "B", "C"],
        "col3": [3.14, 2.71, 1.62],
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_dict():
    """Fixture to provide a sample dictionary."""
    return {
        "col1": [1, 2, 3],
        "col2": ["A", "B", "C"],
        "col3": [3.14, 2.71, 1.62],
    }

@pytest.fixture
def cleanup_files():
    """Fixture to clean up test files after each test."""
    yield
    for file in os.listdir():
        if file.startswith("test_data"):
            DataStorage.remove_file(file)

def generic_test_write_read_append(format_name, sample_data, cleanup_files, **kwargs):
    """
    Generic test to validate write, read, and append functionalities for all formats.

    Args:
        format_name (str): The format being tested (e.g., 'csv', 'parquet').
        sample_data (Union[dict, pd.DataFrame]): The sample data to test with.
        cleanup_files (Fixture): Ensures cleanup of test files.
        **kwargs: Additional arguments for format-specific parameters (e.g., key, table_name).
    """
    # Prepare filenames or keys based on format
    if format_name == "sqlite":
        filename = "test_data.db"
        table_name = kwargs.get("table_name", "test_table")
    elif format_name == "hdf5":
        filename = "test_data.h5"
        key = kwargs.get("key", "test_key")
    else:
        filename = f"test_data.{format_name}"

    # Write operation
    write_method = getattr(DataStorage, f"write_{format_name}")
    write_method(sample_data, filename, **kwargs)
    assert os.path.exists(filename), f"File {filename} was not created."
    
    # Read operation
    read_method = getattr(DataStorage, f"read_{format_name}")
    read_data = read_method(filename, **kwargs)
    expected_data = pd.DataFrame(sample_data) if isinstance(sample_data, dict) else sample_data
    
    
    pd.testing.assert_frame_equal(read_data, expected_data, f"Read data does not match expected data for {format_name}.")

    # Append operation
    DataStorage.append_to_file(expected_data, filename, format_name, **kwargs)
    appended_data = read_method(filename, **kwargs)
    double_data = pd.concat([expected_data, expected_data], ignore_index=True)
    
    pd.testing.assert_frame_equal(appended_data, double_data, f"Appended data does not match expected result for {format_name}.")
    
def test_csv(sample_dataframe, sample_dict, cleanup_files):
    generic_test_write_read_append("csv", sample_dataframe, cleanup_files)
    generic_test_write_read_append("csv", sample_dict, cleanup_files)
    

def test_parquet(sample_dataframe, sample_dict, cleanup_files):
    generic_test_write_read_append("parquet", sample_dataframe, cleanup_files)
    generic_test_write_read_append("parquet", sample_dict, cleanup_files)

def test_json(sample_dataframe, sample_dict, cleanup_files):
    generic_test_write_read_append("json", sample_dataframe, cleanup_files)
    generic_test_write_read_append("json", sample_dict, cleanup_files)

def test_feather(sample_dataframe, sample_dict, cleanup_files):
    generic_test_write_read_append("feather", sample_dataframe, cleanup_files)
    generic_test_write_read_append("feather", sample_dict, cleanup_files)

def test_sqlite(sample_dataframe, sample_dict, cleanup_files):
    generic_test_write_read_append("sqlite", sample_dataframe, cleanup_files, table_name="test_table")
    generic_test_write_read_append("sqlite", sample_dict, cleanup_files, table_name="test_table")

def test_hdf5(sample_dataframe, sample_dict, cleanup_files):
    generic_test_write_read_append("hdf5", sample_dataframe, cleanup_files, key="test_key")
    generic_test_write_read_append("hdf5", sample_dict, cleanup_files, key="test_key")

def test_pickle(sample_dataframe, sample_dict, cleanup_files):
    generic_test_write_read_append("pickle", sample_dataframe, cleanup_files)
    generic_test_write_read_append("pickle", sample_dict, cleanup_files)