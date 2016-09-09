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
#include "IQueueProtocol.hpp"

IQueueProtocol::IQueueProtocol(Queue<std::string>& inQueue) :
    mQueue(inQueue),
    mCurrentString(""),
    mBytesReadFromCurrentString(0)
    {
    }

uword_t IQueueProtocol::read(uword_t inByteCount, void *inData, bool inBlock)
    {
    uword_t totalBytesRead = 0;
    while (totalBytesRead < inByteCount)
        {
        if (mCurrentString.size() && mBytesReadFromCurrentString < mCurrentString.size())
            {
            const void* sourcePtr = static_cast<const void *>(mCurrentString.data() + mBytesReadFromCurrentString);
            size_t bytesToRead = std::min(inByteCount - totalBytesRead, mCurrentString.size() - mBytesReadFromCurrentString);
            void * destPtr = static_cast<void*>(static_cast<char*>(inData) + totalBytesRead);
            memcpy(destPtr, sourcePtr, bytesToRead);
            mBytesReadFromCurrentString += bytesToRead;
            totalBytesRead += bytesToRead;
            mPosition += bytesToRead;
            }
        else
            {
            if(inBlock)
                mCurrentString = mQueue.get();
            else if (!mQueue.get(mCurrentString))
                return totalBytesRead;
            mBytesReadFromCurrentString = 0;
            }
        }
    return totalBytesRead;
    }

uword_t IQueueProtocol::position()
    {
    return mPosition;
    }


