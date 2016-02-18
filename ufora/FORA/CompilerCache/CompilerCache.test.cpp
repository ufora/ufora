#include "CompilerCache.hpp"
#include "../ControlFlowGraph/ControlFlowGraph.hppml"
#include "../Core/ClassMediator.hppml"
#include "../Language/FunctionToCFG.hppml"
#include "../Language/Parser.hppml"
#include "../../core/UnitTest.hpp"


void testCodeCacheWithCodeConvertedFromString(
		const std::string& code,
		const Fora::Language::FunctionToCFG& converter
		)
	{
	const CompilerCache& cache = converter.getCompilerCache();
	Function f = parseStringToFunction(
			code,
			false,
			CodeDefinitionPoint::External(emptyTreeVec()),
			"<eval>");
	ClassMediator cm =
			ClassMediator::Function(
						"",
						f.withFreeAsArgs(),
						LexicalBindingMap(),
						CSTValue()
						);

	ClassMediatorResumption resumption;
	ApplySignature args;

	CompilerMapKey key(resumption.hash(), cm.hash(), args.hash());
	BOOST_CHECK_EQUAL(cache.get(key).isValue(), false);

	ControlFlowGraph cfg = converter.functionToCFG(cm, resumption, args);
	Nullable<ControlFlowGraph> result = cache.get(key);

	BOOST_CHECK(result.isValue());

	BOOST_CHECK(*result==cfg);

	}

BOOST_AUTO_TEST_CASE( test_InMemoryCompilerStore)
	{
	InMemoryCompilerStore memStore;
	DummyCompilerStore dummyStore;

	ClassMediator code;
	ClassMediatorResumption resumption;
	ApplySignature args;

	CompilerMapKey key(resumption.hash(), code.hash(), args.hash());
	auto result = memStore.get(key);
	BOOST_CHECK_EQUAL(result.isValue(), false);

	ControlFlowGraph cfg;
	ControlFlowGraph cfg2;
	BOOST_CHECK(cfg==cfg);

	BOOST_CHECK(cfg==cfg2);

	memStore.set(key, cfg);
	result = memStore.get(key);
	BOOST_CHECK(result.isValue());

	BOOST_CHECK(*result==cfg);

	GenericCompilerCache<InMemoryCompilerStore, DummyCompilerStore> cache(memStore, dummyStore);
	Fora::Language::FunctionToCFG converter(cache);

	testCodeCacheWithCodeConvertedFromString(
			"object{x:10}.x",
			converter
			);

	testCodeCacheWithCodeConvertedFromString(
			"object{x:10; y:20; foo : fun() { x+y; } }.foo()",
			converter
			);


	}

