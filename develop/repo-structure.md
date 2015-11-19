---
layout: main
title: Repository Structure
tagline: How Code is Organize in the Repo
category: develop
sort_index: 02
---

# Front-End and Auxiliaries
```
+-- build/          - Custom [WAF](https://waf.io/) tools used to build Ufora
|
+-- cppml/          - Implementation of the cppml extension to c++
|
+-- doc/            - Sphinx documentation for the pyfora package
|
+-- docker/         - Dockerfiles
|
+-- packages/
|   +-- python/     - Implementation of Ufora python packages for front-end
|   |   +-- pyfora/ - The pyfora front-end package
|
+-- test_scripts/   - unit-tests for Ufora that spin up multiple processes and are
|                     run as individual test-scripts.
|                     They can be triggered using `test.py -script`.
|
+-- third_party/    - Third party code that is built and linked with Ufora
```


# Backend

The Ufora backend source code is located under the `ufora/` top-level directory.
Its internal structure is:

```
+-- BackendGateway/     - A JSON-based service used to communicate with a Ufora cluster.
|                         The pyfora talks to it over socket.io.
|
+-- config/             - Configuration parameter loading, logging config, etc.
|
+-- core/               - Generic C++ (and some python) infrastructure for
|                         serialization, memory, some math, container types,
|                         pretty printing.
|
+-- cumulus/            - Implementation of the Ufora multi-machine infrastructure.
|                         Message passing layer, etc.
|
+-- distributed/        - Poorly named grab-bag of code for SharedState (which we will
|                         replace with kafka) and our AWS S3 interface.
|
|
+-- FORA/           - The FORA compiler, memory manager, FORA language
|   +--  Axioms/         - C++ implementations of the FORA language object model and
|   |                      associated classes
|   |
|   +--  builtin/        - fora implementation of the FORA language builtins
|   |
|   +-- Compiler/       - "judged" CFGs and conversion to "TypedFora" as a prelude to
|   |   |                 machine code generation.
|   |   +-- CompilerInstructionGraph/    - "judged" graph of instruction nodes.
|   |                                       Allows us to reason about code with
|   |                                       associated Judgments on the values.
|   |
|   +-- ControlFlowGraph/ - Core bitcode that all language code targets.
|   |
|   +-- Core/       - Utilities for executing interpreted code, and some
|   |   |             data-structures for the interpreter
|   |   |
|   |   +-- CSTValue            - a constant boxed value the compiler can hold
|   |   +-- ImplVal             - boxed values (not userfriendly)
|   |   +-- ImplValContainer    - boxed values, but with constructor/destructor
|   |   +-- ExecutionContext    - a single thread of FORA state
|   |   +-- MemoryPool          - the base memory abstraction for memory arenas
|   |   +-- Type                - the object that governs layout of objects in the
|   |                             interpreter.
|   |
|   +-- FORAValuePrinting/      - Utilities for formatting and printing FORA values.
|   |
|   +-- Interpreter/            - Untyped CFGs (like "Compiler" but without judgments).
|   |
|   +-- Judgment/               - Datastructure and utilities for talking about sets of
|   |                             FORA values.
|   |
|   +-- JudgmentOnInterpreterTrace/ - Datastructure and utilites for describing a
|   |                                 partial trace of a FORA program.
|   |
|   +-- Language/       - Utilites for the FORA language, which eventually boils down
|   |                     to "CFG"
|   |
|   +-- Native/         - Native code model (basically C with continuations and multiple
|   |   |                 function entry/exit points).
|   |   |
|   |   +-- NativeCFGTransforms/ - Transforms on NativeCode
|   |
|   |
|   +-- Primitives/ - C++ implementations of things like fora String, DateTime, etc.
|   |
|   +-- python/ - infrastructure for setup and invocation of the compiler from python
|   |   |
|   |   +-- Evaluator/  - Abstraction for evaluating FORA code. Can be local or remote.
|   |   |                 The LocalEvaluator will eventually go away.
|   |   |
|   |   +-- PurePython/ - implementation of the server side of pyfora
|   |
|   +-- Serialization/ - code to serialize FORA objects
|   |
|   +-- test/ - fora language tests
|   |
|   +-- TypedFora/ - an expression language where all values have a "judgment" on them.
|   |   |            So no ambiguity about operational semantics.
|   |   |
|   |   +-- ABI/     - machine code implementation of Vector and Tuple interactions.
|   |   |              Defines the expectations that the runtime and compiled code have
|   |   |              about each other for Vectors (and some tuple stuff).
|   |   |
|   |   +-- JitCompiler/ - wrapper around a bunch of Native code compilers.
|   |   |                  Allows us to compiler TypedFora into actual entrypoints for
|   |   |                  the interpreter.
|   |   |
|   |   +-- Transforms/  - manipulate TypedFora objects
|   |   |
|   |   TypedFora.hppml - the typed fora expression language.
|   |
|   +-- Vector/         - support structures for "Vector" which is the Ufora large
|   |                     dataset abstraction
|   |
|   +-- VectorDataManager/   - memory management for running FORA compiler processes.
|   |
|   +-- wrappers/            - infrastructure for calling Fortran code
|
+-- native/     - the python module that wraps the entire Ufora codebase and hoists
|                 it into python
|
+-- networking/ - some channel and socket infrastructure in c++/python
|
+-- scripts/    - utility scripts (e.g. bash, python) for various tasks
|
+-- test/       - support for our test infrastructure
|
+-- util/       - grab-bag of python utilities. should probably get merged into `core`
|                 and both renamed
|
+-- web/
|   +-- relay/ - the socket.io relay (connects socket.io to the BackendGateway
|   |            C++/python process)
```
