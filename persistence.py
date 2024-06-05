import os
import pickle
import time

class FileData:
    """Class to hold file name and modification time."""
    def __init__(self, file_name, mod_time):
        self.name = file_name
        self.time = mod_time

class PersistentSet:
    """Class to manage a persistent set of items using pickle."""
    def __init__(self, pkl_filename):
        self.pkl_filename = pkl_filename
        self.timestamp = None
        self.set = self._load_set()

    def _load_set(self):
        """Load the set from a pickle file."""
        if os.path.exists(self.pkl_filename):
            try:
                with open(self.pkl_filename, 'rb') as pkl_file:
                    return pickle.load(pkl_file)
            except (EOFError, pickle.UnpicklingError):
                pass  # Handle empty or corrupt pickle file
        return set()

    def _save_set(self):
        """Save the set to a pickle file."""
        with open(self.pkl_filename, 'wb') as pkl_file:
            pickle.dump(self.set, pkl_file)

    def add(self, element):
        """Add an element to the set and save."""
        self.set.add(element)
        self._save_set()

    def remove(self, element):
        """Remove an element from the set and save."""
        self.set.remove(element)
        self._save_set()

    def list(self):
        """Return a list of elements in the set."""
        return list(self.set)

    def get_modified_timestamp(self):
        """Get the modified timestamp from the pickle file."""
        if os.path.exists(self.pkl_filename):
            try:
                with open(self.pkl_filename, 'rb') as pkl_file:
                    pickle.load(pkl_file)  # Load set
                    return pickle.load(pkl_file)  # Load timestamp
            except (EOFError, pickle.UnpicklingError):
                pass  # Handle empty or corrupt pickle file
        return 0  # File does not exist or is empty

    def update_modified_timestamp(self):
        """Update the modified timestamp in the pickle file."""
        with open(self.pkl_filename, 'wb') as pkl_file:
            pickle.dump(self.set, pkl_file)
            pickle.dump(time.time(), pkl_file)

class FilesPersistentSet(PersistentSet):
    """Class to manage a persistent set of file data."""
    def __init__(self, pkl_filename):
        super().__init__(pkl_filename)

    def add(self, file_name, modified_time):
        """Add a file with its modification time to the set."""
        super().add(FileData(file_name, modified_time))

    def remove(self, file_name):
        """Remove a file from the set."""
        self.set = {filedata for filedata in self.set if filedata.name != file_name}
        self._save_set()

    def get(self, file_name):
        """Retrieve a FileData object based on the file name."""
        for filedata in self.set:
            if filedata.name == file_name:
                return filedata
        return None

import time
import os

class TimeKeeper:
    """Class to store and retrieve the current time in a file."""

    @staticmethod
    def update_time(filename='time_keeper.txt'):
        """Store the current time in the file."""
        with open(filename, 'w') as file:
            file.write(str(time.time()))

    @staticmethod
    def get_time(filename='time_keeper.txt'):
        """Retrieve the stored time from the file."""
        if os.path.exists(filename):
            with open(filename, 'r') as file:
                stored_time = file.read()
                if stored_time:
                    return float(stored_time)
        return None
