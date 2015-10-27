all: cppml

clean:
	rm -f *.cmi *.cmo *.cmx *.o *.output *.mli test test_dbg test.cpp
	rm -f lexer.ml parser.ml cppml cppml.tar

cppml: codemodel.ml errs.ml lexer.mll parser.mly run.ml util.ml

	ocamlc -c errs.ml
	ocamlc -c util.ml
	ocamlc str.cma -c codemodel.ml

	ocamllex lexer.mll
	ocamlyacc -v parser.mly

	ocamlc -c parser.mli

	ocamlopt str.cmxa -inline 2 $(addsuffix .cmxa,$(basename $(extras))) util.ml codemodel.ml errs.ml parser.ml lexer.ml run.ml -o cppml

test.cpp_: cppml test.cppml_ preamble.txt
	./cppml test.cppml_ - > test.cpp_

test: cppml test.cpp_
	g++ -std=c++0x -x c++ test.cpp_ -lstdc++ -o test -O3 -g -Iinclude

test_dbg: cppml test.cpp_
	g++ -std=c++0x -x c++ test.cpp_ -lstdc++ -o test_dbg -O0 -g -Iinclude

cppml.tar:
	rm -rf cppml.tar
	tar -cvvf cppml.tar *

.PHONY: all, clean, cppml.tar
