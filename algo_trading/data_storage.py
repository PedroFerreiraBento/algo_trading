import pandas as pd
import sqlite3
import logging
from typing import Callable, Optional, Union
import pickle
import os
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.feather as feather
import pyarrow.ipc as ipc

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class DataStorage:
    """
    A utility class for saving, loading, and managing data in various formats including:
        CSV, Parquet, JSON, Feather, SQLite, HDF5, and Pickle.
    """

    # Write Methods -------------------------------------------------------------------------------
    @staticmethod
    def _write_file(filename: str, func: Callable, **kwargs) -> None:
        """
        Generic function to handle file writing.

        Args:
            filename (str): The name of the file to save.
            func (Callable): The function to use for saving.
            **kwargs: Additional arguments for the saving function.
        """
        try:
            func(filename, **kwargs)
            logging.info(f"File saved to {filename}")
        except Exception as e:
            logging.error(f"Failed to save file: {e}")

    @staticmethod
    def write_csv(data: Union[pd.DataFrame, dict], filename: str, **kwargs) -> None:
        """
        Save data as a CSV file. Accepts either a DataFrame or a dictionary.

        Args:
            data (Union[pd.DataFrame, dict]): The data to save.
            filename (str): The name of the file to save.
            **kwargs: Additional arguments for pandas to_csv.
        """
        if isinstance(data, dict):
            data = pd.DataFrame(data)

        try:
            data.to_csv(filename, index=False, **kwargs)
            logging.info(f"File saved to {filename}")
        except Exception as e:
            logging.error(f"Failed to save CSV file: {e}")

    @staticmethod
    def write_parquet(data: Union[pd.DataFrame, dict], filename: str) -> None:
        """
        Create a new Parquet file with the given data.

        Args:
            data (Union[pd.DataFrame, dict]): Data to write.
            filename (str): File name.
        """
        try:
            if isinstance(data, dict):
                data = pd.DataFrame(data)

            table = pa.Table.from_pandas(data)
            with pq.ParquetWriter(filename, table.schema, compression="snappy") as writer:
                writer.write_table(table)
            logging.info(f"Parquet file created: {filename}")
        except Exception as e:
            logging.error(f"Failed to create Parquet file: {e}")
    
    @staticmethod
    def write_json(data: Union[pd.DataFrame, dict], filename: str, **kwargs) -> None:
        """
        Save data as a JSON file. Accepts either a DataFrame or a dictionary.

        Args:
            data (Union[pd.DataFrame, dict]): The data to save.
            filename (str): The name of the file to save.
            **kwargs: Additional arguments for json.dump.
        """
        if isinstance(data, dict):
            data = pd.DataFrame(data)

        try:
            data.to_json(filename, orient="records", lines=True, **kwargs)
            logging.info(f"File saved to {filename}")
        except Exception as e:
            logging.error(f"Failed to save JSON file: {e}")

    @staticmethod
    def write_feather(data: Union[pd.DataFrame, dict], filename: str) -> None:
        """
        Create a new Feather file with the given data.

        Args:
            data (pd.DataFrame): Data to write.
            filename (str): File name.
        """
        try:
            if isinstance(data, dict):
                data = pd.DataFrame(data)
                
            table = pa.Table.from_pandas(data)
            with open(filename, "wb") as f:
                writer = ipc.RecordBatchStreamWriter(f, table.schema)
                writer.write_table(table)
                writer.close()
            logging.info(f"Feather file created: {filename}")
        except Exception as e:
            logging.error(f"Failed to create Feather file: {e}")

    @staticmethod
    def write_sqlite(
        data: Union[pd.DataFrame, dict], db_name: str, table_name: str
    ) -> None:
        """
        Save data to a SQLite database, overwriting the table if it exists.

        Args:
            data (Union[pd.DataFrame, dict]): The data to save.
            db_name (str): The name of the SQLite database file.
            table_name (str): The name of the table to save data to.
        """
        if isinstance(data, dict):
            data = pd.DataFrame(data)

        try:
            with sqlite3.connect(db_name) as conn:
                data.to_sql(table_name, conn, if_exists="replace", index=False)
            logging.info(f"Table '{table_name}' saved to database '{db_name}'")
        except Exception as e:
            logging.error(
                f"Failed to save table '{table_name}' to database '{db_name}': {e}"
            )

    @staticmethod
    def write_hdf5(data: Union[pd.DataFrame, dict], filename: str, key: str) -> None:
        """
        Save data as an HDF5 file.

        Args:
            data (Union[pd.DataFrame, dict]): The data to save.
            filename (str): The name of the file to save.
            key (str): The key (table name) under which the data will be saved.
        """
        if isinstance(data, dict):
            data = pd.DataFrame(data)

        try:
            data.to_hdf(filename, key=key, mode="w", format="table", index=False)
            logging.info(f"Data saved to {filename} under key '{key}'")
        except Exception as e:
            logging.error(f"Failed to save HDF5 file: {e}")

    @staticmethod
    def write_pickle(data: Union[pd.DataFrame, dict], filename: str, **kwargs) -> None:
        """
        Save data as a Pickle file. Accepts either a DataFrame or a dictionary.

        Args:
            data (Union[pd.DataFrame, dict]): The data to save.
            filename (str): The name of the file to save.
            **kwargs: Additional arguments for pickle.dump.
        """
        if isinstance(data, dict):
            data = pd.DataFrame(data)

        try:
            with open(filename, "wb") as file:
                pickle.dump(data, file, **kwargs)
            logging.info(f"File saved to {filename}")
        except Exception as e:
            logging.error(f"Failed to save Pickle file: {e}")

    #  Read Methods -------------------------------------------------------------------------------
    @staticmethod
    def _read_file(filename: str, func: Callable, **kwargs) -> Optional[pd.DataFrame]:
        """
        Generic function to handle file reading.

        Args:
            filename (str): The name of the file to read.
            func (Callable): The function to use for reading.
            **kwargs: Additional arguments for the reading function.

        Returns:
            pd.DataFrame: The loaded DataFrame, or None if an error occurs.
        """
        if not os.path.exists(filename):
            logging.error(f"File does not exist: {filename}")
            return None

        try:
            return func(filename, **kwargs)
        except Exception as e:
            logging.error(f"Failed to read file: {e}")
            return None

    @staticmethod
    def read_csv(filename: str, **kwargs) -> pd.DataFrame:
        """
        Read data from a CSV file and return it as a DataFrame.

        Args:
            filename (str): The name of the file to read.
            **kwargs: Additional arguments for pandas read_csv.

        Returns:
            pd.DataFrame: The data read from the file.
        """
        if not os.path.exists(filename):
            logging.error(f"File does not exist: {filename}")
            return pd.DataFrame()

        try:
            return pd.read_csv(filename, **kwargs)
        except Exception as e:
            logging.error(f"Failed to read CSV file: {e}")
            return pd.DataFrame()

    @staticmethod
    def read_parquet(filename: str) -> pd.DataFrame:
        """
        Read all data from a Parquet file.

        Args:
            filename (str): File name.

        Returns:
            pd.DataFrame: Combined data.
        """
        if not os.path.exists(filename):
            logging.error(f"File does not exist: {filename}")
            return pd.DataFrame()

        try:
            # Lê todos os row groups do arquivo
            parquet_file = pq.ParquetFile(filename)
            dataframes = [parquet_file.read_row_group(i).to_pandas() for i in range(parquet_file.num_row_groups)]
            combined_data = pd.concat(dataframes, ignore_index=True)
            logging.info(f"Parquet file read successfully: {filename}")
            return combined_data
        except Exception as e:
            logging.error(f"Failed to read Parquet file: {e}")
            return pd.DataFrame()

    @staticmethod
    def read_json(filename: str, **kwargs) -> pd.DataFrame:
        """
        Read data from a JSON file and return it as a DataFrame.

        Args:
            filename (str): The name of the file to read.
            **kwargs: Additional arguments for pandas read_json.

        Returns:
            pd.DataFrame: The data read from the file.
        """
        if not os.path.exists(filename):
            logging.error(f"File does not exist: {filename}")
            return pd.DataFrame()

        try:
            return pd.read_json(filename, orient="records", lines=True, **kwargs)
        except Exception as e:
            logging.error(f"Failed to read JSON file: {e}")
            return pd.DataFrame()

    @staticmethod
    def read_feather(filename: str) -> pd.DataFrame:
        """
        Read all data from a Feather file by combining all batches.

        Args:
            filename (str): File name.

        Returns:
            pd.DataFrame: Combined data.
        """
        if not os.path.exists(filename):
            logging.error(f"File does not exist: {filename}")
            return pd.DataFrame()

        try:
            with open(filename, "rb") as f:
                reader = ipc.open_stream(f)
                dataframes = [batch.to_pandas() for batch in reader]
                combined_data = pd.concat(dataframes, ignore_index=True)
            logging.info(f"Feather file read successfully with multiple batches.")
            return combined_data
        except Exception as e:
            logging.error(f"Failed to read Feather file: {e}")
            return pd.DataFrame()
        
    @staticmethod
    def read_sqlite(db_name: str, table_name: str) -> pd.DataFrame:
        """
        Read data from a SQLite database table and return it as a DataFrame.

        Args:
            db_name (str): The name of the SQLite database file.
            table_name (str): The name of the table to read data from.

        Returns:
            pd.DataFrame: The data read from the table.
        """
        try:
            with sqlite3.connect(db_name) as conn:
                query = f"SELECT * FROM {table_name}"
                data = pd.read_sql(query, conn)
            logging.info(
                f"Table '{table_name}' read successfully from database '{db_name}'"
            )
            return data
        except Exception as e:
            logging.error(
                f"Failed to read table '{table_name}' from database '{db_name}': {e}"
            )
            return pd.DataFrame()

    @staticmethod
    def read_hdf5(filename: str, key: str) -> pd.DataFrame:
        """
        Read data from an HDF5 file and return it as a DataFrame.

        Args:
            filename (str): The name of the file to read.
            key (str): The key (table name) from which the data will be read.

        Returns:
            pd.DataFrame: The data read from the file with reset index.
        """
        if not os.path.exists(filename):
            logging.error(f"File does not exist: {filename}")
            return pd.DataFrame()

        try:
            data = pd.read_hdf(filename, key=key)
            data.reset_index(drop=True, inplace=True)
            logging.info(f"Data read from {filename} under key '{key}' with index reset")
            return data
        except Exception as e:
            logging.error(f"Failed to read HDF5 file: {e}")
            return pd.DataFrame()

    @staticmethod
    def read_pickle(
        filename: str, **kwargs
    ) -> Optional[Union[pd.DataFrame, list[dict]]]:
        """
        Read all data from a Pickle file, handling multiple sequential objects,
        and return it as a DataFrame or a list of dictionaries.

        Args:
            filename (str): The name of the file to read.
            return_type (str): The format to return data in ('dataframe' or 'dict').
            **kwargs: Additional arguments for handling the data.

        Returns:
            Optional[Union[pd.DataFrame, list[dict]]]: The concatenated data read from the file.
        """
        if not os.path.exists(filename):
            logging.error(f"File does not exist: {filename}")
            return None

        try:
            dfs = []
            with open(filename, "rb") as file:
                while True:
                    try:
                        data = pickle.load(file)
                        if isinstance(data, pd.DataFrame):
                            dfs.append(data)
                        elif isinstance(data, dict):
                            dfs.append(pd.DataFrame(data))
                    except EOFError:
                        break

            combined_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

            return combined_df
        except Exception as e:
            logging.error(f"Failed to read Pickle file: {e}")
            return None

    # Append Methods ------------------------------------------------------------------------------
    @staticmethod
    def append_to_file(
        df: pd.DataFrame, filename: str, file_type: str, **kwargs
    ) -> None:
        """
        Append the DataFrame to a specified file without loading the entire file into memory.

        Args:
            df (pd.DataFrame): The DataFrame to append.
            filename (str): The file path to append to.
            file_type (str): The file type (e.g., 'csv', 'parquet', 'sqlite', 'hdf5', 'pickle').
            **kwargs: Additional arguments specific to the file type.

        Raises:
            ValueError: If the file type is not supported or if append operation is not feasible.
        """
        if file_type == "csv":
            DataStorage._append_csv(df, filename, **kwargs)
        elif file_type == "parquet":
            DataStorage._append_parquet(df, filename, **kwargs)
        elif file_type == "json":
            DataStorage._append_json(df, filename, **kwargs)
        elif file_type == "feather":
            DataStorage._append_feather(df, filename, **kwargs)
        elif file_type == "sqlite":
            DataStorage._append_sqlite(df, filename, **kwargs)
        elif file_type == "hdf5":
            DataStorage._append_hdf5(df, filename, **kwargs)
        elif file_type == "pickle":
            DataStorage._append_pickle(df, filename, **kwargs)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def _append_csv(data: Union[pd.DataFrame, dict], filename: str, **kwargs) -> None:
        """
        Append data to a CSV file incrementally without loading the entire file into memory.

        Args:
            data (Union[pd.DataFrame, dict]): The data to append.
            filename (str): The file path to append to.
            **kwargs: Additional arguments for pandas to_csv.
        """
        if isinstance(data, dict):
            data = pd.DataFrame(data)

        mode = "a" if os.path.exists(filename) else "w"
        header = not os.path.exists(filename)  # Write header only if file doesn't exist

        try:
            data.to_csv(filename, mode=mode, index=False, header=header, **kwargs)
            logging.info(f"Appended data to CSV file: {filename}")
        except Exception as e:
            logging.error(f"Failed to append to CSV file: {e}")

    @staticmethod
    def _append_parquet(data: Union[pd.DataFrame, dict], filename: str) -> None:
        """
        Append data to an existing Parquet file by re-writing all row groups.

        Args:
            data (Union[pd.DataFrame, dict]): Data to append.
            filename (str): File name.
        """
        try:
            if isinstance(data, dict):
                data = pd.DataFrame(data)

            table = pa.Table.from_pandas(data)

            if os.path.exists(filename):
                # Lê todos os row groups do arquivo existente
                parquet_file = pq.ParquetFile(filename)
                existing_row_groups = [
                    parquet_file.read_row_group(i) for i in range(parquet_file.num_row_groups)
                ]

                # Cria um novo arquivo e escreve todos os row groups
                with pq.ParquetWriter(filename, parquet_file.schema_arrow, compression="snappy") as writer:
                    # Reescreve os row groups existentes
                    for row_group in existing_row_groups:
                        writer.write_table(row_group)
                    # Adiciona o novo row group
                    writer.write_table(table)
                logging.info(f"Data appended to Parquet file: {filename}")
            else:
                # Cria um novo arquivo Parquet
                DataStorage.write_parquet(data, filename)
        except Exception as e:
            logging.error(f"Failed to append to Parquet file: {e}")

    @staticmethod
    def _append_json(data: Union[pd.DataFrame, dict], filename: str, **kwargs) -> None:
        """
        Append data to a JSON file incrementally without loading the entire file into memory.

        Args:
            data (Union[pd.DataFrame, dict]): The data to append.
            filename (str): The file path to append to.
            **kwargs: Additional arguments for json.dump.
        """
        if isinstance(data, dict):
            data = pd.DataFrame(data)

        try:
            mode = "a" if os.path.exists(filename) else "w"
            with open(filename, mode) as file:
                data.to_json(file, orient="records", lines=True, **kwargs)
            logging.info(f"Appended data to JSON file: {filename}")
        except Exception as e:
            logging.error(f"Failed to append to JSON file: {e}")

    @staticmethod
    def _append_feather(data: Union[pd.DataFrame, dict], filename: str) -> None:
        """
        Append data to an existing Feather file incrementally by writing new batches.

        Args:
            data (pd.DataFrame): Data to append.
            filename (str): File name.
        """
        try:
            if isinstance(data, dict):
                data = pd.DataFrame(data)
            
            table = pa.Table.from_pandas(data)

            if os.path.exists(filename):
                with open(filename, "rb") as f:
                    reader = ipc.open_stream(f)
                    existing_batches = list(reader)  # Lê todos os batches existentes
                    schema = reader.schema

                # Valida se o esquema do novo batch é compatível
                if schema != table.schema:
                    raise ValueError("Schema of the new data does not match the existing data.")

                # Reescreve o arquivo com todos os batches antigos e o novo batch
                with open(filename, "wb") as f:
                    writer = ipc.RecordBatchStreamWriter(f, schema)
                    for batch in existing_batches:
                        writer.write_batch(batch)
                    writer.write_table(table)  # Adiciona o novo batch
                    writer.close()
                logging.info(f"Data appended to Feather file: {filename}")
            else:
                # Cria um novo arquivo se ele não existir
                DataStorage.write_feather(data, filename)
        except Exception as e:
            logging.error(f"Failed to append to Feather file: {e}")

    @staticmethod
    def _append_sqlite(
        data: Union[pd.DataFrame, dict], db_name: str, table_name: str
    ) -> None:
        """
        Append data to a SQLite database table. Creates the table if it doesn't exist.

        Args:
            data (Union[pd.DataFrame, dict]): The data to append.
            db_name (str): The name of the SQLite database file.
            table_name (str): The name of the table to append data to.
        """
        if isinstance(data, dict):
            data = pd.DataFrame(data)

        try:
            with sqlite3.connect(db_name) as conn:
                data.to_sql(table_name, conn, if_exists="append", index=False)
            logging.info(
                f"Data appended to table '{table_name}' in database '{db_name}'"
            )
        except Exception as e:
            logging.error(
                f"Failed to append data to table '{table_name}' in database '{db_name}': {e}"
            )

    @staticmethod
    def _append_hdf5(data: Union[pd.DataFrame, dict], filename: str, key: str) -> None:
        """
        Append data to an HDF5 file incrementally without loading the entire file into memory.

        Args:
            data (Union[pd.DataFrame, dict]): The data to append.
            filename (str): The name of the file to append to.
            key (str): The key (table name) under which the data will be appended.
        """
        if isinstance(data, dict):
            data = pd.DataFrame(data)

        # Reset index before appending
        data.reset_index(drop=True, inplace=True)

        try:
            if os.path.exists(filename):
                # Append data incrementally
                data.to_hdf(
                    filename,
                    key=key,
                    mode="a",
                    format="table",
                    append=True,
                    index=False,
                )
                logging.info(f"Data appended to {filename} under key '{key}'")
            else:
                # Create new file and write data
                data.to_hdf(filename, key=key, mode="w", format="table", index=False)
                logging.info(
                    f"HDF5 file created and data written to {filename} under key '{key}'"
                )
        except Exception as e:
            logging.error(f"Failed to append to HDF5 file: {e}")

    @staticmethod
    def _append_pickle(
        data: Union[pd.DataFrame, dict], filename: str, **kwargs
    ) -> None:
        """
        Append data to a Pickle file incrementally without loading the entire file into memory.

        Args:
            data (Union[pd.DataFrame, dict]): The data to append.
            filename (str): The file path to append to.
            **kwargs: Additional arguments for pickle.
        """
        if isinstance(data, dict):
            data = pd.DataFrame(data)

        try:
            mode = "ab" if os.path.exists(filename) else "wb"
            with open(filename, mode) as file:
                pickle.dump(data, file, **kwargs)
            logging.info(f"Appended data to Pickle file: {filename}")
        except Exception as e:
            logging.error(f"Failed to append to Pickle file: {e}")

    # Remove Methods ------------------------------------------------------------------------------
    @staticmethod
    def remove_file(filename: str) -> None:
        """
        Remove a specified file from the filesystem.

        Args:
            filename (str): The name of the file to remove.
        """
        if os.path.exists(filename):
            try:
                # Clean up temporary file
                if "db" in filename:
                    try:
                        # Delay removal to ensure connection is closed
                        import gc

                        gc.collect()  # Force garbage collection to close any open SQLite connections
                    except Exception as e:
                        logging.error(f"Failed to clean SQLite resources: {e}")

                os.remove(filename)
                logging.info(f"File {filename} removed successfully.")
            except Exception as e:
                logging.error(f"Failed to remove file {filename}: {e}")
        else:
            logging.warning(f"File {filename} does not exist.")
