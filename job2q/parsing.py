# -*- coding: utf-8 -*-
from re import match

'''
    Disj = Conj | Conj '|' Disj
    Conj = Neg  | Neg & Conj
    Neg = Lit | ! Lit
    Lit = [A-Z]  | ( Disj )
'''

def lexer(s):
    for token in s.replace('(', ' ( ').replace(')', ' ) ').split():
        yield token
    while True:
        yield '\0'

class Node:
    def __init__(self, left, right, name):
        self.left=left
        self.right=right
        self.name=name
    def pr(self):
        a = "("
        if self.left!=None:
            a += self.left.pr()
        a += " " + self.name + " "
        if self.right != None:
            a += self.right.pr()
        a+=')'
        return a
    def ev(self, values):
        if self.name=="not":
            return not self.right.ev(values)
        if self.name=="and":
            return self.left.ev(values) and self.right.ev(values)
        if self.name=="or":
            return self.left.ev(values) or self.right.ev(values)
        if self.name not in values:
            raise Exception(self.name, 'not in value dict')
        return values[self.name]



class BoolParser:

    def __init__(self, s):
        self.lex = lexer(s)
        self.current = next(self.lex)
        self.tree = self.Disj()

    def pr(self):
        return self.tree.pr()

    def ev(self, values):
        return self.tree.ev(values)

    def accept(self, c):
        if self.current == c:
            self.current = next(self.lex)
            return True
        return False

    def expect(self, c):
        if self.current == c:
            self.current = next(self.lex)
            return True
        raise Exception('Unexpected token', self.current, 'expected', c)
        return False

    def Disj(self):
        l = self.Conj()
        if self.accept('or'):
            r = self.Disj()
            if r == None:
                return None
            return Node(l, r, "or")
        return l

    def Conj(self):
        l = self.Neg()
        if self.accept('and'):
            r = self.Conj()
            if r == None:
                return None
            return Node(l, r, "and")
        return l

    def Neg(self):
        if self.accept('not'):
            l = self.Lit()
            if l == None:
                return None
            return Node(None, l, "not")
        return self.Lit()

    def Lit(self):
        if self.accept('('):
            r = self.Disj()
            if self.expect(')'):
                return r
            return None
        l = self.current
        self.current = next(self.lex)
        if not match(r'[A-Za-z0-9_.]+$', l):
            raise Exception('Expected an alphanumeric string')
        return Node(None, None, l)

