import unittest
from goviaji import Goviaji
from compiler import Compiler, CompilerError
import rules
import os


def make_goviaji_test_case(file_name, test_cases):
    test_case_name = os.path.splitext(file_name)[0]
    print(test_case_name)
    test_class = type(test_case_name, (unittest.TestCase,), {})

    @classmethod
    def setUpClass(self):
        try:
            self.goviaji = Goviaji(file_name)
        except CompilerError as err:
            self.fail("Compilation error: " + err.args[0])
        except rules.RulesError as err:
            self.fail("Rules error: " + err.args[0])

    setUpClass.__name__ = "setUpClass"
    setattr(test_class, setUpClass.__name__, setUpClass)

    for output_name, expected_output in test_cases.items():
        def test_func_maker(expr_name, output):
            def test_func(self):
                self.assertIn(expr_name, self.goviaji.compiler.rules_db.constants, "%s is not defined" % expr_name)
                name = self.goviaji.compiler.rules_db.constants[expr_name]
                self.assertIn(name, self.goviaji.compiler.expressions_to_print, "%s is not an output")
                current_expr = self.goviaji.compiler.expressions_to_print[name][0]
                step = 0
                for test in output.split(";"):
                    if len(test) == 0:
                        continue
                    elif test.startswith("SYNTAX"):
                        self.assertIsNotNone(self.goviaji.syntax_predicate_name, "syntax is not defined")
                        steps, syntax_ok = self.goviaji.syntax_check(current_expr)
                        self.assertTrue(syntax_ok or test != "SYNTAX_OK",
                                        "syntax check failure %s\n" % self.goviaji.steps_report(steps))

                        self.assertTrue(not syntax_ok or test == "SYNTAX_OK",
                                        "syntax unexpectedly ok %s." % self.goviaji.steps_report(steps))
                    elif test.endswith("VALUE"):
                        self.assertIsNotNone(self.goviaji.value_predicate_name, "value check is not defined")
                        steps, is_value = self.goviaji.value_check(current_expr)
                        self.assertTrue(is_value or test != "VALUE",
                                        "value check failure: %s %s\n" %
                                        (current_expr.to_str(), self.goviaji.steps_report(steps)))

                        self.assertTrue(not is_value or test == "VALUE",
                                        "term is unexpectedly a value: %s %s." %
                                        (current_expr.to_str(), self.goviaji.steps_report(steps)))
                    elif test.startswith("STEP_"):
                        jump_to = int(test.replace("STEP_", ""))
                        while step != jump_to:
                            self.assertIsNotNone(self.goviaji.eval_predicate_name, "eval is not defined")
                            steps, new_current_expr = self.goviaji.eval_step(current_expr)
                            self.assertIsNotNone(new_current_expr, "could not eval: \"%s\" %s, at step %d, expected to"
                                                                   " reach step %d\n" %
                                                (current_expr.to_str(), self.goviaji.steps_report(steps), step,
                                                 jump_to))

                            current_expr = new_current_expr
                            step += 1
                    else:
                        self.assertIsNotNone(self.goviaji.eval_predicate_name, "eval is not defined")
                        steps, new_current_expr = self.goviaji.eval_step(current_expr)
                        if new_current_expr:
                            self.assertTrue(test != "NORMAL",
                                            "normal form \"%s\" evaluated to: \"%s\" %s\n" %
                                            (current_expr.to_str(), new_current_expr.to_str(),
                                             self.goviaji.steps_report(steps)))

                            if test != "_":
                                test_expr = self.goviaji.str_to_expression(test)
                                current_output = self.goviaji.compiler.rules_db.collapse_definitions(new_current_expr)
                                self.assertIsNotNone(current_output.unify(test_expr),
                                                "\"%s\" evaluated to \"%s\" %s, expected \"%s\"" %
                                                (current_expr.to_str(), current_output.to_str(),
                                                 self.goviaji.steps_report(steps), test))

                            current_expr = new_current_expr
                            step += 1
                        else:
                            if test != "NORMAL":
                                self.fail("could not eval: \"%s\" %s, expected %s\n" %
                                                (current_expr.to_str(), self.goviaji.steps_report(steps),
                                                 test))

            return test_func

        test_function = test_func_maker(output_name, expected_output)
        test_function.__name__ = "test_" + output_name

        setattr(test_class, test_function.__name__, test_function)

    globals()[test_case_name] = test_class


make_goviaji_test_case("systems/untyped_arithmetic/b_tests.goviaji",
                       {"simple":"SYNTAX_OK;NOT_VALUE;true;NORMAL;VALUE",
                        "double":"SYNTAX_OK;if true then (if false then false else false) else true;"
                                 "if false then false else false;false;NORMAL;VALUE",
                        "syntax_error":"SYNTAX_ERROR",
                        "main":"SYNTAX_OK;if false then false else false;false;NORMAL;VALUE",
                        "val":"SYNTAX_OK;NORMAL;VALUE"})

