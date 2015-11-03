---
layout: main
title: Performance
tagline: What Ufora can optimize and what it can't
---

# Compilation and parallelism.

The Ufora VM performs two kinds of optimization: JIT compilation,
which ensures that single-threaded code is fast, and automatic
parallelization, which ensures that you can use many cores at once.
In both cases, our goal is to get as close as possible to the
performance one can achieve using C with hand-crafted parallelism.
As with any programming model, however, there are often multiple ways
to write the same program that have very different performance implications.
This section will help you understand what the Ufora VM can optimize
and what it can't.

Generally speaking, there's a lot of overhead for invoking Ufora, since it has to
compile your code, and has overhead shipping objects to the server. Don't expect
Ufora to speed up things that are already pretty fast (e.g. less than a second or two).

For achieving maximum single-threaded code, the main takeaways are:

* Numerical calculations involving ints and floats will be super fast - very close to what you can get with C.
* There is no penalty for using higher-order functions, yield, classes, etc. Ufora can usually optimize it all away.
* Prefer for each variable to take a small number of distinct "types" (e.g. 'int', 'float', 'tuple of int and string')
within a given loop. Preferably only one or two.
* Tuples with a structure that is stable throughout your program (e.g. they always have three elements) will be very fast.
* Tuples where the number of elements varies with program data will be slow - use lists for this.
* Lists prefer to be homogenously typed - e.g. a list with only floats in it will be faster to access than a list with
floats and ints.
* There is more overhead for using a list in Ufora than in CPython - prefer a few large lists to a lot of small lists. [^1]
* Deeply nested lists of lists are slow. [^1]
* Dictionaries are very slow. [^1]
* Strings are fast.

For achieving maximum parallelism, the main takeaways are:

* Ufora parallelizes within stackframes - if you write `f(g(), h())`, Ufora will be able to run `g()` and `h()` in parallel.
* Parallel calls within parallel calls work.
* List comprehensions, xrange, sum, are parallel out of the box.
* Ufora parallelizes adaptively - it won't be triggered if all the cores in the system are saturated.
* Ufora won't currently parallelize for and while loops.
* Passing generator expressions into 'sum' or other parallelizable algorithms parallelizes.
* Large lists have a strong performance preference for "cache local" access.

# The Ufora JIT compiler

## The basic behavior of the JIT

The Ufora JIT compiler optimizes the code your program spends the most time in.
So, for instance, if you write

```python
def loopSum(x):
    result = 0.0
    while x > 0:
        result = result + x
        x = x - 1
    return result
print loopSum(1000000000)
```

