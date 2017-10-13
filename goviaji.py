from sys import stderr
from compiler import Compiler, CompilerError
import rules
import prover
from expressions import expression_from_list
from lexer import tokenize
from goviaji_parser import parse_expression


class Goviaji:
    def __init__(self, file_name):
        self.proof_steps_budget = 10000
        self.max_eval_steps = 1000
        self.prover_cache = {}
        self.compiler = Compiler()
        self.compiler.compile_file(file_name)
        self.compiler.finalize()
        self.syntax_predicate_name = self.compiler.rules_db.constants["term"] \
            if "term" in self.compiler.rules_db.constants else None
        
        self.value_predicate_name = self.compiler.rules_db.constants["value"] \
            if "value" in self.compiler.rules_db.constants else None
        
        self.eval_predicate_name = self.compiler.rules_db.constants["eval"] \
            if "eval" in self.compiler.rules_db.constants else None

        print("%d rules loaded: %s" %
              (len(self.compiler.rules_db.rules_by_name),
               ", ".join(rn.name for rn in self.compiler.rules_db.rules_by_name.keys())))

        print("%d defs loaded: %s" %
              (len(self.compiler.rules_db.definitions),
               ", ".join(rn.name for rn in self.compiler.rules_db.definitions.keys())))

        print("%d outputs loaded: %s" %
              (len(self.compiler.expressions_to_print),
               ", ".join(rn.name for rn in self.compiler.expressions_to_print.keys())))

    def property_check(self, expr, property_name):
        test_proposition = [expression_from_list([property_name, expr])]
        steps, subs = next(prover.prove_dfs(self.compiler.rules_db, test_proposition, self.proof_steps_budget,
                                            self.prover_cache))
        return steps, subs is not None
    
    def syntax_check(self, expr):
        return self.property_check(expr, self.syntax_predicate_name)
        
    def value_check(self, expr):
        return self.property_check(expr, self.value_predicate_name)

    def eval_step(self, expr):
        target_var = self.compiler.rules_db.introduce_variable()
        eval_proposition = [expression_from_list([self.eval_predicate_name, expr, target_var])]
        steps, subs = next(prover.prove_dfs(self.compiler.rules_db, eval_proposition, self.proof_steps_budget,
                                            self.prover_cache))

        return steps, subs.replacements[target_var] if subs is not None else subs

    def steps_report(self, num_steps):
        return "[%d steps%s]" % (num_steps, " - stopped" * (num_steps >= self.proof_steps_budget))

    def str_to_expression(self, s):
        tokens = tokenize(s)
        parsed_expr = parse_expression(tokens)
        return self.compiler.compile_expression(parsed_expr, tokens)


def run_file(file_name):
    print("Running file %s" % file_name)
    try:
        goviaji = Goviaji(file_name)
    except CompilerError as err:
        print("Compilation error: " + err.args[0], file=stderr)
        exit(1)
    except rules.RulesError as err:
        print("Rules error: " + err.args[0], file=stderr)
        exit(1)

    if not goviaji.syntax_predicate_name:
        print("Rules have no predicate \"term\", skipping syntax checks")

    if not goviaji.value_predicate_name:
        print("Rules have no predicate \"value\", skipping value checks")

    if not goviaji.eval_predicate_name:
        print("Rules have no predicate \"eval\", skipping evaluation")

    for name, (expr, src) in goviaji.compiler.expressions_to_print.items():
        print("Output %s: " % name.name, end="")
        if goviaji.syntax_predicate_name:
            steps, syntax_ok = goviaji.syntax_check(expr)
            if not syntax_ok:
                print("syntax check failure \"%s\" %s\n" % (expr.to_str(), goviaji.steps_report(steps)))
                print()
                continue
            else:
                print("syntax ok %s." % goviaji.steps_report(steps), end="")

        current_expr = expr

        if not goviaji.eval_predicate_name:
            if goviaji.value_predicate_name:
                steps, is_value = goviaji.value_check(current_expr)
                if is_value:
                    print(" value %s" % goviaji.steps_report(steps))
                else:
                    print(" not value %s" % goviaji.steps_report(steps))
            else:
                print()

            print()
            continue

        print(" Evaluating:")

        for s in range(goviaji.max_eval_steps):
            print("\t[%d]\t%s: " % (s, goviaji.compiler.rules_db.collapse_definitions(current_expr).to_str()),
                  end="")

            if goviaji.value_predicate_name:
                steps, is_value = goviaji.value_check(current_expr)
                if is_value:
                    print("value %s" % goviaji.steps_report(steps))
                    break

                print("not value %s, " % goviaji.steps_report(steps), end="")

            steps, current_expr = goviaji.eval_step(current_expr)
            if current_expr is None:
                print("eval failure %s. Term is stuck." % goviaji.steps_report(steps))
                break

            print("eval ok %s" % goviaji.steps_report(steps))
            if s == goviaji.max_eval_steps - 1:
                print("Calculation stopped after %d steps" % goviaji.max_eval_steps)

        print()

    print()


if __name__ == '__main__':
    #run_file("systems/untyped_arithmetic/b.goviaji")
    #run_file("systems/untyped_arithmetic/nb.goviaji")
    #run_file("systems/untyped_arithmetic/nb_branches_first.goviaji")
    #run_file("systems/untyped_arithmetic/nb_big_step.goviaji")
    #run_file("systems/untyped_arithmetic/nb_with_wrong.goviaji")
    #run_file("systems/untyped_lambda/lambda_semantics.goviaji")
    #run_file("systems/untyped_lambda/cn_tests.goviaji")
    run_file("systems/untyped_lambda/lambda_nb_tests.goviaji")
