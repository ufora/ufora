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
#pragma once

#include "IProtocol.hpp"
#include "../threading/Queue.hpp"

#include <string>

class IQueueProtocol : public IProtocol {
public:

    IQueueProtocol(Queue<std::string>& inQueue);

    uword_t read(uword_t inByteCount, void *inData, bool inBlock);

    uword_t position();

private:

    std::string mCurrentString;

    size_t mBytesReadFromCurrentString;

    uword_t mPosition;

    Queue<std::string>& mQueue;

};


