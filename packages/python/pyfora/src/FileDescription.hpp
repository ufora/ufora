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

#include <string>


class FileDescription {
public:
    // stub to placate std::map
    FileDescription() {}

    FileDescription(const std::string& filename,
                    const std::string& filetext) :
            filename(filename),
            filetext(filetext)
        {
        }

    FileDescription(const std::pair<std::string, std::string>& filenameAndText) :
            filename(filenameAndText.first),
            filetext(filenameAndText.second)
        {
        }

    static const FileDescription& cachedFromArgs(const std::string& filename,
                                                 const std::string& filetext);

    static const FileDescription& cachedFromArgs(
        const std::pair<std::string, std::string>& filenameAndText)
        {
        return cachedFromArgs(filenameAndText.first, filenameAndText.second);
        }

    std::string filename;
    std::string filetext;
};
