from rules import Rule
from expressions import expression_from_list, Variable, Constant
from substitution import Substitution


class RuleIsNot(Rule):
    def __init__(self, rules_db):
        Rule.__init__(self, [], expression_from_list([Variable("X"), rules_db.add_constant_by_name("is_not"),
                                                      Variable("Y")]),
                      rules_db.add_constant_by_name("is_not_rule"), "(built-in)", rules_db)

    def unify(self, goal):
        subs = self.conclusion.unify(goal)
        if subs is not None and len(subs) == 2 and all(v in subs for v in self.variables):
            xy = list(self.variables)
            if subs[xy[0]] is not subs[xy[1]]:
                return subs

        return None


class RuleAtom(Rule):
    def __init__(self, rules_db):
        Rule.__init__(self, [], expression_from_list([rules_db.add_constant_by_name("atom"), Variable("X")]),
                      rules_db.add_constant_by_name("atom_rule"), "(built-in)", rules_db)

    def unify(self, goal):
        subs = self.conclusion.unify(goal)
        if subs is not None and len(subs) == 1 and all(v in subs for v in self.variables):
            x = list(self.variables)
            if isinstance(subs[x[0]], Constant):
                return subs

        return None


class RuleNewAtom(Rule):
    def __init__(self, rules_db):
        Rule.__init__(self, [], expression_from_list([rules_db.add_constant_by_name("new_atom"), Variable("X")]),
                      rules_db.add_constant_by_name("new_atom_rule"), "(built-in)", rules_db)

    def unify(self, goal):
        subs = self.conclusion.unify(goal)
        if subs is not None and len(subs) == 1:
            x = list(self.variables)[0]
            lhs, rhs = list(subs.items())[0]
            if rhs is x:
                lhs, rhs = rhs, lhs

            if isinstance(rhs, Variable):
                res = Substitution()
                res.replace(rhs, self.rules_db.introduce_constant())
                return res

        return None


def add_builtins(rules_db):
    rules_db.add_rule(Rule([], expression_from_list([Variable("X"), rules_db.add_constant_by_name("is"),
                                                     Variable("X")]),
                      rules_db.add_constant_by_name("is_rule"), "(built-in)", rules_db))

    rules_db.add_rule(RuleIsNot(rules_db))
    rules_db.add_rule(RuleAtom(rules_db))
    rules_db.add_rule(RuleNewAtom(rules_db))
