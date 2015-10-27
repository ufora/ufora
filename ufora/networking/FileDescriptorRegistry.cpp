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
#include "FileDescriptorRegistry.hpp"
#include "../core/Logging.hpp"
#include "../core/lassert.hpp"

bool ScopedFileDescriptorRegisterer::FileDescriptorRegistry::acquireFd(uint32_t fd, uint32_t inMaxRegistrationCount)
        {
        boost::recursive_mutex::scoped_lock lock(mMutex);
        auto it = mFdMap.find(fd);
        if (it == mFdMap.end())
            it = mFdMap.insert(std::make_pair(fd, RegistrationInformation(inMaxRegistrationCount, 0 ))).first;
        else
            lassert(it->second.mMaxRegistrationCount == inMaxRegistrationCount);

        if (it->second.mCurrentRegistrationCount == it->second.mMaxRegistrationCount)
            {
            LOG_WARN << "fd " << it->first << " has already been registered " << it->second.mCurrentRegistrationCount << " times " << std::endl;
            return false;
            }

        it->second.mCurrentRegistrationCount++;
        return true;
        }

void ScopedFileDescriptorRegisterer::FileDescriptorRegistry::releaseFd(uint32_t fd)
    {
    boost::recursive_mutex::scoped_lock lock(mMutex);
    auto it = mFdMap.find(fd);
    lassert(it != mFdMap.end());
    it->second.mCurrentRegistrationCount--;
    if(it->second.mCurrentRegistrationCount == 0)
        mFdMap.erase(it);
    }

ScopedFileDescriptorRegisterer::ScopedFileDescriptorRegisterer(uint32_t inFileDescriptor, uint32_t inMaxRegistrationCount) :
    mFileDescriptor(inFileDescriptor),
    mAcquired(false)
    {
    mAcquired = FileDescriptorRegistry::getRegistrySingleton().acquireFd(inFileDescriptor, inMaxRegistrationCount);
    }

ScopedFileDescriptorRegisterer::FileDescriptorRegistry::FileDescriptorRegistry(){}

ScopedFileDescriptorRegisterer::~ScopedFileDescriptorRegisterer()
    {
    if(mAcquired)
        FileDescriptorRegistry::getRegistrySingleton().releaseFd(mFileDescriptor);
    }

bool ScopedFileDescriptorRegisterer::sucessfullyRegistered(void)
    {
    return mAcquired;
    }

ScopedFileDescriptorRegisterer::FileDescriptorRegistry& ScopedFileDescriptorRegisterer::FileDescriptorRegistry::getRegistrySingleton(void)
    {
    static FileDescriptorRegistry sFileDescriptorRegistry;
    return sFileDescriptorRegistry;
    }

