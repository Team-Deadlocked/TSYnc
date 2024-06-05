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
