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

#include "../../../core/PolymorphicSharedPtr.hpp"
#include "../../../core/math/Nullable.hpp"

class Expression;
class PatternWithName;
class ImplValContainer;
class VectorDataManager;

template<class T>
class ImmutableTreeVector;

namespace Fora {
class PythonAstExpr;
class PythonAstExpr_ListType;
class PythonAstExpr_ListCompType;
}

namespace Fora {

class PythonListConverter:
        public PolymorphicSharedPtrBase<PythonListConverter> {
public:
    virtual Expression convertPyList(
        const Fora::PythonAstExpr_ListType& listExpr,
        const std::function<Expression(const PythonAstExpr&)>& 
            convertPythonAstExpressionToFora
        ) const = 0;

    virtual Expression concatSingleEltVectorExpr(
        const Expression& lhs,
        const Expression& eltInVector
        ) const = 0;

    virtual Expression convertPyListComprehension(
        const Fora::PythonAstExpr_ListCompType& listCompExpr,
        const std::function<Expression(const PythonAstExpr&)>& 
            convertPythonAstExpressionToFora,
        const std::function<PatternWithName(const PythonAstExpr&)>&
            convertPythonAstExpressionToPattern
        ) const = 0;

    virtual ImplValContainer createList(
        const ImmutableTreeVector<ImplValContainer>& listElements,
        PolymorphicSharedPtr<VectorDataManager> vdm
        ) const;

    //if this is a tuple, extract a Vector containing its elements
    virtual Nullable<ImplValContainer> invertList(ImplValContainer possibleList) = 0;

    virtual ~PythonListConverter() {}
};

}

