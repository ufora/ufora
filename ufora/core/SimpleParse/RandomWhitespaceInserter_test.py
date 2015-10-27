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

import unittest
import ufora.native.FORA as ForaNative
import logging

class TestRandomWhitespaceInserter(unittest.TestCase):
    def test_1(self):
        toParse = """
let fun1 = 
    fun(row) { 
        // the match does seem necessary here
        match (row) with 
            (...) {
            return row 
            }
    };

let fun2 = 
    fun() {
        
        // TP: the following is just some crap designed to take a few seconds to run
        // so that we can see that recomputes are actually happening 
        // (takes me about 3 sec on my machine with 8 cores in local sim)
        let doSomethingExpensive = fun() {
            let tr = nothing;        
            for ix in sequence(40000001)
                {
                logging.log(ix)
                if (ix % 3 == 0)
                    tr = tr + Float64(math.log(math.log(ix + 1) + 1))
                else if (ix % 3 == 1)
                    tr = tr + Int64(math.log(math.log(ix + 1) + 1))
                else 
                    tr = tr + Int32(math.log(math.log(ix + 1) + 1))
                }
            return tr
            }
        return doSomethingExpensive()
        
        fun1() // definitely necessary
        };
    
fun2"""
        simpleParse1 = ForaNative.SimpleParseNode.parse(toParse)
        
        whitespaceInserter = ForaNative.RandomWhitespaceInserter(1337)

        withWhitespace = \
            whitespaceInserter.stringifyWithRandomWhitespaceAndComments(simpleParse1)
        
        simpleParse2 = ForaNative.SimpleParseNode.parse(withWhitespace)

        self.assertEqual(str(simpleParse1), str(simpleParse2))

        withWhitespace2 = \
            whitespaceInserter.stringifyWithRandomWhitespaceAndComments(simpleParse2)

        self.assertNotEqual(withWhitespace2, withWhitespace)

        simpleParse2 = ForaNative.SimpleParseNode.parse(withWhitespace2)

        self.assertEqual(str(simpleParse1), str(simpleParse2))

                

