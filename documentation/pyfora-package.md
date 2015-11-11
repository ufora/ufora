---
layout: main
title: The pyfora Package
tagline: Reference Manual
sort_index: 03
---


# pyfora - The Ufora Client

Use the `pyfora` module to connect and submit computations to a Ufora cluster.
The `pyfora` module exposes two programming models for interacting with a remote cluster:

1. A low-level async interface based on [`concurrent.futures`](http://pythonhosted.org/futures/)
2. A higher-level synchroneous API encapsulated in a Python `with` block

In both cases 

## connect