make_goviaji_test_case("systems/untyped_arithmetic/nb_tests.goviaji",
                       {"simple":"SYNTAX_OK;NOT_VALUE;true;NORMAL;VALUE",
                        "double":"SYNTAX_OK;if true then (if false then false else false) else true;"
                                 "if false then false else false;false;NORMAL;VALUE",
                        "syntax_error":"SYNTAX_ERROR",
                        "main":"SYNTAX_OK;if false then false else false;false;NORMAL;VALUE",
                        "val":"SYNTAX_OK;NORMAL;VALUE",
                        "ar_runtime_error":"SYNTAX_OK;NORMAL;NOT_VALUE",
                        "ar_0":"SYNTAX_OK;is_zero (pred 0);is_zero 0;true;NORMAL;VALUE",
                        "e_pred_succ_test":"SYNTAX_OK;pred 1;0;NORMAL;VALUE"})

make_goviaji_test_case("systems/untyped_arithmetic/nb_branches_first.goviaji",
                       {"test_1":"SYNTAX_OK;if true then false else true;false;NORMAL;VALUE",
                        "test_2":"SYNTAX_OK;true;NORMAL;VALUE",
                        "simple":"SYNTAX_OK;NOT_VALUE;true;NORMAL;VALUE",
                        "double":"SYNTAX_OK;if (if true then true else false) then false else true;"
                                 "if true then false else true;false;NORMAL;VALUE",
                        "triple":"SYNTAX_OK;if (if true then true else false) then false else "
                                 "(if (is_zero (succ (pred 0))) then (pred (succ 0)) else true);"
                                 "if (if true then true else false) then false else "
                                 "(if (is_zero (succ (pred 0))) then 0 else true);"
                                 "if (if true then true else false) then false else "
                                 "(if (is_zero (succ 0)) then 0 else true);"
                                 "if (if true then true else false) then false else (if false then 0 else true);"
                                 "if (if true then true else false) then false else true;"
                                 "if true then false else true;false;NORMAL;VALUE",
                        "syntax_error":"SYNTAX_ERROR",
                        "main":"SYNTAX_OK;if true then false else true;false;NORMAL;VALUE",
                        "val":"SYNTAX_OK;NORMAL;VALUE",
                        "test_stuck": "SYNTAX_OK;succ (if true then false else (succ 0));succ false;NORMAL;NOT_VALUE",
                        "test_num_bool": "SYNTAX_OK;if true then false else (succ 0);false;NORMAL;VALUE"})

make_goviaji_test_case("systems/untyped_arithmetic/nb_big_step.goviaji",
                       {"simple":"SYNTAX_OK;NOT_VALUE;true;VALUE",
                        "double":"SYNTAX_OK;false;VALUE",
                        "triple":"SYNTAX_OK;false;VALUE",
                        "syntax_error":"SYNTAX_ERROR",
                        "main":"SYNTAX_OK;false;VALUE",
                        "val":"SYNTAX_OK;VALUE",
                        "test_stuck": "SYNTAX_OK;NORMAL;NOT_VALUE",
                        "test_num_bool": "SYNTAX_OK;false;VALUE",
                        "ar_runtime_error":"SYNTAX_OK;NOT_VALUE",
                        "ar_0":"SYNTAX_OK;true;VALUE",
                        "e_pred_succ_test":"SYNTAX_OK;0;VALUE"})

make_goviaji_test_case("systems/untyped_arithmetic/nb_with_wrong.goviaji",
                       {"simple":"SYNTAX_OK;NOT_VALUE;true;NORMAL;VALUE",
                        "double":"SYNTAX_OK;if true then (if false then false else false) else true;"
                                 "if false then false else false;false;NORMAL;VALUE",
                        "syntax_error":"SYNTAX_ERROR",
                        "main":"SYNTAX_OK;if false then false else false;false;NORMAL;VALUE",
                        "val":"SYNTAX_OK;NORMAL;VALUE",
                        "ar_runtime_error":"SYNTAX_OK;wrong;NORMAL;NOT_VALUE",
                        "ar_0":"SYNTAX_OK;is_zero (pred 0);is_zero 0;true;NORMAL;VALUE",
                        "e_pred_succ_test":"SYNTAX_OK;pred 1;0;NORMAL;VALUE",
                        "test_wrong_1": "SYNTAX_OK;succ (if true then false else 1);succ false;wrong;"
                                        "NORMAL;NOT_VALUE",
                        "test_wrong_2":"SYNTAX_OK;if true then false else 1;false;NORMAL;VALUE"})

make_goviaji_test_case("systems/untyped_lambda/lambda_tests.goviaji",
                       {"simple":"SYNTAX_OK;NOT_VALUE;id;NORMAL;VALUE",
                        "simple_2":"SYNTAX_OK;NOT_VALUE;lambda x . (x id) (id id);"
                                   "lambda x . (x id) id;id id;"
                                   "id;NORMAL;VALUE",
                        "id_3": "SYNTAX_OK;NOT_VALUE;id (lambda z . (id z));"
                                "lambda z . (id z);NORMAL;VALUE",
                        "omega_test": "SYNTAX_OK;NOT_VALUE;omega;omega;omega;NOT_VALUE",
                        "bug_4":"SYNTAX_OK;NOT_VALUE;_;NORMAL;VALUE"})

