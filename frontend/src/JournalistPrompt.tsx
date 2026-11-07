import { useState } from "react";

export function JournalistPrompt({ onSubmit }: { onSubmit: (name: string) => void }) {
  const [name, setName] = useState("");
  const trimmed = name.trim();

  return (
    <form
      className="card prompt"
      onSubmit={(event) => {
        event.preventDefault();
        if (trimmed) onSubmit(trimmed);
      }}
    >
      <h1>Embeds with chat</h1>
      <label>
        Your name
        <input autoFocus value={name} maxLength={64} onChange={(e) => setName(e.target.value)} />
      </label>
      <p className="hint">No password: your name only keeps your embeds apart from others'.</p>
      <button type="submit" disabled={!trimmed}>
        Continue
      </button>
    </form>
  );
}
