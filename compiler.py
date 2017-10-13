import lexer
from goviaji_parser import read_file, parse_instructions, is_keyword, RuleKeywords, TokenList
import rules
from builtin_rules import add_builtins
from expressions import Variable, expression_from_list
import os


class CompilerError(Exception):
    pass


def is_constant(t, name=None):
    return isinstance(t, lexer.Token) and t.type == lexer.TokenType.CONSTANT and \
           (name is None or t.string == name)


class Compiler:
    def __init__(self):
        self.rules_db = rules.Rules()
        add_builtins(self.rules_db)
        self.expressions_to_print = {}
        self.compiled_files = set()

    @staticmethod
    def file_name_report_str(file_name, inclusion_path):
        text = file_name
        if inclusion_path is not None:
            for fn in inclusion_path:
                text += "\n\t...included from " + fn

        return text

    def compile_file(self, file_name, inclusion_path=None):
        file_name = os.path.abspath(file_name)
        self.compiled_files.add(file_name)
        print("Compiling %s..." % os.path.basename(file_name))
        file_name_report = self.file_name_report_str(file_name, inclusion_path)

        if not os.path.exists(file_name):
            raise CompilerError("cannot find file " + file_name_report)

        try:
            tokens = lexer.tokenize(read_file(file_name))
            compiled_instructions = parse_instructions(tokens)
        except lexer.RuleParseError as err:
            raise CompilerError("parse error in file %s:\n%s" % (file_name_report, err.args[0]))

        for instr in compiled_instructions:
            definition_src = "file %s:\n%s" % (file_name_report, instr.source_str(tokens.lines))
            if is_keyword(instr.name, RuleKeywords.IMPORT):
                cur_folder = os.path.dirname(file_name)
                module_path = []
                for t in (instr.expression.elems if isinstance(instr.expression, TokenList)
                          else [instr.expression]):
                    if isinstance(t, lexer.Token):
                        if t.type == lexer.TokenType.VARIABLE:
                            raise CompilerError("variable in imports:\n" + tokens.part_str(instr.loc, t.loc))

                        module_path.append(t.string)
                    else:
                        raise CompilerError("compound expression in imports:\n" + tokens.part_str(instr.loc, t.loc))

                to_include = os.path.join(cur_folder, *module_path) + ".goviaji"
                to_include = os.path.abspath(to_include)
                if to_include in self.compiled_files:
                    continue

                self.compile_file(to_include, [file_name] if inclusion_path is None else ([file_name] + inclusion_path))
            elif is_keyword(instr.name, RuleKeywords.RULE) or is_keyword(instr.name, RuleKeywords.DEF) or \
                    is_keyword(instr.name, RuleKeywords.PRINT):
                if not isinstance(instr.expression, TokenList) or len(instr.expression.elems) < 3 or \
                        not is_constant(instr.expression.elems[0]) or \
                        not is_constant(instr.expression.elems[1],  "="):
                    raise CompilerError("syntax error in %s. Expected <name> = <expression> format:\n%s" %
                                        (instr.name.string, tokens.part_str(instr.loc, instr.expression.loc)))

                name = self.compile_expression(instr.expression.elems[0], tokens)
                expr_tokens = instr.expression.elems[2:]
                if is_keyword(instr.name, RuleKeywords.DEF) or is_keyword(instr.name, RuleKeywords.PRINT):
                    expr = self.compile_expression(expr_tokens, tokens)
                    if is_keyword(instr.name, RuleKeywords.DEF):
                        self.rules_db.add_definition(name, expr, definition_src)
                    else:
                        if name in self.expressions_to_print:
                            raise CompilerError("duplicate print label %s:\nFirst occurrence:\n"
                                                "%s\nDuplicate occurrence:\n%s" % (name.name,
                                                                                   self.expressions_to_print[name][1],
                                                                                   definition_src))

                        self.expressions_to_print[name] = expr, definition_src
                else:
                    conclusion_tokens = []
                    while expr_tokens and not is_constant(expr_tokens[0], ":-"):
                        conclusion_tokens.append(expr_tokens.pop(0))

                    if not conclusion_tokens:
                        raise CompilerError("rule with an empty head:\n" + tokens.part_str(instr.loc))

                    conclusion = self.compile_expression(conclusion_tokens, tokens)
                    premises = []

                    if expr_tokens:
                        expr_tokens.pop(0)
                        while expr_tokens:
                            premise_tokens = []
                            while expr_tokens and not is_constant(expr_tokens[0], ","):
                                if is_constant(expr_tokens[0], ":-"):
                                    raise CompilerError("second turnstile in rule:\n" +
                                                        tokens.part_str(instr.loc, expr_tokens[0].loc))

                                premise_tokens.append(expr_tokens.pop(0))

                            if not premise_tokens:
                                raise CompilerError("empty premise in rule:\n" + tokens.part_str(instr.loc))

                            premises.append(self.compile_expression(premise_tokens, tokens))
                            if expr_tokens:
                                expr_tokens.pop(0)

                    added_rule = rules.Rule(premises, conclusion, name, definition_src, self.rules_db)
                    self.rules_db.add_rule(added_rule)

                    exprs = [added_rule.conclusion] + added_rule.premises
                    var_counter = {}
                    for e in exprs:
                        e.count_leaves(var_counter)

                    for leaf, count in var_counter.items():
                        if count == 1 and leaf in added_rule.variables:
                            for e in exprs[1:]:
                                e_vars = e.collect_variables()
                                if leaf in e_vars and len(e_vars) == 1:
                                    print("Warning: rule %s has unbound variable %s:\n%s\nRepresentation: %s" %
                                          (added_rule.name, leaf.name, definition_src, added_rule.to_str()))
            else:
                raise CompilerError("unknown instruction type %s" % instr.name)

        print("Finished %s" % os.path.basename(file_name))

    def compile_expression(self, parsed_expression, tokens):
        if isinstance(parsed_expression, lexer.Token):
            if parsed_expression.type == lexer.TokenType.CONSTANT:
                return self.rules_db.add_constant_by_name(parsed_expression.string)

            if parsed_expression.type == lexer.TokenType.VARIABLE:
                return Variable(parsed_expression.string)

            raise CompilerError("Unknown token:\n" + tokens.part_until_here_str(parsed_expression.loc))

        if isinstance(parsed_expression, TokenList):
            parsed_expression = parsed_expression.elems

        return expression_from_list([self.compile_expression(e, tokens) for e in parsed_expression])

    def finalize(self):
        self.rules_db.flatten_definitions()
        for name, (expr, src) in self.expressions_to_print.items():
            self.expressions_to_print[name] = self.rules_db.instantiate_definitions(expr), src
