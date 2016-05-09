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
#ifndef INCLUDED_BSAThread_hpp
#define INCLUDED_BSAThread_hpp

#include <memory> // for auto_ptr, used internally
#include <stdlib.h>
#include <pthread.h>

namespace Ufora {
	namespace thread {

        #if defined(BSA_PLATFORM_LINUX) || defined(BSA_PLATFORM_APPLE)
        struct BsaThreadData {
            pthread_t           pthreadIdentifier;
            };
        #else
        struct BsaThreadData {
            };
        #endif


		namespace detail {
			struct ThreadFunc {
				virtual ~ThreadFunc() {}
				virtual void call() = 0;
			};
			template<typename FuncT>
			struct TemplatedThreadFunc : public ThreadFunc {
				FuncT mFunc;
				explicit TemplatedThreadFunc(FuncT f) : mFunc(f) {}
				void call() { mFunc(); }
			};
			void spawnAndDetach(std::auto_ptr<ThreadFunc>, size_t inStackSize);
			BsaThreadData spawnThread(std::auto_ptr<ThreadFunc>, size_t inStackSize);
		}

		// Run a function in a raw pthread with a given stack size.
		// Note that whether the resulting thread plays well in a
		// boost::thread environment is undefined.
		// Explicit specification of stack sizes is discouraged, as is
		// all use of this function. All such usages should be considered
		// deprecated. -rob 2011-08-26

        void joinThread(BsaThreadData);

        bool currentlyOnThread(BsaThreadData);

		template<typename FuncT>
		void spawnAndDetach(FuncT f, size_t inStackSize) {
			detail::spawnAndDetach(
				std::auto_ptr<detail::ThreadFunc>
					(new detail::TemplatedThreadFunc<FuncT>(f)),
				inStackSize
			);
        }

		template<typename FuncT>
		BsaThreadData spawnThread(FuncT f, size_t inStackSize) {
			return detail::spawnThread(
				std::auto_ptr<detail::ThreadFunc>
					(new detail::TemplatedThreadFunc<FuncT>(f)),
				inStackSize
			);
		}
	}
}

#endif

