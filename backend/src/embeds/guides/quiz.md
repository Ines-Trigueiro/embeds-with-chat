# Guide: quiz

- One question at a time, with a visible progress indicator ("Spørsmål 2 av 8").
- Answer options are real <button> elements in a list, large enough to tap (at least 44px high).
- After an answer: lock the options, show clearly whether it was right (text, not only
  colour) and a one- or two-sentence explanation, then a "Neste" / "Next" button.
- At the end: the score, a short verdict, and a "Prøv igjen" / "Try again" button that resets.
- Keep all questions and answers in one JavaScript array at the top of the script, so
  the journalist's later changes ("change question 3") are easy to apply.
- Never invent facts for questions. If the journalist only gave a topic, write clearly
  marked placeholder questions and ask them for the real ones.
- Nothing is sent anywhere: scores live only in the reader's page and vanish on reload.
