# Ufora - Release Notes


## Known Issues

1. Assignment of cores to users is persistent across login sessions. When a user logs out of the system or closes their browser, any cores assigned to them are not released back to the pool of unassigned machines. Users must explicity set their core count to zero in order to relinquish their cores.

2. After stopping the ufora-worker service on an active worker (assigned to a user), it may take up to one minute for the updated core count to show up in the GUI.

3. All machines running the ufora-worker service MUST have the same number of CPU cores and the same amount of RAM.

4. The FORA language does not support Unicode yet. Non-ASCII characters will result in parse errors.

## Troubleshooting Tips

If the application appears to be in a bad state:

1. Reload the page in the browser. If the problem persists or if the page fail to reload correctly, check the browser's console (ctrl+alt+i/cmd+alt+i in Chrome) for any errors.
   If there are errors that suggest failure to load resources (HTTP 404: Not found), you probably need to restart the cluster. Skip to step 3.

2. If you see other kinds of errors or no errors at all, try setting your core count to zero, and once the cores show up as unassigned again, reset the count to the desired value. Now reload the page in the browser and resubmit your computations (ctrl/cmd+enter).

3. Restart the cluster.
On each worker, run `bin/ufora-worker stop` from the ufora package directory.
Stop the cluster manager by running `bin/stop` from the package directory.
Start the cluster manager by running `bin/start` from the package directory.
On each worer, run `bin/ufora-worker start`.

4. Contact the Ufora team: [support@ufora.com](mailto:support@ufora.com)
