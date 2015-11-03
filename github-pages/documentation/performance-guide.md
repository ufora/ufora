---
layout: main
title: Performance
tagline: What Ufora can optimize and what it can't
---

## Compilation and parallelism.

The Ufora VM performs two kinds of optimization: JIT compilation,
which ensures that single-threaded code is fast, and automatic
parallelization, which ensures that you can use many cores at once.
In both cases, our goal is to get as close as possible to the 
performance one can achieve using C with hand-crafted parallelism.
As with any programming model, however, there are often multiple ways
to write the same program that have very different performance implications.
This section will help you understand what the Ufora VM can optimize
and what it can't.

## tl;dr 

For achieving maximum single-threaded code, the main takeaways are:

* Numerical calculations involving ints and floats will be super fast - very close to what you can get with C.
* There is no penalty for using higher-order functions, yield, classes, etc. Ufora can usually optimize it all away.
* Prefer for each variable to take a small number of distinct "types" (e.g. 'int', 'float', 'tuple of int and string')
within a given loop. Preferably only one or two.
* Lists prefer to be homogenously typed - e.g. a list with only floats in it will be faster to access than a list with
floats and ints, which in turn will be faster than a list with 
* Tuples with a structure that is stable throughout your program (e.g. they always have three elements) will be very fast.
* Tuples where the number of elements varies with program data will be slow - use lists for this.
* There is more overhead for using a list in Ufora than in CPython - prefer a few large lists to a lot of small lists. [^1]
* Deeply nested lists of lists are slow. [^1]
* Dictionaries are very slow. [^1]
* Strings are fast, especially if they are under 30 characters. However, unlike python strings, concatenation makes a copy,
so you can accidentally get N^2 behavior if you are not careful.

For achieving maximum parallelism, the main takeaways are:

* Nested and recursive parallelism works fine - if you have 10 tasks that create 10 subtasks
* Ufora parallelizes within stackframes - if you write `f(g(), h())`, Ufora will be able to run `g()` and `h()` in parallel.
* Ufora parallelizes adaptively - it won't be triggered if all the cores in the system are saturated.
* List comprehensions are naturally parallel.
* Ufora won't currently parallelize for and while loops.
* Passing generator expressions into 'sum' or other parallelizable algorithms parallelizes.
* Large lists have a strong performance preference for "cache local" access.
If you index randomly into big lists (here we mean really big, as in
gigabytes), the VM will be forced to constantly load data. However, if your
program tends to consume whole chunks of lists simultaneously, then Ufora will
attempt to lay data out so that your threads are always saturated.

## The Ufora JIT compiler

The Ufora JIT compiler (like many JIT compilers),
operates by watching where your program spends time, and optimizing that particular
code. So, for instance, if you write

```py
def loopSum(x):
	result = 0.0
	while x > 0:
		result = result + x
		x = x - 1
	return result
print loopSum(1000000000)
```

The Ufora VM will notice that your program is spending a huge amount of time
in this loop and produce a faster version of it in which `x` is known to always
be an integer, `result` to always be a floating point number, etc.  This lets it
generate efficient machine code (using the excellent and widely-used [llvm](http://llvm.org/) 
project for native code generation). In simple numerical programs, you'll end up
with the same exact code you'd get from a good C++ compiler.

However, unlike most JIT compilers applied to dynamically typed languages,
Ufora is  designed to work well with higher-order functions and classes. In
general, this is a thorny problem for any system attempting to speed up python
because in regular python programs, it's possible to modify class and instance
methods during the execution of the program.  This means that any generated
code in tight loops has to check repeatedly to see whether some method call
has changed.  Because this is disabled in code running in Ufora, Ufora can
agressively optimize away these checks, perform agressive function inlining, and generally
perform a lot of the optimizations you see in compilers optimizing statically typed
languages like C++ or Java. This is great because it means you can refactor your
code into classes and objects without paying a performance penalty.

[^1]: this is the current state of affairs. Some of these performance penalties would be easier to
	fix than others.