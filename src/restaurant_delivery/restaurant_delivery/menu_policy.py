"""Read-only menu policy. Nav2's native SpeedLimit topic applies the limit."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MenuPolicy:
    name: str
    max_speed_mps: float


def read_policy(data, menu):
    menu = menu.upper()
    if menu not in ('NORMAL', 'SOUP'):
        raise ValueError('UNSUPPORTED_MENU: ' + menu)
    speed = float(data[menu]['max_speed_mps'])
    if not 0.0 < speed < 0.5:
        raise ValueError('INVALID_MENU_SPEED')
    if float(data['SOUP']['max_speed_mps']) >= float(data['NORMAL']['max_speed_mps']):
        raise ValueError('SOUP_MUST_BE_SLOWER')
    return MenuPolicy(menu, speed)
