import enum
from lexer import TokenType, part_str, RuleParseError, tokenize


class RuleKeywords(enum.Enum):
    IMPORT = "import"
    RULE = "rule"
    DEF = "def"
    PRINT = "print"
    OPEN_PARENTHESIS = "("
    CLOSE_PARENTHESIS = ")"


all_keywords = frozenset([k.value for k in RuleKeywords])


def is_keyword(token, keyword=None):
    return token.type == TokenType.CONSTANT and \
           (token.string in all_keywords if keyword is None else (token.string == keyword.value))


def is_next_keyword(tokens, keyword=None):
    return is_keyword(tokens.next(), keyword)


class Instruction:
    def __init__(self, name, expr, loc):
        self.loc = loc
        self.name = name
        self.expression = expr

    def source_str(self, lines):
        return part_str(self.loc, lines)


def parse_instructions(tokens):
    instructions = []
    while not tokens.is_empty():
        pos_begin = tokens.next_begin_pos
        instruction_name = tokens.pop()
        if instruction_name.string not in [RuleKeywords.IMPORT.value, RuleKeywords.RULE.value, RuleKeywords.DEF.value,
                                           RuleKeywords.PRINT.value]:
            raise RuleParseError("unknown instruction %s:\n%s" % (instruction_name.string,
                                                                  tokens.part_until_here_str(pos_begin, instruction_name.loc)))

        if tokens.is_empty():
            raise RuleParseError("instruction without content:\n" + tokens.part_until_here_str(pos_begin))

        expr = parse_expression(tokens)
        instructions.append(Instruction(instruction_name, expr, (pos_begin, tokens.last_end_pos)))

    return instructions


class TokenList:
    def __init__(self, elems, loc):
        self.elems = elems
        self.loc = loc


def parse_expression(tokens):
    pos_begin = tokens.next_begin_pos
    subexpressions = []
    while True:
        if tokens.is_empty():
            break
        elif is_next_keyword(tokens, RuleKeywords.OPEN_PARENTHESIS):
            p = tokens.pop()
            subexpressions.append(parse_expression(tokens))
            if tokens.is_empty():
                raise RuleParseError("unbalanced parenthesis:\n" + tokens.part_until_here_str(pos_begin, p.loc))

            p = tokens.pop()
            if not is_keyword(p, RuleKeywords.CLOSE_PARENTHESIS):
                raise RuleParseError("expected closing parenthesis:\n" + tokens.part_until_here_str(pos_begin, p.loc))

        elif is_next_keyword(tokens):
            break
        else:
            subexpressions.append(parse_atom(tokens))

    if len(subexpressions) == 0:
        t = tokens.pop()
        raise RuleParseError("empty term:\n" + tokens.part_until_here_str(pos_begin, t.loc))

    if len(subexpressions) == 1:
        return subexpressions[0]

    return TokenList(subexpressions, (pos_begin, tokens.last_end_pos))


def parse_atom(tokens):
    t = tokens.pop()
    return t


def read_file(file_name):
    with open(file_name, "r") as f:
        return "".join(f.readlines())
