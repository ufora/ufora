---
layout: main
title: Running python code
tagline: How to use ufora.remote to execute code
---

Once you've booted a ufora cluster (remotely or locally), you can connect to it
and start executing code:

```python
import pyfora
ufora = pyfora.connect("http://localhost:8000/")
```

The variable `ufora` now holds an `Executor`, which is a live connection to
the cluster. There are two ways to use an `Executor`: using a futures model (
powerful but more cumbersome), or using `with` blocks, which we'll detail here.

First, let's define a function we want to work with:

```python
def isPrime(p):
    x = 2
    while x*x <= p:
        if p%x == 0:
            return 0
        x = x + 1
    return 1
```

Now, we can use the executor to do something interesting with the function.

```python
with ufora.remote.downloadAll():
    result = sum(isPrime(x) for x in xrange(10 * 1000 * 1000))

print result
```

The code contained in the `with` block gets shipped to the Ufora server along
with any dependent objects and code (like `isPrime`) you're referencing in the
block. This code gets translated into Ufora bitcode, and executed by the Ufora
VM. The resulting objects are returned over the `ufora` connection, which
downloads them and copies them back into the local environment because we used
`ufora.remote.downloadAll()`.

Now, imagine that we want to get a list of primes. We can then write

```python
with ufora.remote.remoteAll():
    primes = [x for x in xrange(10 * 1000 * 1000) if isPrime(x)]
```

Now, because we used `ufora.remote.remoteAll()`, the variable `primes` is a
_proxy_ to a list of primes (actually, it's a `RemotePythonObject`). Remote python
objects can be used in two ways: they can be downloaded into the local python
scope, or they can be passed to additional computations.  To download a proxy,
we might write

```python
primes = primes.toLocal().result()
```

If the list is very large, or our connection to the cluster is slow, however,
that might be a bad idea.  In this case, we can interact with the proxy object
again inside of another `with ufora.remote` block:

```python
with ufora.remote.downloadAll():
    lastFewPrimes = primes[-100:]
```

Ufora recognizes that `primes` refers to an object living remotely on the server,
and allows us to perform dependent computations on it, which we return as regular
python objects.

For convenience, we may also write:

```python
with ufora.remote.downloadSmall(bytecount=100*1024):
    ...
```

in which case objects requiring more than `bytecount` bytes will be left on the
server, and smaller objects will be downloaded. This pattern works well as long as
your objects are obviously on one side or the other of the threshold. If they're
not, we recommend leaving objects as remotes and downloading them as you need them.