the Ufora VM will notice that your program is spending a huge amount of time
in the `while` loop and produce a fast machine-code version of it in which `x`
and `result` are held in registers (as 64 bit integer and floats,
respectively).  We generate machine code using the excellent and widely-used
[llvm](http://llvm.org/ project. In simple numerical programs, you'll end up
with the same exact code you'd get from a good C++ compiler. Today, these are
table-stakes for all JIT compilers.

## Use higher-order functions, classes, and other language constructs.

Unlike most JIT compilers applied to dynamically typed languages, Ufora is
designed to work well with higher-order functions and classes. In general,
this is a thorny problem for any system attempting to speed up python because
in regular python programs, it's possible to modify class and instance methods
during the execution of the program.  This means that any generated code in
tight loops has to check repeatedly to see whether some method call has
changed [^2].  Because this is disabled in code running in Ufora, Ufora can
agressively optimize away these checks, perform agressive function inlining,
and generally perform a lot of the optimizations you see in compilers
optimizing statically typed languages like C++ or Java. This is great because
it means you can refactor your code into classes and objects without paying a
performance penalty.

This flexibility comes at a cost: the compiler generates new code for every
combination of types and functions that the it sees. For instance, if you
write

```python
def loopSum(x, f):
    result = 0
    while x>0:
        result = result + f(x)
        x = x - 1
    return result
```

then the compiler will generate completely different code for
`loopSum(1000000, lambda x:x)` and `loopSum(1000000, lambda x:x*x)` and both
will be very fast.  This extends to classes. For instance, if you write

```python
class Add:
    def __init__(self, arg):
        self.arg = arg

    def __call__(self, x):
        return self.arg + x

class Mul:
    def __init__(self, arg):
        self.arg = arg

    def __call__(self, x):
        return self.arg * x

class Compose:
    def __init__(self, f, g):
        self.f = f
        self.g = g

    def __call__(self, x):
        return self.f(self.g(x))
```

then you'll get idential performance if you write
`loopSum(1000000, lambda x: x * 10.0 + 20.0)` and
`loopSum(1000000, Compose(Mul(10.0), Add(20.0)))` -
they boil down to the same mathematical operations,
and because Ufora doesn't allow class methods to be
modified, Ufora can reason about the code well enough
to produce fast code.

## Keep the total number of type combinations small

The Ufora compiler operates by tracking all the distinct combinations of types
it sees for all the variables in a given stackframe, and generating code for
each combination. This means that code like

```python
def typeExplosion(v):
    a = None
    b = None
    c = None
    for x in v:
        if x < 1:
            a = x
        elif x < 2:
            b = x
        else:
            c = x
    return (a,b,c)
```

could generate a lot of code. For instance, if 'a', 'b', and 'c' can all be
None or an integer, you'll  end up with 8 copies of the loop. That by itself
isn't a problem, but if you keep adding variables, the total number of types
grows exponentially - eventually, you'll wind up waiting forever for the
compiler to finish generating code.

## Tuples as structure

Speaking of 'types', Ufora considers function instances, class instances, and
tuples to be "structural". This means that the compiler will agressively track
type information about the contents of these objects. So, for instance,
`lambda x: x + y` is a different type if `y` is an integer or `y` is a float
in the surrounding scope. Similarly, `(x,y)` tracks the type information of
both `x` and `y`. This is one of the reasons that there is no penalty for
putting values into objects or tuples - the Ufora compiler is tracking that
type information the whole way through, so that `(x,y)[0]` is semantically
equivalent to `x` regardless of what `y` is.

This is great until you start using tuples to represent data with a huge
variety of structure, which can overwhelm the compiler. For instance,

```python
def buildTuple(ct):
    res = ()
    for ix in xrange(ct):
        res = res + (ix,)
    return res
print buildTuple(100)
```

will produce a lot of code, because it will produce separate copies of the
loop for the types "empty tuple", "tuple of one integer", "tuple of two
integers", ..., "tuple of 99 integers", etc.

Because of this, tuples should generally be used when their shape will be
stable (e.g. producing a small number of types) over the course of the program
and you want the compiler to be able to see it. [^3]

Note also that this means that if you have tuples with heterogeneous types and
you index into the tuple with a non-constant index, you will generate slower
code. This is because the compiler needs to  generate a separate pathway for
each possible resulting type. For instance, if you write

```python
aTuple = (0.0, 1, "a string", lambda x:x)
functionCount = floatCount = 0

for ix in range(100):
    #pull an element out of the tuple - the compiler can't tell what
    #kind of element it is ahead of time
    val = aTuple[ix % len(aTuple)]

    if isinstance(val, type(lambda: None)):
        functionCount = functionCount + 1
    elif isinstance(val, float):
        floatCount = floatCount + 1
```

then the compiler will need to generate branch code at the `aTuple[...]`
instruction. This will work, but will be slower than it would be if the tuple
index could be known ahead of time.

## Lists

Lists are designed to hold data that varies in structure. The compiler doesn't
attempt to track the types of the individual objects inside of a list.
Specifically, that means that `[1, 2.0]` and `[2.0, 1]` have the same type -
they're both 'list of int and float', whereas `(1, 2.0)` and `(2.0, 1)` are
different types.

Lists are fastest when they're homogenous (e.g. entirely containing elements
of the same type). This is because the Ufora VM can pack data elements very
tightly (since they all have the same layout) and can generate very efficient
lookup code. Lists with heterogenous types are still fast, but the more types
there are, the more code the compiler needs to generate in order to work with
them, so try to keep the total number of types small.

In general, lists have more overhead in Ufora than in CPython[^4]. This is
because lists are the primary "big data" structure for Ufora - a list can be
enormous (up to terabytes of data), and the data structure that represents
them is rather large and complex. So, if possible try to structure your
program so that you create a few bigger lists, rather than a lot of little
lists.

The one exception to this rule is the way that lists are constructed: Ufora is
optimized so that if `l` is a list, and you write `l + [element]` it will
optimize away the creation of the intermediate small list, and is careful not
to duplicate `l` unless absolutely necessary. This is, in fact, the fastest
way to build lists

Large lists are cheap to concatenate - they're held as a tree structure,
so you don't have to worry that each time you concatenate you're making a
copy.

