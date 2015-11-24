class NullObjectStore(object):
    '''
    A dummy object store that doesn't do anything.
    '''
    def listValues(self, prefix=''):
        return []

