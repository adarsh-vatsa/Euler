import { useEffect, useState } from "react";
import { api, Skill } from "../lib/api";

interface Props {
  onStart: (skillId: number) => void;
}

export function Home({ onStart }: Props) {
  const [skills, setSkills] = useState<Skill[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);

  async function refresh() {
    try {
      setSkills(await api.listSkills());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function seed() {
    setSeeding(true);
    try {
      await api.seedSkills();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSeeding(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold">Euler</h1>
        <p className="mt-1 text-sm text-gray-400">
          Personal learning system. Pick a skill to start.
        </p>
      </header>

      {error && (
        <div className="mb-4 rounded border border-red-700 bg-red-900/30 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {skills && skills.length === 0 && (
        <div className="rounded border border-gray-800 bg-gray-900/40 px-4 py-6 text-center">
          <div className="mb-3 text-sm text-gray-400">No skills yet.</div>
          <button
            onClick={seed}
            disabled={seeding}
            className="rounded bg-gray-100 px-4 py-2 text-sm font-medium text-black hover:bg-white disabled:opacity-50"
          >
            {seeding ? "Seeding…" : "Seed sample skills"}
          </button>
        </div>
      )}

      {skills && skills.length > 0 && (
        <ul className="divide-y divide-gray-800 rounded border border-gray-800">
          {skills.map((s) => (
            <li key={s.id}>
              <button
                onClick={() => onStart(s.id)}
                className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-gray-900"
              >
                <span className="mt-0.5 min-w-[3rem] font-mono text-xs text-gray-500">
                  {s.unit_path}
                </span>
                <span className="flex-1">
                  <span className="block font-medium">{s.name}</span>
                  <span className="mt-0.5 block text-xs text-gray-500">
                    {s.description}
                  </span>
                </span>
                <span className="text-xs text-gray-600">
                  {s.kp_count > 0 ? `${s.kp_count} KPs ready` : "new"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
