#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import ufora.util.StackInfo as StackInfo
import ufora.util.ManagedThread as ManagedThread
import threading


class AssertStableThreadCount(object):
    def __enter__(self):
        self.origThreads = ManagedThread.ManagedThread.allManagedThreads()

    def __exit__(self, *args):
        finalThreads = ManagedThread.ManagedThread.allManagedThreads()

        if len(self.origThreads) < len(finalThreads):
            print "\nThe following %s threads were left running by tests:\n" % (
                len(self.origThreads) - len(finalThreads)
                )
            self.printExcessThreads(finalThreads, self.origThreads)
            assert False, "Tests left behind threads."
        else:
            print "All test threads were properly cleaned up"

    def printExcessThreads(self, finalThreads, originalThreads):
        """Prints a stack trace for any thread in 'lookIn' that doesn't exit in 'lookFor'
        """
        origThreadIds = set([id(x) for x in originalThreads])

        stacktraces = StackInfo.getTraces()

        for thread in finalThreads:
            if id(thread) not in origThreadIds:
                print "Thread: ", thread
                print 'Stack:\n', ''.join(stacktraces[thread.ident])

                managedThread = ManagedThread.ManagedThread.threadByObjectId(id(thread))
                if managedThread is not None:
                    print "Thread Spawned From:"
                    print ''.join(managedThread.creatorStacktrace)
                print

