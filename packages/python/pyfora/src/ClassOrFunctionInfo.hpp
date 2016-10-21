/***************************************************************************
   Copyright 2016 Ufora Inc.

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

#include "FreeVariableMemberAccessChain.hpp"

#include <map>
#include <stdint.h>
#include <string>


class ClassOrFunctionInfo {
public:
    ClassOrFunctionInfo(int64_t sourceFileId,
                       int64_t lineNumber,
                       const std::map<FreeVariableMemberAccessChain, int64_t>& chainToId
                       ):
            mSourceFileId(sourceFileId),
            mLineNumber(lineNumber),
            mFreeVariableMemberAccessChainsToId(chainToId)
        {
        }

    int64_t sourceFileId() const {
        return mSourceFileId;
        }
    int64_t lineNumber() const {
        return mLineNumber;
        }
    const std::map<FreeVariableMemberAccessChain, int64_t>&
    freeVariableMemberAccessChainsToId() const {
        return mFreeVariableMemberAccessChainsToId;
        }

private:
    int64_t mSourceFileId;
    int64_t mLineNumber;
    std::map<FreeVariableMemberAccessChain, int64_t> 
        mFreeVariableMemberAccessChainsToId;
    };
