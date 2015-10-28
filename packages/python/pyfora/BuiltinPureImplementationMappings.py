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

import pyfora.PureImplementationMapping as PureImplementationMapping
import pyfora.PureImplementationMappings as PureImplementationMappings

class Len:
	def __call__(self, other):
		return other.__len__()

class Str:
	def __call__(self, other):
		return other.__str__()

class Range:
    def __call__(self, first, second=None, increment=None):
        start = 0
        stop = 0
        if second == None:
            stop = first
        else:
            start = first
            stop = second

        if increment == None:
            increment = 1
        
        toReturn = []
        currentVal = start

        while currentVal < stop:
            toReturn = toReturn + [currentVal]
            currentVal = currentVal + increment
        return toReturn

class XRange:
    def __call__(self, first, second=None, increment=None):
        # this is some unfortunate code duplication
        # Range() should really return list(xrange())
        # but that isn't converting properly right now
        # --Amichai
        start = 0
        stop = 0
        if second == None:
            stop = first
        else:
            start = first
            stop = second

        if increment == None:
            increment = 1
        
        currentVal = start

        while currentVal < stop:
            yield currentVal
            currentVal = currentVal + increment



class Abs:
    def __call__(self, val):
        return val.__abs__()

class All:
    def __call__(self, iterable):
        if len(iterable) == 0:
            return True
        for i in iterable:
            if not i:
                return False
        return True

class Ord:
    def __init__(self):
        # should be a static attribute
        self.charToASCIIValue = {'\'':39, '(':40, ')':41, '*':42, '+':43, ',':44, '-':45, '.':46, '/':47, '0':48, '1':49, '2':50, '3':51, '4':52, '5':53, '6':54, '7':55, '8':56, '9':57, ':':58, ';':59, '<':60, '=':61, '>':62, '?':63, '@':64, 'A':65, 'B':66, 'C':67, 'D':68, 'E':69, 'F':70, 'G':71, 'H':72, 'I':73, 'J':74, 'K':75, 'L':76, 'M':77, 'N':78, 'O':79, 'P':80, 'Q':81, 'R':82, 'S':83, 'T':84, 'U':85, 'V':86, 'W':87, 'X':88, 'Y':89, 'Z':90, '[':91, '\\':92, ']':93, '^':94, '_':95, '`':96, 'a':97, 'b':98, 'c':99, 'd':100, 'e':101, 'f':102, 'g':103, 'h':104, 'i':105, 'j':106, 'k':107, 'l':108, 'm':109, 'n':110, 'o':111, 'p':112, 'q':113, 'r':114, 's':115, 't':116, 'u':117, 'v':118, 'w':119, 'x':120, 'y':121, 'z':122, '{':123, '|':124, '}':125, '~':126}

    def __call__(self, character):        
        # assert we're getting a character of length 1
        if len(character) != 1:
            raise TypeError("ord() expected a character")
        if not character in self.charToASCIIValue:
            raise ValueError("Unrecognized ascii value")
        return self.charToASCIIValue[character]
        
class Chr:
    def __init__(self):
        # should be a static attribute
        self.ASCIIValueToChar = {40:'(',44:',',48:'0',52:'4',56:'8',60:'<',64:'@',68:'D',72:'H',76:'L',80:'P',84:'T',88:'X',92:'\\',96:'`',100:'d',104:'h',108:'l',112:'p',116:'t',120:'x',124:'|',39:'\'',43:'+',47:'/',51:'3',55:'7',59:';',63:'?',67:'C',71:'G',75:'K',79:'O',83:'S',87:'W',91:'[',95:'_',99:'c',103:'g',107:'k',111:'o',115:'s',119:'w',123:'{',42:'*',46:'.',50:'2',54:'6',58:':',62:'>',66:'B',70:'F',74:'J',78:'N',82:'R',86:'V',90:'Z',94:'^',98:'b',102:'f',106:'j',110:'n',114:'r',118:'v',122:'z',126:'~',41:')',45:'-',49:'1',53:'5',57:'9',61:'=',65:'A',69:'E',73:'I',77:'M',81:'Q',85:'U',89:'Y',93:']',97:'a',101:'e',105:'i',109:'m',113:'q',117:'u',121:'y',125:'}'}
        
    def __call__(self, asciiValue):
        # assert we're getting an integer within the range 40 - 125
        if asciiValue > 125 or asciiValue < 40:
            raise ValueError("chr() arg not in range")

        return self.ASCIIValueToChar[asciiValue]

mappings_ = [(len, Len), (str, Str), (range, Range), (xrange, XRange), (abs, Abs), (all, All), (ord, Ord), (chr, Chr)]

def generateMappings():
	return [PureImplementationMapping.InstanceMapping(instance, pureType) for (instance, pureType) in mappings_]

