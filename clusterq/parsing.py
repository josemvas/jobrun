'''
Disj = Conj | Conj '|' Disj
Conj = Neg  | Neg & Conj
Neg = Lit | ! Lit
Lit = [A-Z]  | ( Disj )
'''

import re

def tokenize(expr):
    for token in re.findall(r'(?:[^ ()]+|[()])', expr):
        yield token

class Node:
    def __init__(self, left, right, name):
        self.left = left
        self.right = right
        self.name = name
    def pr(self):
        a = '('
        if self.left != None:
            a += self.left.pr()
        a += ' ' + self.name + ' '
        if self.right != None:
            a += self.right.pr()
        a += ')'
        return a
    def evaluate(self, values):
        if self.name == 'not':
            return not self.right.evaluate(values)
        elif self.name == 'and':
            return self.left.evaluate(values) and self.right.evaluate(values)
        elif self.name == 'or':
            return self.left.evaluate(values) or self.right.evaluate(values)
        elif self.name in values:
            return values[self.name]
        else:
            raise Exception(self.name, 'not in value dict')

class BoolParser:
    def __init__(self, expr):
        self.tokens = tokenize(expr)
        self.current = next(self.tokens, None)
        self.etree = self.Disj()
    def pr(self):
        return self.etree.pr()
    def evaluate(self, values):
        return self.etree.evaluate(values)
    def accept(self, c):
        if self.current == c:
            self.current = next(self.tokens, None)
            return True
        return False
    def expect(self, c):
        if self.current == c:
            self.current = next(self.tokens, None)
            return True
        raise Exception('Unexpected token', self.current, 'expected', c)
    def Disj(self):
        l = self.Conj()
        if self.accept('or'):
            r = self.Disj()
            if r is None:
                return None
            return Node(l, r, 'or')
        return l
    def Conj(self):
        l = self.Neg()
        if self.accept('and'):
            r = self.Conj()
            if r is None:
                return None
            return Node(l, r, 'and')
        return l
    def Neg(self):
        if self.accept('not'):
            l = self.Lit()
            if l is None:
                return None
            return Node(None, l, 'not')
        return self.Lit()
    def Lit(self):
        if self.accept('('):
            r = self.Disj()
            if self.expect(')'):
                return r
            return None
        l = self.current
        self.current = next(self.tokens, None)
        if re.fullmatch(r'[a-zA-Z0-9_.]+', l):
            return Node(None, None, l)
        else:
            raise Exception('Expected an alphanumeric string')

