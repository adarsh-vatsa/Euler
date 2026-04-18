import { useEffect, useRef, useState } from "react";
import { api, KP, Problem, SubmitResponse } from "../lib/api";
import { Markdown } from "../components/Markdown";

type Status =
  | { kind: "loading" }
  | { kind: "ready"; kp: KP; problem: Problem; startedAt: number }
  | { kind: "submitting"; kp: KP; problem: Problem }
  | {
      kind: "feedback";
      kp: KP;
      problem: Problem;
      result: SubmitResponse;
    }
  | { kind: "generating"; kp: KP }
  | { kind: "complete"; skillName: string }
  | { kind: "error"; message: string };

interface Props {
  skillId: number;
  onExit: () => void;
}

export function Lesson({ skillId, onExit }: Props) {
  const [status, setStatus] = useState<Status>({ kind: "loading" });
  const [answer, setAnswer] = useState("");
  const [skillName, setSkillName] = useState("");
  const [showWorkedExample, setShowWorkedExample] = useState(true);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.startLesson(skillId);
        if (cancelled) return;
        setSkillName(res.skill_name);
        setStatus({
          kind: "ready",
          kp: res.kp,
          problem: res.problem,
          startedAt: Date.now(),
        });
      } catch (e) {
        if (cancelled) return;
        setStatus({
          kind: "error",
          message: e instanceof Error ? e.message : String(e),
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [skillId]);

  useEffect(() => {
    if (status.kind === "ready") {
      inputRef.current?.focus();
    }
  }, [status.kind]);

  async function submit() {
    if (status.kind !== "ready") return;
    if (!answer.trim()) return;
    const elapsed = (Date.now() - status.startedAt) / 1000;
    const kp = status.kp;
    const problem = status.problem;
    setStatus({ kind: "submitting", kp, problem });
    try {
      const result = await api.submitAnswer(problem.id, answer, elapsed);
      setStatus({ kind: "feedback", kp, problem, result });
    } catch (e) {
      setStatus({
        kind: "error",
        message: e instanceof Error ? e.message : String(e),
      });
    }
  }

  function advance() {
    if (status.kind !== "feedback") return;
    const { result } = status;
    setAnswer("");
    if (result.next.type === "lesson_complete") {
      setStatus({ kind: "complete", skillName });
      return;
    }
    const nextKp = result.next.kp ?? status.kp;
    const nextProblem = result.next.problem;
    if (!nextProblem) {
      setStatus({
        kind: "error",
        message: "Expected a next problem but got none",
      });
      return;
    }
    // Reset worked-example visibility only when moving to a new KP.
    if (result.next.type === "next_kp") setShowWorkedExample(true);
    setStatus({
      kind: "ready",
      kp: nextKp,
      problem: nextProblem,
      startedAt: Date.now(),
    });
  }

  // Keyboard: Space advances from feedback; Esc exits.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onExit();
        return;
      }
      if (status.kind === "feedback" && e.key === " ") {
        e.preventDefault();
        advance();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (status.kind === "loading" || status.kind === "generating") {
    return (
      <CenteredMessage>
        <div className="text-gray-400">Generating lesson…</div>
      </CenteredMessage>
    );
  }

  if (status.kind === "error") {
    return (
      <CenteredMessage>
        <div className="text-red-400">Error: {status.message}</div>
        <button
          onClick={onExit}
          className="mt-4 rounded bg-gray-800 px-4 py-2 hover:bg-gray-700"
        >
          Back
        </button>
      </CenteredMessage>
    );
  }

  if (status.kind === "complete") {
    return (
      <CenteredMessage>
        <div className="text-2xl font-semibold">Lesson complete</div>
        <div className="mt-2 text-gray-400">{status.skillName}</div>
        <button
          onClick={onExit}
          className="mt-6 rounded bg-green-700 px-5 py-2 hover:bg-green-600"
        >
          Continue
        </button>
      </CenteredMessage>
    );
  }

  const kp = status.kp;
  const problem = status.kind === "ready" || status.kind === "submitting" || status.kind === "feedback"
    ? status.problem
    : null;

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-10">
      <header className="mb-6 flex items-center justify-between text-sm text-gray-400">
        <div>
          <span className="mr-2">{skillName}</span>
          <span className="text-gray-600">·</span>
          <span className="ml-2">
            KP {kp.index + 1}: {kp.name}
          </span>
        </div>
        <button
          onClick={onExit}
          className="rounded border border-gray-700 px-2 py-1 text-xs hover:border-gray-500"
        >
          Esc to exit
        </button>
      </header>

      <section className="mb-6 rounded border border-gray-800 bg-gray-900/50">
        <button
          onClick={() => setShowWorkedExample(!showWorkedExample)}
          className="flex w-full items-center justify-between px-4 py-2 text-left text-sm text-gray-400 hover:bg-gray-900"
        >
          <span>
            {showWorkedExample ? "▾" : "▸"} Worked example
          </span>
          <span className="text-xs text-gray-600">{kp.intro}</span>
        </button>
        {showWorkedExample && (
          <div className="border-t border-gray-800 px-4 py-4">
            <Markdown>{kp.worked_example}</Markdown>
          </div>
        )}
      </section>

      {problem && (
        <section className="mb-6">
          <div className="mb-2 text-xs uppercase tracking-wider text-gray-500">
            Problem
          </div>
          <div className="rounded border border-gray-800 bg-gray-900/50 px-4 py-4">
            <Markdown>{problem.statement}</Markdown>
            {problem.choices && (
              <ul className="mt-4 space-y-1 text-sm">
                {problem.choices.map((c, i) => (
                  <li key={i}>
                    <span className="mr-2 font-mono text-gray-500">
                      {String.fromCharCode(65 + i)}.
                    </span>
                    <Markdown className="inline">{c}</Markdown>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}

      {status.kind === "ready" && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
          className="flex gap-2"
        >
          <input
            ref={inputRef}
            type="text"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder={
              problem?.answer_format === "mcq"
                ? "Type the letter of your answer (A, B, C, …)"
                : problem?.answer_format === "numeric"
                  ? "Type your numeric answer"
                  : "Type your answer (ASCII math: x^2, sqrt(2), pi, …)"
            }
            autoComplete="off"
            autoFocus
            className="flex-1 rounded border border-gray-700 bg-black px-3 py-2 font-mono focus:border-gray-400 focus:outline-none"
          />
          <button
            type="submit"
            className="rounded bg-gray-100 px-4 py-2 font-medium text-black hover:bg-white"
          >
            Submit ↵
          </button>
        </form>
      )}

      {status.kind === "submitting" && (
        <div className="text-sm text-gray-500">Grading…</div>
      )}

      {status.kind === "feedback" && (
        <Feedback result={status.result} onAdvance={advance} />
      )}
    </div>
  );
}

function Feedback({
  result,
  onAdvance,
}: {
  result: SubmitResponse;
  onAdvance: () => void;
}) {
  const ok = result.correct;
  return (
    <div
      className={`rounded border px-4 py-4 ${
        ok
          ? "border-green-700 bg-green-900/20"
          : "border-red-700 bg-red-900/20"
      }`}
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="font-semibold">
          {ok ? "Correct" : "Not quite"}
        </div>
        <button
          onClick={onAdvance}
          className="rounded bg-gray-100 px-3 py-1 text-sm font-medium text-black hover:bg-white"
        >
          {result.next.type === "lesson_complete" ? "Finish" : "Next"} ␣
        </button>
      </div>
      {result.reason && (
        <div className="mb-2 text-xs text-gray-400">{result.reason}</div>
      )}
      <div className="mb-2 text-xs uppercase tracking-wider text-gray-500">
        Solution
      </div>
      <Markdown>{result.solution_steps}</Markdown>
    </div>
  );
}

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="flex flex-col items-center text-center">{children}</div>
    </div>
  );
}
