export type AnswerFormat = "symbolic" | "numeric" | "mcq";

export interface Skill {
  id: number;
  unit_path: string;
  name: string;
  description: string;
  kp_count: number;
}

export interface KP {
  id: number;
  index: number;
  name: string;
  intro: string;
  worked_example: string;
}

export interface Problem {
  id: number;
  statement: string;
  answer_format: AnswerFormat;
  choices: string[] | null;
}

export interface StartResponse {
  skill_id: number;
  skill_name: string;
  kp: KP;
  problem: Problem;
}

export interface NextAction {
  type: "next_problem" | "next_kp" | "lesson_complete";
  problem: Problem | null;
  kp: KP | null;
}

export interface SubmitResponse {
  correct: boolean;
  normalized_user_answer: string;
  solution_steps: string;
  reason: string;
  next: NextAction;
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${text}`);
  }
  return resp.json();
}

export const api = {
  listSkills: () => request<Skill[]>("/api/skills"),
  seedSkills: () =>
    request<{ created: Skill[]; already_existed: Skill[] }>(
      "/api/skills/seed",
      { method: "POST" }
    ),
  startLesson: (skill_id: number) =>
    request<StartResponse>("/api/lessons/start", {
      method: "POST",
      body: JSON.stringify({ skill_id }),
    }),
  submitAnswer: (
    problem_id: number,
    user_answer: string,
    time_spent_seconds: number
  ) =>
    request<SubmitResponse>("/api/lessons/submit", {
      method: "POST",
      body: JSON.stringify({ problem_id, user_answer, time_spent_seconds }),
    }),
};
