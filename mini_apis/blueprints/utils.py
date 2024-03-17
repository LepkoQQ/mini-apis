cache = {}


def get_blueprint_routes(current_app, bp):
    if bp.name in cache:
        return cache[bp.name]

    prefix = f"{bp.name}."
    rules = current_app.url_map.iter_rules()
    rules = [rule for rule in rules if rule.endpoint.startswith(prefix)]
    routes = {rule.endpoint: rule.rule for rule in rules}

    cache[bp.name] = routes
    return routes
