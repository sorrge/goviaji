import enum
import re


class RuleParseError(Exception):
    pass


class TokenType(enum.Enum):
    CONSTANT = 0
    VARIABLE = 1


nontab_re = re.compile("[^\t]")


def pos_indicator_str(line, pos_from, pos_to, indicator_char):
    padding = nontab_re.sub(" ", line[:pos_from])
    pointer = nontab_re.sub(indicator_char, line[pos_from:pos_to])
    return padding + pointer


def overwrite_indicator(indicator_background, indicator_foreground):
    res = ""
    indicator_foreground += " " * (len(indicator_background) - len(indicator_foreground))
    for bg, fg in zip(indicator_background, indicator_foreground):
        if not fg.isspace():
            res += fg
        else:
            res += bg

    return res


def at_pos_str(line, line_num, pos_from, pos_to):
    line_num_str = "%-4d: " % (line_num + 1)
    text = line_num_str + line + "\n" + " " * len(line_num_str)
    text += pos_indicator_str(line, pos_from, pos_to, "^")
    return text


def part_str(print_loc, lines, highlight_loc=None):
    text = ""
    (row_begin, col_begin), (row_end, col_end) = print_loc
    if highlight_loc is not None:
        (highlight_row_begin, highlight_col_begin), (highlight_row_end, highlight_col_end) = highlight_loc

    for line_num in range(row_begin, row_end + 1):
        line_num_str = "%-4d: " % (line_num + 1)
        text += line_num_str + lines[line_num]
        indicator = "\n" + " " * len(line_num_str)
        indicator += pos_indicator_str(lines[line_num], col_begin if line_num == row_begin else 0,
                                      col_end if line_num == row_end else len(lines[line_num]), "-")

        if highlight_loc is not None and highlight_row_begin <= line_num <= highlight_row_end:
            highlight = "\n" + " " * len(line_num_str)
            highlight += pos_indicator_str(lines[line_num],
                                           highlight_col_begin if line_num == highlight_row_begin else 0,
                                           highlight_col_end if line_num == highlight_row_end else
                                           len(lines[line_num]), "^")

            indicator = overwrite_indicator(indicator, highlight)

        text += indicator

        if line_num < row_end:
            text += "\n"

    return text


class Token:
    def __init__(self, type, string, loc):
        self.type = type
        self.string = string
        self.loc = loc

    def __repr__(self):
        return "%s:%s" % ("V" if self.type == TokenType.VARIABLE else "C", self.string)

    def pos_begin(self):
        return self.loc[0]

    def pos_end(self):
        return self.loc[1]


class IncompleteTokenType:
    NONE = 0
    VARIABLE = 1
    CONSTANT_ALPHA = 2
    CONSTANT_NUM = 3
    CONSTANT_OP = 4
    COMMENT = 5


class Tokenizer:
    def __init__(self):
        self.cur_row = 0
        self.tokens = []
        self.cur_type = IncompleteTokenType.NONE
        self.finish_token()

    def take_char(self, c, row, col, line):
        if row > self.cur_row:
            self.finish_token()

        if self.cur_type == IncompleteTokenType.NONE or self.cur_type == IncompleteTokenType.CONSTANT_OP:
            self.new_token(c, row, col, line)
        elif self.cur_type == IncompleteTokenType.VARIABLE or self.cur_type == IncompleteTokenType.CONSTANT_ALPHA:
            if c.isalnum() or c == "_":
                self.cur_string += c
            else:
                self.new_token(c, row, col, line)
        elif self.cur_type == IncompleteTokenType.CONSTANT_NUM:
            if c.isdecimal():
                self.cur_string += c
            elif c.isalpha():
                raise RuleParseError("invalid number constant " +
                                     at_pos_str(line, row, self.cur_begin_col, col + 1))
            else:
                self.new_token(c, row, col, line)
        else:
            pass

    def new_token(self, c, row, col, line):
        self.finish_token()
        if c.isspace():
            return
        elif c.isupper():
            self.begin_token(IncompleteTokenType.VARIABLE, c, row, col)
        elif c.isdecimal():
            self.begin_token(IncompleteTokenType.CONSTANT_NUM, c, row, col)
        elif c.isalpha() or c == "_":
            self.begin_token(IncompleteTokenType.CONSTANT_ALPHA, c, row, col)
        elif c == "#":
            self.begin_token(IncompleteTokenType.COMMENT, c, row, col)
        elif c.isprintable():
            self.begin_token(IncompleteTokenType.CONSTANT_OP, c, row, col)
        else:
            raise RuleParseError("invalid character \"%s\" %s" % (c, at_pos_str(line, row, col, col + 1)))

    def finish_token(self):
        if self.cur_type == IncompleteTokenType.VARIABLE:
            self.tokens.append(Token(TokenType.VARIABLE, self.cur_string,
                                     ((self.cur_row, self.cur_begin_col),
                                      (self.cur_row, self.cur_begin_col + len(self.cur_string)))))
        elif self.cur_type != IncompleteTokenType.NONE and self.cur_type != IncompleteTokenType.COMMENT:
            self.tokens.append(Token(TokenType.CONSTANT, self.cur_string,
                                     ((self.cur_row, self.cur_begin_col),
                                      (self.cur_row, self.cur_begin_col + len(self.cur_string)))))

        self.cur_type = IncompleteTokenType.NONE
        self.cur_begin_col = None
        self.cur_string = "NO_TOKEN"

    def begin_token(self, type, c, row, col):
        self.cur_type = type
        self.cur_begin_col = col
        self.cur_string = c
        self.cur_row = row


class Tokens:
    def __init__(self, tokens, lines):
        self.tokens = tokens
        self.lines = lines
        self.next_begin_pos = tokens[0].pos_begin() if len(tokens) > 0 else (0, 0)
        self.last_end_pos = 0, 0

    def is_empty(self):
        return len(self.tokens) == 0

    def next(self):
        return self.tokens[0]

    def pop(self):
        self.last_end_pos = self.next().pos_end()
        next_token = self.tokens[0]
        self.tokens.pop(0)
        if not self.is_empty():
            self.next_begin_pos = self.next().pos_begin()

        return next_token

    def part_until_here_str(self, pos_begin, highlight_loc=None):
        return part_str((pos_begin, self.last_end_pos), self.lines, highlight_loc)

    def part_str(self, loc, highlight_loc=None):
        return part_str(loc, self.lines, highlight_loc)


def is_punctuation(s):
    return s.isprintable() and not any(c.isalnum() or c == "_" for c in s) and s != ")" and s != "("


def tokenize(text):
    tokenizer = Tokenizer()
    lines = text.split("\n")

    for row, line in enumerate(lines):
        for col, c in enumerate(line):
            tokenizer.take_char(c, row, col, line)

    tokenizer.finish_token()

    joined_tokens = []
    for token in tokenizer.tokens:
        if is_punctuation(token.string) and len(joined_tokens) > 0 and is_punctuation(joined_tokens[-1].string) and \
                        joined_tokens[-1].loc[1] == token.loc[0]:
            joined_tokens[-1].string += token.string
            joined_tokens[-1].loc = joined_tokens[-1].loc[0], token.loc[1]
        else:
            joined_tokens.append(token)

    return Tokens(joined_tokens, lines)
