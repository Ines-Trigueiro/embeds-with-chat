# Guide: calculator

- Inputs are <input type="number"> (or range sliders with a visible value), each with a
  <label>, a unit ("kWh", "øre/kWh") and a sensible default and min/max.
- Recalculate on every input; no "Calculate" button needed.
- Show the result large and clear, with its unit, and a one-line explanation of how it
  was calculated ("forbruk × pris").
- Format numbers for the embed's language: Norwegian and Danish use a space as the
  thousands separator and a comma as the decimal separator (`toLocaleString`).
- Handle empty or invalid input gracefully: show a hint, never "NaN" or "Infinity".
- Put every constant (prices, rates, thresholds) in one clearly named object at the top
  of the script, with a comment saying where it comes from.