make_goviaji_test_case("systems/untyped_lambda/cb_tests.goviaji",
                       {"cb1":"SYNTAX_OK;_;_;fls fls id;id id;id;NORMAL;VALUE",
                        "cb2": "SYNTAX_OK;_;_;tru fls id;_;fls;NORMAL;VALUE",
                        "and_1": "SYNTAX_OK;_;tru tru fls;_;tru;NORMAL;VALUE",
                        "and_2": "SYNTAX_OK;_;tru fls fls;_;fls;NORMAL;VALUE",
                        "and_3": "SYNTAX_OK;_;fls fls fls;id fls;fls;NORMAL;VALUE",
                        "and_4": "SYNTAX_OK;_;fls tru fls;id fls;fls;NORMAL;VALUE",
                        "or_1": "SYNTAX_OK;_;tru tru tru;_;tru;NORMAL;VALUE",
                        "or_2": "SYNTAX_OK;_;tru tru fls;_;tru;NORMAL;VALUE",
                        "or_3": "SYNTAX_OK;_;fls tru fls;id fls;fls;NORMAL;VALUE",
                        "or_4": "SYNTAX_OK;_;fls tru tru;id tru;tru;NORMAL;VALUE",
                        "not_1": "SYNTAX_OK;tru fls tru;_;fls;NORMAL;VALUE",
                        "not_2": "SYNTAX_OK;fls fls tru;id tru;tru;NORMAL;VALUE",
                        "pair_1": "SYNTAX_OK;_;_;_;tru id and;fls and;id;NORMAL;VALUE",
                        "pair_2": "SYNTAX_OK;_;_;_;fls id and;id and;and;NORMAL;VALUE"})

make_goviaji_test_case("systems/untyped_lambda/cn_tests.goviaji",
                       {"s0":"SYNTAX_OK;_;NORMAL;VALUE",
                        "s0_alt": "SYNTAX_OK;_;NORMAL;VALUE",
                        "plus_test": "SYNTAX_OK;_;_;NORMAL;VALUE",
                        "times_test_1": "SYNTAX_OK;STEP_6;NORMAL;VALUE",
                        "times_test_alt": "SYNTAX_OK;STEP_2;NORMAL;VALUE",
                        "power_test_1": "SYNTAX_OK;STEP_15;id fls;fls;NORMAL;VALUE",
                        "n1": "SYNTAX_OK;STEP_1;id tru;tru;NORMAL;VALUE",
                        "n2": "SYNTAX_OK;STEP_3;fls;NORMAL;VALUE",
                        "n3": "SYNTAX_OK;STEP_4;fls;NORMAL;VALUE",
                        "n4": "SYNTAX_OK;STEP_6;fls;NORMAL;VALUE",
                        "prd_1": "SYNTAX_OK;STEP_152;NORMAL;VALUE",
                        "power_test_2": "SYNTAX_OK;STEP_52;fls;NORMAL;VALUE",
                        "minus_test": "SYNTAX_OK;STEP_59;fls;NORMAL;VALUE",
                        "equal_test_1": "SYNTAX_OK;STEP_40;id tru;tru;NORMAL;VALUE",
                        "equal_test_2": "SYNTAX_OK;STEP_81;id tru;tru;NORMAL;VALUE",
                        "equal_test_3": "SYNTAX_OK;STEP_87;id fls;fls;NORMAL;VALUE",
                        "equal_test_4": "SYNTAX_OK;STEP_180;id tru;tru;NORMAL;VALUE",
                        "equal_test_5": "SYNTAX_OK;STEP_134;id fls;fls;NORMAL;VALUE",
                        "l1": "SYNTAX_OK;STEP_4;NORMAL;VALUE",
                        "l2": "SYNTAX_OK;STEP_1;id tru;tru;NORMAL;VALUE",
                        "l3": "SYNTAX_OK;STEP_8;fls;NORMAL;VALUE",
                        "l4": "SYNTAX_OK;STEP_14;prd;NORMAL;VALUE",
                        "l5": "SYNTAX_OK;fls tru fls;id fls;fls;NORMAL;VALUE",
                        "l6": "SYNTAX_OK;STEP_51;c3;NORMAL;VALUE"})

make_goviaji_test_case("systems/untyped_lambda/lambda_nb_tests.goviaji",
                       {"rb_1":"SYNTAX_OK;fls true false;id false;false;NORMAL;VALUE",
                        "rb_2": "SYNTAX_OK;tru true false;_;true;NORMAL;VALUE",
                        "rb_3": "SYNTAX_OK;if false then tru else fls;fls;NORMAL;VALUE",
                        "rb_4": "SYNTAX_OK;if true then tru else fls;tru;NORMAL;VALUE",
                        "rn_1": "SYNTAX_OK;STEP_5;3;NORMAL;VALUE",
                        "rn_2": "SYNTAX_OK;STEP_21;4;NORMAL;VALUE"})


if __name__ == '__main__':
    unittest.main()