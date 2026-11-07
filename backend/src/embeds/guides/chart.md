# Guide: chart

- Use Chart.js from the allowed URL, unless the journalist needs something Chart.js
  can't draw; then D3.
- Pick the simplest chart that answers the question: bars for comparing categories,
  lines for change over time. Avoid pie charts with more than four slices and never use 3D.
- Give the chart a title that states the finding ("Strømprisen doblet seg i 2022"), not
  just the topic, plus axis labels with units.
- Set `maintainAspectRatio: false` inside a container with a height that suits mobile
  (around 300px), so the chart fits narrow screens.
- Start bar charts' value axis at zero.
- If you print values next to bars, leave room for them (`layout: { padding: { right: 48 } }`
  for horizontal bars), so the largest value isn't cut off on narrow screens.
- Use at most a handful of colours, with sufficient contrast. Label series directly or
  with a legend, never by colour alone.
- Include the data as a visually hidden <table> as well, so screen readers can read it.
- Show the source and date under the chart.
