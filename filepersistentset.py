from persistence import PersistentSet, FileData


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
