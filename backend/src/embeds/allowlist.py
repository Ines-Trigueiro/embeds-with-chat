"""The only network resources an embed may load (ADR 0001).

This single list feeds both the Content-Security-Policy on the embed origin
and the system prompt, so the browser enforces exactly what the model is told.
Libraries are pinned by path, so a CSP entry allows one version of one library.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Library:
    name: str
    purpose: str
    base_url: str  # Directory the library is served from; the CSP allows exactly this path.
    files: tuple[str, ...]

    def urls(self) -> list[str]:
        return [self.base_url + f for f in self.files]


CDNJS = "https://cdnjs.cloudflare.com/ajax/libs/"

LIBRARIES: tuple[Library, ...] = (
    Library(
        name="Chart.js 4.4.1",
        purpose="charts",
        base_url=f"{CDNJS}Chart.js/4.4.1/",
        files=("chart.umd.min.js",),
    ),
    Library(
        name="Leaflet 1.9.4",
        purpose="maps (use with OpenStreetMap tiles)",
        base_url=f"{CDNJS}leaflet/1.9.4/",
        files=("leaflet.min.js", "leaflet.min.css"),
    ),
    Library(
        name="D3 7.9.0",
        purpose="custom data visualisations",
        base_url=f"{CDNJS}d3/7.9.0/",
        files=("d3.min.js",),
    ),
)

MAP_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
MAP_TILE_HOST = "https://tile.openstreetmap.org"
MAP_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'


def content_security_policy(embed_origin: str) -> str:
    """The CSP every embed is served with. No `connect-src`: an embed can send nothing anywhere."""
    library_dirs = " ".join(lib.base_url for lib in LIBRARIES)
    directives = {
        "default-src": "'none'",
        "script-src": f"'unsafe-inline' {library_dirs}",
        "style-src": f"'unsafe-inline' {library_dirs}",
        # Leaflet ships marker images inside its library directory.
        "img-src": f"{embed_origin} data: {MAP_TILE_HOST} {library_dirs}",
        "font-src": "data:",
        "connect-src": "'none'",
        "form-action": "'none'",
        "base-uri": "'none'",
        # Forces an opaque origin even when a URL is opened directly, outside <iframe sandbox>.
        "sandbox": "allow-scripts",
    }
    return "; ".join(f"{name} {value}" for name, value in directives.items())