Finally, avoid nesting lists deeply - this places a huge strain on the
"big data" component of Ufora's internal infrastructure.

## Dictionaries and Strings

Dictionaries are currently **very** slow[^5]. Don't use them inside of loops.

Strings, however are fast. The Ufora string structure is 32 bytes, allowing
the VM to pack any string of 30 characters or less into a data structure that doesn't
hit the memory manager.  Indexing into strings is also fast. Strings may be as large as you like
(if they get big enough, they'll be split across machines).

Note that for strings that are under 100000 characters, string concatenation makes a copy,
so you can accidentally get N^2 performance behavior if you write code where you are repeatedly
concatenating a large string to a small string.

# Parallelism

## The core model of parallelism in Ufora

Ufora exploits "dataflow" parallelism at the stack-frame level. Ufora operates
by executing your code on a single thread and then periodically interrupting it
and walking its stack. It looks at the flow of data within each stackframe to see
whether there are upcoming calls to functions that it can schedule while the current
call is executing.

For instance, if you write `f(g(),h())`, then while Ufora is
executing the call to `g()`, it can see that you are going to execute `h()` next. If you
have unsaturated cores, it will rewrite the stackframe to also call `h()` in parallel.
When both calls return, it will resume and call `f`. You can think of this as
fork-join parallelism where the forks are placed automatically.

As an example, the simple divide-and-conquer implementation of a "sum" function could
be written as

```python
def sum(a,b,f):
    if a >= b:
        return 0
    if a + 1 >= b:
        return f(a)

    mid = (a+b)/2

    return sum(a,mid,f) + sum(mid,b,f)
```

We can then write `sum(0, 1000000000000, lambda x: x**0.5)` and get a parallel
implementation. This works because each call to `sum` contains two recursive
calls to `sum`, and Ufora can see that these are independent.

Note that Ufora assumes that exceptions are rare - in the case of `f(g(),h())`,
Ufora assumes that by default, `g()` is not going to throw an exception and that
it can start working on `h()`. In the case where `g()` routinely throws exceptions,
Ufora will start working on `h()` only to find that the work is not relevant.
Some python idioms use exceptions for flow control: for instance, accessing an attribute
and then catching `AttributeError` as a way of determining if an object meets an
interface. In this case, make sure that you don't have an expensive operation in between
the attribute check and the catch block.

## Nested Parallelism

This model of parallelism naturally allows for nested parallelism. For instance,
`sum(0,1000,lambda x: sum(0,x,lambda y:x*y))` will be parallel in both the
outer `sum` but also in the inner `sum`. This is because Ufora doesn't really
distinguish between the two - it's parallelizing stackframes, not algorithms.

## Adaptive Parallelism

Ufora's parallelism is adaptive and dynamic - it doesn't know ahead of time how
the workload is distributed across your functions. It operates by agressively splitting
stackframes until cores are saturated, waiting for threads to finish, and then
splitting additional threads.

This model is particularly effective when your functions have different runtimes
depending on their input. For instance, consider

```python
def isPrime(p):
    if p < 2: return 0
    x = 2
    while x*x <= p:
        if p%x == 0:
            return 1
        x = x + 1
    return 1

sum(isPrime(x) for x in xrange(10000000))
```

Calls to isPrime with large integers take a lot longer than calls to isPrime
with small integers, because we have to divide so many more numbers into the
large ones. Naively allocating chunks of the 10000000 range to cores will end
up with some cores working while others finish their tasks early. Ufora can handle
this because it sees the fine structure of parallelism available to `sum` and can
repeatedly subdivide the larger ranges, keeping all the cores busy.

This technique works best, however, when your tasks subdivide to a very
granular level. In the case where you have a few subtasks with long sections
of naturally single-threaded code, Ufora may not schedule those sections until
partway through the calculation. You'll get better performance if you can find
a way to get the calculation to break down as finely as possible.

It's also important to note that the Ufora VM doesn't penalize you for writing
your code in a parallel way. Ufora machine code is optimized for single-threaded
execution - it's only when there are unused cores and Ufora wants more tasks
to work on that we split stackframes, in which case we pop the given stackframe
out of native code and back into the interpreter.

The one caveat here is that function calls have stack-frame overhead. Code that's
optimized for maximum performance sometimes has conditions to switch it out of a
recursive "parallelizable" form and into a loop. This is a tradeoff between
single-threaded performance and parallelism granularity.

## List comprehensions and sum are parallel out of the box

By default, list comprehensions like `[isPrime(x) for x in xrange(10000000)]` are
parallel if the generator in the righthand side supports the `__pyfora_generator__`
parallelism model, which both `xrange`, and lists support out of the box.

Similarly, functions like `sum` are parallel if their argument supports the
`__pyfora_generator__` interface. Note that this subtly changes the semantics of `sum`:
in standard python, `sum(f(x) for x in xrange(4))` would be equivalent to

```python
(((f(0)+f(1))+f(2))+f(3))+f(4)
```

performing the addition operations linearly. In the parallel case, we have a
tree structure:

```python
(f(0)+f(1)) + (f(2)+f(3))
```

when addition is associative. Usually this produces the same results, but it's not
always true. For instance, roundoff errors in floating point arithmetic mean that
floating point addition is not perfectly associative[^6]. As this
is a deviation from standard python, we plan to make it an optional feature in the
future.

## Loops are sequential

Note that Ufora doesn't try to parallelize across loops. The `isPrime` example above
runs sequentially. In the future, we plan to implement loop unrolling so that if you
write something like

```python
res = None
for x in xrange(...):
    res = f(g(x), res)
```

and the calls to `g` are sufficiently expensive, we'll be able to schedule those calls
in parallel and then execute the naturally sequential calls to `f` as they complete.
For the moment, however, assume that `while` and `for` loops are sequential (although
functions inside them are all candidates for parallelism).

## Lists prefer cache-local access

Lists are the basic building-block for "big data" in Ufora. A list that's large enough
will get split across multiple machines. Ufora organizes a list's data into chunks
of contiguous indices, where each chunk represents ~50-100 mb of data.

When one of your threads (in this context, a thread is just a collection of
stackframes of python code that Ufora hasn't decided to subdivide) indexes
into a very large list and that data isn't on the same machine as the thread,
Ufora must decide what to do: does it move the thread to the data, or the data
to the thread?  This is called a "cache miss". Threads tend to be much smaller
than 50 mb, so usually it will move the thread to the remote machine.

If your thread starts accessing two different blocks in a list, and those two
blocks are not on the same machine, the thread will end up bouncing back and
forth between the two machines. Ufora can often see ahead of time that this
is going to happen: when you "cache miss", it's so expensive that Ufora has
time to try simulating your code where the missing data are replaced with futures,
to see if it can determine any additional values you're planning on reading.
In this case, the Ufora scheduler will try to schedule your thread and
those two blocks on the same machine so that the thread can stop bouncing
back and forth (which is incredibly slow).

All of this infrastructure is useless if you index randomly into very big lists (here, we mean
bigger than ~ 1/4 of a machine's worth of data). This is because it's now impossible
for the scheduler to find an allocation of blocks to machines where a large fraction
of your list accesses don't require you to cross a machine boundary.

As a result, you'll get the best performance if you can organize your program
so that list accesses are "cache local", meaning that when you access one part of a
list you tend to access other parts of the list that are nearby in the index
space.[^7]

[^1]: We consider this to be a performance defect that we can eventually fix.
    However, some of these defects will be easier to fix than others.

[^2]:
    e.g. the following code

        class X:
            def f(self):
                return 0

        x = X()

        print x.f()

        #modify all instances of 'X'
        X.f = lambda self: return 1

        print x.f()

        #now modify x itself
        x.f = lambda: return 2

        print x.f()

[^3]: we expect to be able to fix this over the long run by identifying cases where we have an inordinate
    number of types and moving to a collapsed representation in which we don't track all the possible
    combinations.

[^4]: another performance optimization we plan for the future will be to recognize the difference between
    small and large lists, and generate a faster implementation when we recognize ahead of time that
    lists are going to be small.

[^5]: something we can fix, but not currently scheduled. Let us know if you need this.

[^6]: For instance, `10e30 + (-10e30) + 10e-50` is not the same as `10e30 + ((-10e30) + 10e-50)`

[^7]:
    In the future, we plan to implement a "streaming read" model for
    inherently non-cache-local algorithms. Essentially the idea is to use the same
    simulation technique that we use to determine what your cache misses are going
    to be, but instead of using them for scheduling purposes, we will actually
    fetch the values and merge them back into the program. In a good implementation,
    this should allow for a very low per-value overhead scattered value read.
