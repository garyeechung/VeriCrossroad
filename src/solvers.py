from itertools import product
import copy


from z3 import And, Ints, Not, Or, Solver, sat

from .utils import convert_greenlights_to_routes, get_combinations


class Collision:

    def __init__(self, greenlights, n_ways: int = None):
        self.greenlights = greenlights
        if n_ways is None:
            self.n_ways = max(greenlights.keys()) + 1
        else:
            self.n_ways = n_ways

        self.reset_solver()
    
    def reset_solver(self):
        self.routes = convert_greenlights_to_routes(self.greenlights, self.n_ways)
        self.route_pairs = get_combinations(self.routes, self.n_ways)
        self.solver = Solver()

        self.s1, self.e1, self.s2, self.e2 = Ints('s1 e1 s2 e2')

        # add possible route pairs
        route_pairs_constraints = []
        for pair in self.route_pairs:
            route_pairs_constraints.append(
                And(
                    self.s1 == pair[0][0],
                    self.e1 == pair[0][1],
                    self.s2 == pair[1][0],
                    self.e2 == pair[1][1]
                )
            )
        self.solver.add(Or(route_pairs_constraints))

        # collision constraint 1
        collision_constraints_1 = And(
            0 < (self.s2-self.s1)%self.n_ways,
            (self.s2-self.s1)%self.n_ways < (self.e1-self.s1)%self.n_ways,
            Or((self.e1-self.s1)%self.n_ways < (self.e2-self.s1)%self.n_ways,
               (self.e2-self.s1)%self.n_ways == 0)
        )

        # collision constraint 2
        collision_constraints_2 = And(
            0 < (self.e2-self.s1)%self.n_ways,
            (self.e2-self.s1)%self.n_ways < (self.e1-self.s1)%self.n_ways,
            (self.e1-self.s1)%self.n_ways <= (self.s2-self.s1)%self.n_ways
        )

        self.solver.add(Or(collision_constraints_1, collision_constraints_2))

    def check_unsafe_routes(self, verbose=False):
        unsafe_routes = dict()
        if verbose:
            print("Checking collision...")
        while self.solver.check() == sat:
            sol = self.solver.model()
            start_1 = sol[self.s1].as_long()
            end_1 = sol[self.e1].as_long()
            start_2 = sol[self.s2].as_long()
            end_2 = sol[self.e2].as_long()
            if (start_1, end_1) not in unsafe_routes:
                unsafe_routes[(start_1, end_1)] = 1
            else:
                unsafe_routes[(start_1, end_1)] += 1
            
            if (start_2, end_2) not in unsafe_routes:
                unsafe_routes[(start_2, end_2)] = 1
            else:
                unsafe_routes[(start_2, end_2)] += 1
            
            if verbose:
                print(f"{start_1} -> {end_1}; {start_2} -> {end_2}")
            
            self.solver.add(Not(And(
                self.s1 == sol[self.s1],
                self.e1 == sol[self.e1],
                self.s2 == sol[self.s2],
                self.e2 == sol[self.e2]
            )))

        if verbose:
            print("-" * 50)
            print("Unsafe routes:")
            for route, count in unsafe_routes.items():
                print(f"{route[0]} -> {route[1]}: {count}")
        
        return unsafe_routes
    
    def remove_greenlight(self, way: int, light: int):
        self.greenlights[way].remove(light)
        self.reset_solver()

class AddSafeRoute:
    def __init__(self, greenlights, n_ways: int = None):
        self.greenlights = greenlights
        if n_ways is None:
            self.n_ways = max(greenlights.keys()) + 1
        else:
            self.n_ways = n_ways
        
        self.existing_routes = convert_greenlights_to_routes(self.greenlights, self.n_ways)
        self.candidate_routes = (product(range(self.n_ways), range(self.n_ways)))
        self.candidate_routes = [
            route
            for route in self.candidate_routes
            if (route not in self.existing_routes) and (route[0] != route[1])
        ]
    
    def get_safe_candidates(self, verbose=False):
        safe_routes = []
        for route in self.candidate_routes:
            new_greenlights = copy.deepcopy(self.greenlights)
            new_greenlights[route[0]].append((route[1] - route[0]) % self.n_ways)

            collision = Collision(new_greenlights, self.n_ways)
            unsafe_routes = collision.check_unsafe_routes(verbose=False)
            if len(unsafe_routes) == 0:
                safe_routes.append(route)
                if verbose:
                    print(f"Safe route: {route[0]} -> {route[1]}")
        return safe_routes
    
    def add_safe_route(self, start: int, end: int):
        self.greenlights[start].append((end - start) % self.n_ways)
        self.existing_routes = convert_greenlights_to_routes(self.greenlights, self.n_ways)
        self.candidate_routes.remove((start, end))


if __name__ == '__main__':
    greenlights = {
        0: [1, 2],
        1: [3],
        2: [1, 3],
        3: [2, 3],
    }

    print("=" * 50)
    collision = Collision(greenlights, 4)
    collision.check_unsafe_routes(verbose=True)

    print("=" * 50)
    start, end = 2, 1
    collision.remove_greenlight(start, (end - start) % collision.n_ways)

    print("=" * 50)
    collision.check_unsafe_routes(verbose=True)


    start, end = 1, 0
    collision.remove_greenlight(start, (end - start) % collision.n_ways)
    print(collision.greenlights)
    collision.check_unsafe_routes(verbose=True)
