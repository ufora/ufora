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
#include "Logging.hpp"
#include "ScopedLoggingHandles.hppml"
#include "UnitTest.hpp"

using namespace Ufora;

BOOST_AUTO_TEST_SUITE( test_ScopedLoggingHandles )

BOOST_AUTO_TEST_CASE( test_basic )
	{
	LogLevel globalLevel;

	ScopedLoggingHandles handles(&globalLevel);

	LogLevel** aHandle = handles.getHandle(ScopedLoggingEntry("scope", "file"));

	BOOST_CHECK(aHandle);
	BOOST_CHECK(*aHandle == &globalLevel);
	}

BOOST_AUTO_TEST_CASE( test_overrides )
	{
	LogLevel globalLevel = LOG_LEVEL_INFO;

	ScopedLoggingHandles handles(&globalLevel);

	LogLevel** aHandle11 = handles.getHandle(ScopedLoggingEntry("scope1", "file1"));
	LogLevel** aHandle12 = handles.getHandle(ScopedLoggingEntry("scope1", "file2"));
	LogLevel** aHandle21 = handles.getHandle(ScopedLoggingEntry("scope2", "file1"));
	LogLevel** aHandle22 = handles.getHandle(ScopedLoggingEntry("scope2", "file2"));

	BOOST_CHECK(aHandle11);
	BOOST_CHECK(aHandle12);
	BOOST_CHECK(aHandle21);
	BOOST_CHECK(aHandle22);
	BOOST_CHECK(**aHandle11 == LOG_LEVEL_INFO);
	BOOST_CHECK(**aHandle12 == LOG_LEVEL_INFO);
	BOOST_CHECK(**aHandle21 == LOG_LEVEL_INFO);
	BOOST_CHECK(**aHandle22 == LOG_LEVEL_INFO);

	//verify we can override by filename
	handles.addPattern(ScopedLoggingEntry(".*", "file1"), null() << LOG_LEVEL_WARN);

	BOOST_CHECK(**aHandle11 == LOG_LEVEL_WARN);
	BOOST_CHECK(**aHandle12 == LOG_LEVEL_INFO);
	BOOST_CHECK(**aHandle21 == LOG_LEVEL_WARN);
	BOOST_CHECK(**aHandle22 == LOG_LEVEL_INFO);

	//verify we can override separately by scope
	handles.addPattern(ScopedLoggingEntry("scope1", ".*"), null() << LOG_LEVEL_ERROR);

	BOOST_CHECK(**aHandle11 == LOG_LEVEL_ERROR);
	BOOST_CHECK(**aHandle12 == LOG_LEVEL_ERROR);
	BOOST_CHECK(**aHandle21 == LOG_LEVEL_WARN);
	BOOST_CHECK(**aHandle22 == LOG_LEVEL_INFO);
	
	//verify that a new pattern will have the appropriate level
	LogLevel** aHandle13 = handles.getHandle(ScopedLoggingEntry("scope1", "file3"));
	LogLevel** aHandle31 = handles.getHandle(ScopedLoggingEntry("scope3", "file1"));
	BOOST_CHECK(**aHandle31 == LOG_LEVEL_WARN);
	BOOST_CHECK(**aHandle13 == LOG_LEVEL_ERROR);
	
	//verify we can override everything back to what it was
	handles.addPattern(ScopedLoggingEntry(".*", ".*"), null());

	BOOST_CHECK(**aHandle11 == LOG_LEVEL_INFO);
	BOOST_CHECK(**aHandle12 == LOG_LEVEL_INFO);
	BOOST_CHECK(**aHandle21 == LOG_LEVEL_INFO);
	BOOST_CHECK(**aHandle22 == LOG_LEVEL_INFO);

	//and that it's actually connected to the global level
	globalLevel = LOG_LEVEL_CRITICAL;

	BOOST_CHECK(**aHandle11 == LOG_LEVEL_CRITICAL);
	BOOST_CHECK(**aHandle12 == LOG_LEVEL_CRITICAL);
	BOOST_CHECK(**aHandle22 == LOG_LEVEL_CRITICAL);
	BOOST_CHECK(**aHandle21 == LOG_LEVEL_CRITICAL);
	}

BOOST_AUTO_TEST_SUITE_END()
