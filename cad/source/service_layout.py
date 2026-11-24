"""Unscaled service interfaces shared by the solid build and the fit gauges."""

ESP_HEADER_Y = 12.7
USB_PLUG = (12.4, 18.0, 7.6)
USB_WELL_WIDTH = 15.4
USB_WELL_HEIGHT = 10.6


def pd_board_origin(center):
    """Placement of the Adafruit 5807 vendor model in assembly millimetres."""
    return (-10.16, center[1] - 12.304, center[2] - 7 + .3 + 1.9201765)


def pd_socket_position(center):
    return tuple(a + b for a, b in zip(pd_board_origin(center), (10.16, 24.608, 2.67)))
