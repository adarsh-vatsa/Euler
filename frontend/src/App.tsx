import { useState } from "react";
import { Home } from "./pages/Home";
import { Lesson } from "./pages/Lesson";

type View = { kind: "home" } | { kind: "lesson"; skillId: number };

export default function App() {
  const [view, setView] = useState<View>({ kind: "home" });

  if (view.kind === "home") {
    return <Home onStart={(skillId) => setView({ kind: "lesson", skillId })} />;
  }
  return (
    <Lesson
      skillId={view.skillId}
      onExit={() => setView({ kind: "home" })}
    />
  );
}
