/***************************************************************************
   Copyright 2015 Ufora Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
****************************************************************************/
#include "StringCodegen.hppml"
#include "NativeCodeCompilerTestFixture.hpp"
#include "../../Primitives/String.hppml"
#include "../../Primitives/StringImpl.hppml"
#include "../../Core/ExecutionContextMemoryPool.hppml"
#include "../../../core/UnitTest.hpp"

using namespace TypedFora::Abi;

class StringCodegenTestFixture :
    public NativeCodeCompilerTestFixture
    {
public:
    StringCodegenTestFixture()
        {
        }

    typedef TypedNativeExpression<String> expression_type;

    };

BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_StringCodegen,
    StringCodegenTestFixture )

BOOST_AUTO_TEST_CASE( test_string_size_codegen )
    {
    MemoryPool* freePool = MemoryPool::getFreeStorePool();

    String packedString("asdf", freePool);

    BOOST_CHECK(
        compile(&expression_type::size)(packedString) == packedString.size()
        );

    String nonpackedString(
        "mary had a little lamb its coat as white as snow",
        freePool
        );

    BOOST_CHECK(
        compile(&expression_type::size)(nonpackedString) == nonpackedString.size()
        );
    }

BOOST_AUTO_TEST_SUITE_END()

