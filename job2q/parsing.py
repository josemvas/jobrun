# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from pyparsing import infixNotation, opAssoc, Keyword, Word, alphas, alphanums

class BoolOperand(object):
    def __init__(self, t, context):
        self.label = t[0]
        try:
            self.value = context[t[0]]
        except KeyError as e:
            raise Exception('Undefined BoolOperand context "{0}"'.format(e.args[0]))
    def __bool__(self):
        return self.value
    def __str__(self):
        return self.label
    __repr__ = __str__
    __nonzero__ = __bool__

class BoolBinOp(object):
    def __init__(self, t):
        self.args = t[0][0::2]
    def __str__(self):
        sep = ' %s ' % self.reprsymbol
        return '(' + sep.join(map(str,self.args)) + ')'
    def __bool__(self):
        return self.evalop(bool(a) for a in self.args)
    __nonzero__ = __bool__
    __repr__ = __str__

class BoolAnd(BoolBinOp):
    reprsymbol = '&'
    evalop = all

class BoolOr(BoolBinOp):
    reprsymbol = '|'
    evalop = any

class BoolNot(object):
    def __init__(self, t):
        self.arg = t[0][1]
    def __bool__(self):
        v = bool(self.arg)
        return not v
    def __str__(self):
        return "~" + str(self.arg)
    __repr__ = __str__
    __nonzero__ = __bool__

def parsebool(boolstring, context):
    TRUE = Keyword("True")
    FALSE = Keyword("False")
    boolOperand = TRUE | FALSE | Word(alphas, alphanums + '._-')
    boolOperand.setParseAction(lambda tokens: BoolOperand(tokens, context))
    # define expression, based on expression operand and
    # list of operations in precedence order
    boolExpr = infixNotation( boolOperand, [
        ("not", 1, opAssoc.RIGHT, BoolNot),
        ("and", 2, opAssoc.LEFT,  BoolAnd),
        ("or",  2, opAssoc.LEFT,  BoolOr),
    ])
    return bool(boolExpr.parseString(boolstring)[0])

