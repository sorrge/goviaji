import search
from substitution import Substitution
from expressions import Expression
from enum import Enum


class GoalProvedMark:
    def __init__(self, goal_hash, result):
        self.hash = goal_hash
        self.result = result

    def to_str(self):
        return "<mark hash %d as %s>" % (self.hash, self.result)


class FailMark:
    def __init__(self, goal_check_hash=None): # proof fails if a goal with goal_check_hash is proven
        self.goal_check_hash = goal_check_hash

    def to_str(self):
        return "<fail>" if self.goal_check_hash is None else "<fail if hash %d is proven>" % self.goal_check_hash


def prove_dfs(rules, proposition, steps_budget=None, tried_goals=None, verbose=False):
    if verbose:
        print("Starting proof of \"%s\"" % ", ".join(p.to_str() for p in proposition))

    start = Substitution(), proposition

    if tried_goals is None:
        tried_goals = {}

    def accept_proof_marks(goals):
        while goals:
            if isinstance(goals[0], GoalProvedMark):
                if goals[0].hash not in tried_goals:
                    if verbose:
                        print("*** hash=%d marked as %s" % (goals[0].hash, goals[0].result))

                    tried_goals[goals[0].hash] = goals[0].result

                goals.pop(0)
            elif isinstance(goals[0], FailMark) and goals[0].goal_check_hash and \
                    (goals[0].goal_check_hash not in tried_goals or
                         not tried_goals[goals[0].goal_check_hash]):
                goals.pop(0)
            else:
                break

    def gen_alternative_steps(node):
        _, prop = node
        if verbose:
            print("Trying proposition %s" % ", ".join(g.to_str() for g in prop))

        accept_proof_marks(prop)

        if not prop:
            yield Substitution(), []
            return

        first_goal = prop[0]
        rest_goals = prop[1:]

        if isinstance(first_goal, FailMark):
            return

        h = first_goal.get_hash()
        is_ground = first_goal.is_ground()

        if verbose:
            print("Current goal is \"%s\", hash=%d, %s" %
                  (first_goal.to_str(), h, "ground" if is_ground else "not ground"))

        if h in tried_goals:
            proven = tried_goals[h]
            if proven:
                if is_ground:
                    yield from gen_alternative_steps((Substitution(), rest_goals))
                    return
            else:
                return

        continuations = []
        #print("Goal: %s" % first_goal.to_str())
        for new_subs, rule in rules.get_applicable_rules(first_goal):
            if verbose:
                print("\tRule %s is applicable with substitution [%s]" % (rule.name, new_subs))

            if not rule.premises:
                if verbose:
                    print("\t\t...no premises, goal proven")

                accept_proof_marks(rest_goals)
                if is_ground:
                    if verbose:
                        print("\t\t-> no branching, transferring directly to next subgoal")

                    yield from gen_alternative_steps((Substitution(), rest_goals))
                    return

                unused_subs = new_subs.replacements.keys() & rule.variables
                for v in unused_subs:
                    del new_subs.replacements[v]

                continuations.append((new_subs,
                                      [new_subs.apply(g) if isinstance(g, Expression) else g for g in rest_goals]))
            else:
                new_goals = list(map(new_subs.apply, rule.premises))
                new_goals_vars = set()
                for e in new_goals:
                   e.collect_variables(new_goals_vars)

                refresh_subs = rules.refreshing_substitution(new_goals_vars & rule.variables)
                new_goals = list(map(refresh_subs.apply, new_goals))
                new_subs.compose(refresh_subs, add=False)

                new_goals_with_marks = []
                if is_ground:
                    new_goals_with_marks.append(FailMark(h))

                rule_failed = False
                for g in new_goals:
                    sub_hash = g.get_hash()
                    if verbose:
                        print("\t\tpremise \"%s\", hash=%d" % (g.to_str(), sub_hash))

                    if sub_hash in tried_goals:
                        proven = tried_goals[sub_hash]
                        if proven:
                            if g.is_ground():
                                if verbose:
                                    print("\t\t\talready proven; skipping premise")

                                continue
                        else:
                            if verbose:
                                print("\t\t\talready proven to be false; rule failed")

                            rule_failed = True
                            break

                    new_goals_with_marks.append(g)
                    new_goals_with_marks.append(GoalProvedMark(sub_hash, True))

                if not rule_failed:
                    if not new_goals_with_marks:
                        accept_proof_marks(rest_goals)
                        if is_ground:
                            yield from gen_alternative_steps((Substitution(), rest_goals))
                            return

                    continuations.append((new_subs, new_goals_with_marks +
                          [new_subs.apply(g) if isinstance(g, Expression) else g for g in rest_goals]))

        if verbose:
            if not continuations:
                print("No applicable rules, goal failed")
            else:
                print("%d branches generated" % len(continuations))

        if not continuations:
            tried_goals[h] = False
        else:
            yield from continuations
            yield Substitution(), [GoalProvedMark(h, False), FailMark()]

    def is_goal(node):
        subs, prop = node
        return all(isinstance(g, GoalProvedMark) for g in prop)

    vars_in_proposition = set()
    for e in proposition:
        e.collect_variables(vars_in_proposition)

    for steps_taken, path in search.depth_first_search(start, gen_alternative_steps, is_goal, steps_budget):
        if path is None:
            yield steps_taken, None
            return

        full_subs = path[0][0]
        for subs, prop in path[1:]:
            full_subs.compose(subs)

        full_subs.filter_variables(vars_in_proposition)
        yield steps_taken, full_subs
