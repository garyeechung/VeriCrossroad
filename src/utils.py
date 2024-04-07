from itertools import combinations


def convert_greenlights_to_routes(greenlights, n_ways):
    routes = []
    for way, lights in greenlights.items():
        assert way in range(n_ways), f"Invalid way {way}"
        for light in lights:
            err_msg = f"Way {way} has invalid light {light}"
            assert light in range(1, n_ways), err_msg
            new_route = (way, (way + light) % n_ways)
            if new_route not in routes:
                routes.append(new_route)
    routes = sorted(routes, key=lambda x: (x[0], x[1]), reverse=False)
    return routes


def get_combinations(routes, n_ways):
    route_pairs_candidates = list(combinations(routes, 2))
    route_pairs = []
    for (s1, e1), (s2, e2) in route_pairs_candidates:
        if s1 == s2 or e1 == e2:
            continue
        elif e1 == s2:
            route_pairs.append(((s1, e1), (s2, e2)))
        elif e2 == s1:
            route_pairs.append(((s2, e2), (s1, e1)))
        elif s1 > s2:
            route_pairs.append(((s2, e2), (s1, e1)))
        else:
            route_pairs.append(((s1, e1), (s2, e2)))
    
    shifted_route_pairs = []
    for (s1, e1), (s2, e2) in route_pairs:
        shift = s1
        s1 = (s1 - shift) % n_ways
        e1 = (e1 - shift) % n_ways
        s2 = (s2 - shift) % n_ways
        e2 = (e2 - shift) % n_ways
        shifted_route_pairs.append(((s1, e1), (s2, e2), shift))

    return shifted_route_pairs

if __name__ == '__main__':
    greenlights = {
        0: [1, 2, 3],
        1: [2],
        2: [3],
        3: [2]
    }
    routes = convert_greenlights_to_routes(greenlights, 4)
    print(routes)

    route_pairs = get_combinations(routes, 4)
    print(route_pairs)
