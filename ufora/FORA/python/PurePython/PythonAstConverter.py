#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import ast
import ufora.native.FORA as ForaNative

PythonAstModule = ForaNative.PythonAstModule
PythonAstStatement = ForaNative.PythonAstStatement
PythonAstExpr = ForaNative.PythonAstExpr
PythonAstExprContext = ForaNative.PythonAstExprContext
PythonAstSlice = ForaNative.PythonAstSlice
PythonAstBooleanOp = ForaNative.PythonAstBooleanOp
PythonAstBinaryOp = ForaNative.PythonAstBinaryOp
PythonAstUnaryOp = ForaNative.PythonAstUnaryOp
PythonAstComparisonOp = ForaNative.PythonAstComparisonOp
PythonAstComprehension = ForaNative.PythonAstComprehension
PythonAstExceptionHandler = ForaNative.PythonAstExceptionHandler
PythonAstArguments = ForaNative.PythonAstArguments
PythonAstKeyword = ForaNative.PythonAstKeyword
PythonAstAlias = ForaNative.PythonAstAlias
PythonAstNumericConstant = ForaNative.PythonAstNumericConstant

numericConverters = {
    int: PythonAstNumericConstant.Int,
    bool: PythonAstNumericConstant.Boolean,
    long: lambda x: PythonAstNumericConstant.Long(str(x)),
    type(None): lambda x: PythonAstNumericConstant.None(),
    float: PythonAstNumericConstant.Float
    }

def createPythonAstConstant(c):
    try:
        if type(c) not in numericConverters:
            return PythonAstExpr.Num(PythonAstNumericConstant.Unknown())
        return PythonAstExpr.Num(numericConverters[type(c)](c))
    except Exception as e:
        print e, c, type(c)
        raise

def createPythonAstString(s):
    #WARNING: this code deliberately discards unicode information
    try:
        return PythonAstExpr.Str(str(s))
    except:
        return PythonAstExpr.Num(PythonAstNumericConstant.Unknown())

