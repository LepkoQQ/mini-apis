cache = {}


def get_blueprint_routes(current_app, bp):
    if bp.name in cache:
        return cache[bp.name]

    prefix = f"{bp.name}."
    rules = current_app.url_map.iter_rules()
    routes = {
        rule.endpoint: current_app.url_for(rule.endpoint)
        for rule in rules
        if rule.endpoint.startswith(prefix)
    }

    cache[bp.name] = routes
    return routes
