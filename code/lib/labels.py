"""Human-readable variable labels for tables."""

CORE = {
    "Amr": "AMR",
    "redispatch_mw": "Redispatch volume",
    "redispatch_up_mw": "Redispatch volume, up",
    "redispatch_down_mw": "Redispatch volume, down",
    "grid load MW consumption": "Grid load",
    "wind_onsh_potential": "Onshore wind potential",
    "wind_off_potential": "Offshore wind potential",
    "Wind offshore MW capacity": "Offshore wind capacity",
    "Wind onshore MW capacity": "Onshore wind capacity",
    "Photovoltaics MW capacity": "Solar capacity",
    "wind_speed": "Wind speed (m/s)",
    "sol_rad": "Solar irradiance (W/m²)",
    "AMR_active": "AMR activation",
}

PREFIX = {"wind_onsh": "Onshore wind", "wind_off": "Offshore wind",
          "solar": "Solar", "Load": "Load", "hydro_res": "Reservoir hydro"}


def zone(code: str) -> str:
    return code.replace("_", "")          # DK_1 -> DK1


def pretty(name: str) -> str:
    """'wind_onsh_DK_1' -> 'Onshore wind DK1' (Appendix A naming)."""
    if name in CORE:
        return CORE[name]
    for pre, lab in sorted(PREFIX.items(), key=lambda x: -len(x[0])):
        if name.startswith(pre + "_"):
            return f"{lab} {zone(name[len(pre) + 1:])}"
    return name


def pretty_control(name: str) -> str:
    """'wind_onsh_PL' -> 'Onshore wind generation, PL' (Table 8 naming)."""
    for pre, lab in (("wind_onsh", "Onshore wind generation"),
                     ("wind_off", "Offshore wind generation"),
                     ("solar", "Solar generation"), ("Load", "Load"),
                     ("hydro_res", "Reservoir hydro generation")):
        if name.startswith(pre + "_"):
            return f"{lab}, {zone(name[len(pre) + 1:])}"
    return pretty(name)
