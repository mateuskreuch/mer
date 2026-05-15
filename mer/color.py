import functools

COLORS = ["cyan", "green", "yellow", "magenta", "blue", "bright_cyan", "bright_green"]
color_cycle = -1

@functools.cache
def get_unique_color(id: str):
   global color_cycle
   color_cycle += 1
   return COLORS[color_cycle % len(COLORS)]