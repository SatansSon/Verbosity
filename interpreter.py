import re
import sys

import _exceptions as exceptions
import _parser as parser
import _types as types
import _checks as checks

VARIABLES = {}
INCLUDES = []
STRUCTURES = []
EXTERNALS = []

def isint(string):
    return re.search(r'^-?\d+$', string) and 'Integer' in INCLUDES

def isreal(string):
    return re.search(r'^-?\d+\.\d+$', string) and 'FloatingPoint' in INCLUDES

def iscomplex(string):
    return re.search(r'^-?\d+(\.\d+)?[+-]\d+(\.\d+)?j$', string) and 'Complex' in INCLUDES

def isstring(string):
    sliced = 1
    if string[:3] == '"""':
        if string[-3:] != '"""':
            return False
        sliced = 3
    if string[0] != string[-1] != '"':
        return False
    return 'String' in INCLUDES

def isconst(string):
    return re.search(r'^({})@[A-Z]+$'.format(')|('.join(INCLUDES)), string)

def standard_eval(*args):
    for value in args:
        try:
            yield VARIABLES[value]
        except:
            exceptions.RaiseException('UnknownArgumentProvided')

def define_eval(*args):
    if not args:
        exceptions.RaiseException('CannotDefineVariableToNothing')
    args = args[:(args[0].split(':')[0] in INCLUDES)+1]
    if len(args) == 1:
        value = args[0]
    else:
        master, method = args[0].split(':')
        master = PARENTS[master]
        new_args = list(standard_eval(*args[1]))
        return master.__run_method__(master, method, new_args)

    if isint(value):
        return types.Integer(value)
    if isreal(value):
        return types.FloatingPoint(value)
    if iscomplex(value):
        return types.Complex(value)
    if isstring(value):
        return types.String(value)
    if isconst(value):
        master, const = value.split('@')
        master = PARENTS[master]
        print(getattr(master, const))
        return getattr(master, const)
    if value in VARIABLES.keys():
        return VARIABLES[value]
    exceptions.RaiseException('UnknownArgumentProvided')

class MetaFunctions(types.BaseClass):
    GLOBALS = 'Testing'

class BaseBlock:
    def __run_method__(self, method, args, block):
        try: func = getattr(self, method)
        except: return
        func(self, args, block)

class Class(BaseBlock):
    pass

class Conditional(BaseBlock):
    pass

class Error(BaseBlock):
    pass

class Function(BaseBlock):
    pass

class Loop(BaseBlock):
    def WhileCondition(self, arg, block):
        new = list(standard_eval(*arg))[0]
        while checks.boolean(new):
            new = list(standard_eval(*arg))[0]
            for i, line in enumerate(block):
                interpreter.handle_line(line, interpreter.index+i)

PARENTS = {'Array'          :types.Array,
           'Binary'         :types.Binary,
           'Boolean'        :types.Boolean,
           'Complex'        :types.ComplexNumber,
           'Dictionary'     :types.DictionaryArray,
           'FloatingPoint'  :types.FloatingPointNumber,
           'Input'          :types.Input,
           'Integer'        :types.Integer,
           'MetaFunctions'  :MetaFunctions,
           'Output'         :types.Output,
           'Set'            :types.SetArray,
           'String'         :types.String,
           'UnorderedSet'   :types.UnorderedSetArray}
STRUCTS = {'Class'          :Class,
           'Conditional'    :Conditional,
           'Function'       :Function,
           'Loop'           :Loop}

class Interpreter:
    def __init__(self):
        self.index = 1
        
    def handle_line(self, line, index):
        try:

            if len(types.Output.WRITTEN) > 127:
                exceptions.RaiseException('OutputTooLarge')
            
            func = line[0]
                
            if func == 'Include':
                new_type = line[1][0]
                if new_type in PARENTS:
                    INCLUDES.append(new_type)
                else:
                    exceptions.RaiseException('UnknownIncludeType')
                
            if func == 'Structure':
                new_struct = line[1][0]
                if new_struct in STRUCTS:
                    STRUCTURES.append(new_struct)
                else:
                    exceptions.RaiseException('UnknownStructure')
                    
            elif re.search(r'({}):DefineVariable'.format('|'.join(INCLUDES)), func):
                variable_type = PARENTS[func.split(':DefineVariable')[0]]
                name = line[1][0]
                value = define_eval(*line[1][1:])
                if name in VARIABLES.keys():
                    exceptions.RaiseException('VariableAlreadyDefined')
                if len(name) < 10 and name not in ['STDOUT', 'STDIN', 'STDERR']:
                    exceptions.RaiseException('VariableNameMustBeTenCharactersMinimum')
                VARIABLES[name] = variable_type(value)
                    
            elif re.search(r'({}):RedefineVariable'.format('|'.join(INCLUDES)), func):
                name = line[1][0]
                new_value = define_eval(*line[1][1:])
                try: variable_type = VARIABLES[name].__class__
                except: exceptions.RaiseException('AttemptToRedefineUnknownVariable')
                VARIABLES[name] = variable_type(new_value)
                    
            elif func.split(':')[0] in INCLUDES:
                master = PARENTS[func.split(':')[0]]
                method = func.split(':')[1]
                args = list(standard_eval(*line[1]))
                master.__run_method__(master, method, args)
                    
            elif func.split(':')[0] in VARIABLES.keys():
                var = VARIABLES[func.split(':')[0]]
                master = var.__class__
                method = func.split(':')[1]
                args = list(standard_eval(*line[1]))
                master.__run_method__(var, method, args)
                
            elif func.split(':')[0] in STRUCTURES:
                master, method = func.split(':')
                master = STRUCTS[master]
                args = line[1]
                block = line[2]
                master.__run_method__(master, method, args, block)
                
        except Exception as e:
            exceptions.ShowError(e, self.code.split('\n')[index], index + len(list(filter(lambda a: not a, self.code.split('\n')))))

    def handle_main(self, code, parsed):
        lines = code[0][2]

        for line in lines:
            if line[0] == 'MetaFunctions:ExecuteScript':
                file = line[1][0]
                if file == 'MetaFunctions@FILE':
                    for i, line in enumerate(parsed):
                        self.index = i
                        self.handle_line(line, self.index)

    def interpreter(self, code):
        self.code = code
        try:
            parsed = parser.parser(code)
        except:
            exceptions.ShowError(exceptions.CustomException('InvalidSyntax'), self.code, -1)

        match = re.search(r'''DefineMain<> \[$
^.*$
^]$''', self.code, re.MULTILINE|re.DOTALL)
        try:
            start, end = match.start(), match.end()
        except:
            exceptions.ShowError(exceptions.CustomException('No\'DefineMain\'Defination'),
                                 self.code[-1], len(self.code.split('\n')))

        self.handle_main(parser.parser(self.code[start:end]),
                         parser.parser(self.code[:start]+self.code[end:]))

if __name__ == '__main__':
    interpreter = Interpreter()
    program = open(sys.argv[1], 'r').read()
    if program:
        interpreter.interpreter(program)
