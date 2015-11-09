---
layout: main
title: The Ufora subset of python
tagline: Python code that Ufora can execute.
category: documentation
---


# So what's "Pure Python"?

The Ufora VM executes a restricted, "purely functional" subset of python that we call
"Pure python." This essentially means that it executes python code in which

- all datastructures are immutable (e.g. no modification of lists)
- no operations have side-effects (e.g. no files, no `print`)
- all operations are deterministic (e.g. no access to system time.)

These restrictions are a crucial component of the kinds of reasoning that Ufora applies to
your code.  In the future, we plan to relax some of these constraints in certain settings.
But for the moment, the following features of regular python are disallowed:

- **Objects are immutable** (except for `self` in constructors). Expressions like  
`o.x = 10` are disallowed, as they
would modify `o`. The exception to the rule is `self` within `__init__`, where we use assignment to the fields of
`self` to construct the object.
- **Lists are immutable**. Expressions like `l[0] = 10` won't work, nor will `l.append(10)`.
Note that if you append to a list `x` by writing `x + [element]`, the compiler will generate efficient code.
- **Dictionaries are immutable**. In the future, we will support assignment to dictionaries in cases
where Ufora can prove that there is exactly one reference to the dictionary. But for the moment, dictionaries can only
be constructed from iterators (e.g. `dict((x, x**2) for x in xrange(100))`). Also note that as of this
writing, our dictionary implementation is quite slow, so use it sparingly. See the
[performance guide](https://ufora.github.io/ufora/github-pages/documentation/performance-guide.html).
- **No augmented assignment**. Expressions like `x += 10` are disabled since they modify `x`.
- `print` is disabled
- `locals()` and `globals()` are disabled
- `del` is disabled.
- **No `eval`**.
- **No `exec`**.

Do note, however, that regular variable assignment **does** work as expected.

# What happens if I violate one of the constraints?

Whenver you invoke Ufora on a block of python code, Ufora attempts to
give you either  (a) an identical answer to what you would have received if
you ran that code in your python interpreter locally, or (b) to raise an
exception [^1].

Constraint checking happens in two places. Some of the constraints are
enforced at parse-time. As soon as you enter a `with ufora.remotely` block,
Ufora tries to determine all the code your invocation can touch. If any of
that code contains syntatic elements that Ufora knows are invalid (such as
`print` statements),  it will generate an exception.

Other constraints are enforced at runtime.  For instance, the `append` method
of lists, when invoked in Ufora, raises a
`pyfora.Exceptions.InvalidPyforaOperation` exception  that's not catchable by
python code running inside of Ufora. This indicates that the program has
attempted to execute semantics that Ufora can't faithfully reproduce.

[^1]: Currently, the only intended exception to this rule is integer arithmetic: on the occurrence of an integer arithmetic overflow, Ufora will give you the semantics of the underyling hardware, whereas python will produce an object of type `long` with the correct value. Eventually, we will make this tradeoff configurable, but it has pretty serious performance implications, so for the moment we're just ignoring this difference.