converters = {
    ast.Module: PythonAstModule.Module,
    ast.Expression: PythonAstModule.Expression,
    ast.Interactive: PythonAstModule.Interactive,
    ast.Suite: PythonAstModule.Suite,
    ast.FunctionDef: PythonAstStatement.FunctionDef,
    ast.ClassDef: PythonAstStatement.ClassDef,
    ast.Return: PythonAstStatement.Return,
    ast.Delete: PythonAstStatement.Delete,
    ast.Assign: PythonAstStatement.Assign,
    ast.AugAssign: PythonAstStatement.AugAssign,
    ast.Print: PythonAstStatement.Print,
    ast.For: PythonAstStatement.For,
    ast.While: PythonAstStatement.While,
    ast.If: PythonAstStatement.If,
    ast.With: PythonAstStatement.With,
    ast.Raise: PythonAstStatement.Raise,
    ast.TryExcept: PythonAstStatement.TryExcept,
    ast.TryFinally: PythonAstStatement.TryFinally,
    ast.Assert: PythonAstStatement.Assert,
    ast.Import: PythonAstStatement.Import,
    ast.ImportFrom: PythonAstStatement.ImportFrom,
    ast.Exec: PythonAstStatement.Exec,
    ast.Global: PythonAstStatement.Global,
    ast.Expr: PythonAstStatement.Expr,
    ast.Pass: PythonAstStatement.Pass,
    ast.Break: PythonAstStatement.Break,
    ast.Continue: PythonAstStatement.Continue,
    ast.BoolOp: PythonAstExpr.BoolOp,
    ast.BinOp: PythonAstExpr.BinOp,
    ast.UnaryOp: PythonAstExpr.UnaryOp,
    ast.Lambda: PythonAstExpr.Lambda,
    ast.IfExp: PythonAstExpr.IfExp,
    ast.Dict: PythonAstExpr.Dict,
    ast.Set: PythonAstExpr.Set,
    ast.ListComp: PythonAstExpr.ListComp,
    ast.SetComp: PythonAstExpr.SetComp,
    ast.DictComp: PythonAstExpr.DictComp,
    ast.GeneratorExp: PythonAstExpr.GeneratorExp,
    ast.Yield: PythonAstExpr.Yield,
    ast.Compare: PythonAstExpr.Compare,
    ast.Call: PythonAstExpr.Call,
    ast.Repr: PythonAstExpr.Repr,
    ast.Num: createPythonAstConstant,
    ast.Str: createPythonAstString,
    ast.Attribute: PythonAstExpr.Attribute,
    ast.Subscript: PythonAstExpr.Subscript,
    ast.Name: PythonAstExpr.Name,
    ast.List: PythonAstExpr.List,
    ast.Tuple: PythonAstExpr.Tuple,
    ast.Load: PythonAstExprContext.Load,
    ast.Store: PythonAstExprContext.Store,
    ast.Del: PythonAstExprContext.Del,
    ast.AugLoad: PythonAstExprContext.AugLoad,
    ast.AugStore: PythonAstExprContext.AugStore,
    ast.Param: PythonAstExprContext.Param,
    ast.Ellipsis: PythonAstSlice.Ellipsis,
    ast.Slice: PythonAstSlice.Slice,
    ast.ExtSlice: PythonAstSlice.ExtSlice,
    ast.Index: PythonAstSlice.Index,
    ast.And: PythonAstBooleanOp.And,
    ast.Or: PythonAstBooleanOp.Or,
    ast.Add: PythonAstBinaryOp.Add,
    ast.Sub: PythonAstBinaryOp.Sub,
    ast.Mult: PythonAstBinaryOp.Mult,
    ast.Div: PythonAstBinaryOp.Div,
    ast.Mod: PythonAstBinaryOp.Mod,
    ast.Pow: PythonAstBinaryOp.Pow,
    ast.LShift: PythonAstBinaryOp.LShift,
    ast.RShift: PythonAstBinaryOp.RShift,
    ast.BitOr: PythonAstBinaryOp.BitOr,
    ast.BitXor: PythonAstBinaryOp.BitXor,
    ast.BitAnd: PythonAstBinaryOp.BitAnd,
    ast.FloorDiv: PythonAstBinaryOp.FloorDiv,
    ast.Invert: PythonAstUnaryOp.Invert,
    ast.Not: PythonAstUnaryOp.Not,
    ast.UAdd: PythonAstUnaryOp.UAdd,
    ast.USub: PythonAstUnaryOp.USub,
    ast.Eq: PythonAstComparisonOp.Eq,
    ast.NotEq: PythonAstComparisonOp.NotEq,
    ast.Lt: PythonAstComparisonOp.Lt,
    ast.LtE: PythonAstComparisonOp.LtE,
    ast.Gt: PythonAstComparisonOp.Gt,
    ast.GtE: PythonAstComparisonOp.GtE,
    ast.Is: PythonAstComparisonOp.Is,
    ast.IsNot: PythonAstComparisonOp.IsNot,
    ast.In: PythonAstComparisonOp.In,
    ast.NotIn: PythonAstComparisonOp.NotIn,
    ast.comprehension: PythonAstComprehension,
    ast.excepthandler: lambda x:x,
    ast.ExceptHandler: PythonAstExceptionHandler,
    ast.arguments: PythonAstArguments,
    ast.keyword: PythonAstKeyword,
    ast.alias: PythonAstAlias
    }


def convertPythonAstToForaPythonAst(tree, lineOffsets):
    if issubclass(type(tree), ast.AST):
        converter = converters[type(tree)]
        args = []

        for f in tree._fields:
            args.append(
                convertPythonAstToForaPythonAst(
                    getattr(tree, f),
                    lineOffsets
                    )
                )
        try:
            result = converter(*args)
            if isinstance(result, (PythonAstExpr, PythonAstStatement)):
                charOffset = tree.col_offset - 1 + lineOffsets[tree.lineno - 1]
                result = result.withParseInfo(
                    charOffset,
                    tree.lineno,
                    tree.col_offset
                    )
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise UserWarning("Failed to construct %s with arguments %s" % (type(tree), args))
    if isinstance(tree, list):
        return [convertPythonAstToForaPythonAst(x, lineOffsets) for x in tree]
    return tree


def computeLineOffsets(text):
    lineOffsets = [0]
    for line in text.split("\n"):
        lineOffsets.append(lineOffsets[-1] + len(line) + 1)
    return lineOffsets

astCache_ = {}
def parseStringToPythonAst(text):
    lineOffsets = computeLineOffsets(text)
    try:
        pyAst = astCache_.get(text)
        if pyAst is None:
            pyAst = astCache_[text] = convertPythonAstToForaPythonAst(ast.parse(text), lineOffsets)
        return pyAst
    except SyntaxError as e:
        return ForaNative.PythonParseError(e.msg,
                                           e.filename,
                                           e.lineno,
                                           e.offset,
                                           e.text)
    except TypeError as e:
        return ForaNative.PythonParseError(str(e.message))




