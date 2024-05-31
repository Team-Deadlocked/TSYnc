import os
import pickle
import errno
import time



class FileData(object):

    def __init__(self, file_name, time):
        self.name = file_name
        self.time = time


class PersistentSet(object):

    def __init__(self, pkl_filename):
        self.pkl_filename = pkl_filename
        self.timestamp = None
        try:
            pkl_object = open(self.pkl_filename, 'rb')
            self.set = pickle.load(pkl_object)
        except:
            self.set = set()

    def add(self, element):
        self.set.add(element)
        pkl_object = open(self.pkl_filename, 'wb')
        pickle.dump(self.set, pkl_object)
        pkl_object.close()

    def remove(self, element):
        self.set.remove(element)
        pkl_object = open(self.pkl_filename, 'wb')
        pickle.dump(self.set, pkl_object)
        pkl_object.close()

    def list(self):
        return list(self.set)

    def get_modified_timestamp(self):
        try:
            with open(self.pkl_filename, 'rb') as pkl_object:
                try:
                    pickle.load(pkl_object)  # Load set
                    timestamp = pickle.load(pkl_object)  # Load timestamp
                    return timestamp
                except EOFError:
                    return 0  # File is empty
        except FileNotFoundError:
            return 0  # File does not exist

    def update_modified_timestamp(self):
        """
        update last sync time
        """
        pkl_object = open(self.pkl_filename, 'wb')
        pickle.dump(self.set, pkl_object)
        #push current time
        pickle.dump(time.time, pkl_object)
        pkl_object.close()


class FilesPersistentSet(PersistentSet):

    def __init__(self, pkl_filename):
        super(FilesPersistentSet, self).__init__(pkl_filename)

    def add(self, file_name, modified_time):
        super(FilesPersistentSet, self).add(FileData(file_name, modified_time))

    def remove(self, file_name):
        for filedata in list(self.set):
            if file_name == filedata.name:
                self.set.remove(filedata)

