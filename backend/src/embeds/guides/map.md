# Guide: map

- Use Leaflet from the allowed URLs (both the JS and the CSS file), with the
  OpenStreetMap tiles and attribution exactly as given. No other tile servers.
- Give the map container an explicit height (around 350px on mobile) and set the view
  to fit the features (`fitBounds`), not a hardcoded zoom.
- Disable scroll-wheel zoom (`scrollWheelZoom: false`) so readers scrolling the article
  don't get trapped in the map.
- Draw lines (routes, bike lanes) with `L.polyline` and areas with `L.polygon`; give
  each a popup with its name and a short description.
- Add a small legend if there is more than one kind of feature.
- Coordinates must come from the journalist. Never guess coordinates for real places;
  if they're missing, ask for them or use an obviously placeholder shape and say so.
- Below the map, list the features as text too, for readers who can't use the map.
