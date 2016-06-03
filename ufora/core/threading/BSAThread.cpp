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
#include "../Platform.hpp"
#include "../Exception.hpp"
#include <string.h>

#include "BSAThread.hpp"

#if defined(BSA_PLATFORM_LINUX) || defined(BSA_PLATFORM_APPLE)

#include <pthread.h>
#include <boost/scoped_ptr.hpp>


namespace {

	struct PthreadAttrs {
		pthread_attr_t data;
		PthreadAttrs() {
			int err = pthread_attr_init(&data);
			if (err) throw Ufora::Exception("couldn't init pthread attributes");
		}
		~PthreadAttrs() {
			pthread_attr_destroy(&data);
		}
	};

	extern "C" {
		static void* callThreadFunc(void* inThreadFuncPtr) {
			boost::scoped_ptr<Ufora::thread::detail::ThreadFunc>
				f(static_cast<Ufora::thread::detail::ThreadFunc*>(inThreadFuncPtr));
			f->call();

			return 0;
		}
	}
} // end anonymous namespace



namespace Ufora {
    namespace thread {

        void joinThread(BsaThreadData threadData)
            {
            int errnum;

            if ((errnum = pthread_join(threadData.pthreadIdentifier, NULL)) != 0)
                {
                #ifdef BSA_PLATFORM_APPLE
                throw Ufora::Exception("could not join pthread!");
                #else
                throw Ufora::Exception("could not join pthread: " + std::string(strerror(errnum)));
                #endif
                }
            }


        bool currentlyOnThread(BsaThreadData threadData)
            {
            return pthread_equal(threadData.pthreadIdentifier, pthread_self());
            }

        namespace detail {
            BsaThreadData spawnThread(std::auto_ptr<ThreadFunc> inFunc, size_t inStackSize)
                {
                PthreadAttrs attrs;
                int err = pthread_attr_setstacksize(&attrs.data, inStackSize);
                if (err) throw Ufora::Exception("couldn't set pthread stack size");

                pthread_t newThreadId;
                ThreadFunc* theFunc = inFunc.release();
                // the thread takes ownership of the newly-allocated function...
                err = pthread_create(&newThreadId, &attrs.data, callThreadFunc,
                                     static_cast<void*>(theFunc));
                if (err)
                    {
                    // ...unless it doesn't:
                    delete theFunc;
                    throw Ufora::Exception("could not start pthread");
                    }
                BsaThreadData tr = {newThreadId};
                return tr;
                }

            void spawnAndDetach(std::auto_ptr<ThreadFunc> inFunc,
                                                     size_t inStackSize)
                {
                BsaThreadData threadData(spawnThread(inFunc, inStackSize));
                int err = pthread_detach(threadData.pthreadIdentifier);
                if (err)
                    throw Ufora::Exception("could not detach pthread");
                }


        } // detail
    } //thread
} //Ufora

#elif defined(BSA_PLATFORM_WINDOWS)

#include <boost/thread.hpp>

namespace Ufora { namespace thread { namespace detail {

class ThreadFuncCaller {
public:
		ThreadFuncCaller(std::auto_ptr<ThreadFunc>& tf) : m(tf.release())
			{
			}
		void operator()()
			{
			m->call();
			}

private:
		std::auto_ptr<ThreadFunc> m;
};

void spawnAndDetach(std::auto_ptr<ThreadFunc> inFunc,
										 size_t inStackSize)
	{
	//TODO BUG ronen: we're not implementing this correctly. Do you know the Win32 thread API?

	//for now, just use boost threads
	new boost::thread(ThreadFuncCaller(inFunc));
	}


bool currentlyOnThread(BsaThreadData)
    {
    //not implemented in windows yet
    lassert(false);
    }

}
}
}

#endif

