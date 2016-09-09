
# CPPML

CPPML is a simple overlay on top of C++ syntax that creates a concise
syntax to mimic the typing and pattern matching found in ML based languages.
In ocaml, we might write

	type list = Nil | Node of int * list;

in CPPML,

	@type List = Nil of () -| Node of int, List;

In particular, this syntax makes it easy to create simple tuples or tagged union
types. These classes expose simple interfaces that can be manipulated by cppml
"match" statements, and also expose template metadata that makes it possible
to automatically generate constructs such as serializers, python wrappers,
and arbitrary tree transformations.

CPPML consists of a program "cppml" which takes C++ code that has already
been passed through a preprocessor and expands CPPML language extensions back
into regular C++ code ready to be fed back into a compiler.

## Running CPPML

CPPML is written in OCaml, so you need OCaml installed.

Run "make cppml" to build the cppml binary.

Run "make test" to build the test app out of test.cppml as a simple example,
and "./test" to run it. Check out test.cppml to see some example code.


## Language Examples

The extension @type allows us to easily declare tuples and tagged union types.
For instance, to declare a type T1 which is a tuple of int and int, we write

	@type T1 = int, int;

The tuple elements are accessible as getM1() and getM2() when they're not named.
We can, however, give them names:

	@type T1 = int a, int b;

the elements are accessible as a() and b(), as well as getM1() and getM2(). Then
we can write

	T1 t(1,2);
	assert(t.a() + t.b() == 3);

Any type declared this way can be given a body to expose member functions

	@type T1 = int a, int b {
	public:
		int sum(void) const { return a() + b(); };
	};

Simple pattern matching can take apart a tuple and bind the tuple elements
to variables in the subpattern. for instance, we can sum the elements of the
tuple like this:

	@match T1(t) -| (x,y) ->> {
		return x + y;
		};

here's what these pieces are:

	-|				 indicates a term in a match. like | in ocaml matching
	(x,y)  		 	 the pattern to match. decomposes the tuple and binds
						x and y to the members of the tuple
	->> 			 indicates the pattern is over, time to have a result
	{ return x+y; }  predicate. "x" is a reference to the first element
			        	of the tuple, "y" is a reference to the second element
						result gets passed back

We can also generate tagged unions. For instance, in

	@type T2 =
		Tag1 of int, int
	-| 	Tag2 of string, string;


An element of type T2 is either a "Tag1" with a pair of ints, or a "Tag2" with
a pair of strings. in ocaml we would have written

	type T2 = Tag1 of int * int | Tag2 of string * string

The resulting union is stored as a pointer to a block of memory containing
the tag, a refcount, and the data of the tuple represented by the tag. GC is
done using the refcount.

Instances of the tagged union are created using a static member function. In
this case, T2::Tag1 and T2::Tag2.

	T2 aTag1Object = T2::Tag1(1,2);
	T2 aTag2Object = T2::Tag2("hello", "world");

are equivalent to ocaml code

	let aTag1Object = Tag1(1,2);
	let aTag2Object = Tag2("hello", "world");

We can query a tagged union rather without using the pattern matching:

	//we can find out which tag we have:
	assert(aTag1Object.isTag1());
	assert(!aTag1Object.isTag2());

we can also get the tag1 object out as a tuple and query it. The parser generates
"getX" and "isX" functions for every possible tag. "getX" functions don't check
what kind of object you have to reduce overhead, so be careful. Use @match
to be sure.

	assert(aTag1Object.getTag1().getM1() == 1);

We support pattern matching on tagged unions like ocaml has using @match:

	@match T2(aTag1Object)
		-|	Tag1(a,b) ->> {
			return "was a tag1 with integers...";
			}
		-|	Tag2(a,b) ->> {
			return "was a tag2 with " + a + b;
			}

In this case, we match the first line if "aTag1Object" is an object with tag Tag1
or the second line otherwise. Patterns can be arbitrarily complicated trees.
If the set of matches doen't match the result the operation throws an exception.
For instance, this would throw T2::MatchError:

	@match T2(aTag1Object)
		-|	Tag2(a,b) ->> {
			return "not going to match";
			}

we can get around this by writing

	@match T2(aTag1Object)
		-|	Tag2(a,b) ->> {
			return "not going to match";
			}
		-|	_ ->> {
			"matches anything and throws away the result";
			}

since "_" matches anything and doesn't bind the variable. 

Note that matching doesn't insist that we consume all the match terms. So,
even though all Tag2 objects have two members, the following will work:

	@match T2(aTag1Object)
		-| Tag2(a) ->> { ... }

Of course the power of this sort of typing comes when you make the types
refer to themselves. Here's the definition of a list of integers, defined in
ocaml as

	type list = Nil | Node of int*list;

and in CPPML as

	@type List =
		Nil of ()					// empty tag denoted by "()"
	-|	Node of int, List
		;

	//make a list
	List nil = List::Nil();

	//create a list with "10" in it. two ways to do it
	List withOneThing = List::Node(10, nil);

	//operators are more conscise than constructors. these are equivalent:
	List withSeveralThings = List::Node(1, List::Node(2, List::Node(3, nil)));

We can sum a list using recursion and pattern matching. Unlike OCaml,
c++ compilers will usually not turn the tail recursion into a loop.

	int sumList(List l)
		{
		@match List(l)
			-|	Nil()	->> {
				return  0;
				}
			-|	Node(head,tail) ->> {
				return head + sumList(tail);
				}
		}

A non-recursive loop would look like this

	int sumListLoop(List l)
		{
		int result = 0;
		while (true)
			{
			@match List(l) 
				-| Nil() ->> { return result; }
				-| Node(head, tail) ->>  { 
					result += head;
					l = tail;
					}
			}
		}

We can define several types that refer to each other at once

	@type T1 =
			Tag1 of int
		-| 	Tag2 of T2
	and T2 =
			Tag3 of int
		-|	Tag4 of T1;

And we also support templates

	template <class T>
	@type ListT = 		
		-|	Nil of ()
		-| 	Node of T head, ListT<T> tail
	{
	public:
		T sum(void) const
			{
			@match self_type(*this)
				-| Nil() ->> { return T(); }
				-| Node(head,tail) ->> { return head + tail.sum(); }
			}
	};

	List<int>::Node(10, List<int>::Nil());

## COMMON DATA

We allow clients to define "common" data members that exist for all alternatives of a tagged union.

As an example,

	@type Alt =
		-|	Option1 of string val
		-|	Option2 of double val
	with
		int commonInteger
		;

"commonInteger" is now defined for both alternatives.  Constructors are

	Alt::Option1(int, string)
	Alt::Option2(int, double)

to reflect the new value. the common value can be extracted as

	Alt a;
	...
	a.commonInteger()

without having to use a pattern match.  The value is available in the pattern match. For instance

	Alt a;
	...
	@match Alt(a)
		-|	Option1(val) with (ci) ->> {
			return  ...;
			}
		;

is valid.  values placed in the "with' clause are full pattern matchers

## MEMOIZATION

We also support adding common memo-values to tagged union.  These values are computed
once, on demand, the first time they are accessed.  As an example

	@type Alt =
		-|	Option1 of float val
		-|	Option2 of double val
	with
		double square = (this->computeSquare())
	{
	public:
		double computeSquare()
			{
			@match Alt(*this) 
				-| Option1(val) ->> { return val*val; }
				-| Option2(val) ->> { return val*val; }
			}
	};

"square", when accessed, is computed once and then cached. This is particularly useful for caching hashes of constant objects.

If a memo-function on a given instance calls back into itself (indicating that it would cycle forever), it throws an exception.

