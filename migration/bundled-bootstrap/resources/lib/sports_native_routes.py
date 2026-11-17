"""Allowlisted native addon routes shared by catalog serialization and playback."""
import sports_crew_routes as crew
import sports_loop_routes as loop


def route_kind(address):
    if crew.valid_route(address):
        return crew.NAME
    if loop.valid_route(address):
        return loop.NAME
    return None


def source_rank(name):
    if name.startswith('Crew '):
        return 0
    return 1 + loop.source_rank(name) if name.startswith('Loop ') else 100


def prepare_proxy(addresses=()):
    # Crew-only playback must never initialize Loop/JetExtractors.
    if any(crew.valid_route(address) for address in addresses):
        crew.wait_for_listing()
    return loop.prepare_proxy() if any(loop.valid_route(address) for address in addresses) else False
