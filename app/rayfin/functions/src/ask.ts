import Anthropic from '@anthropic-ai/sdk';

import { FEW_SHOTS } from './few-shots.js';
import { BLOCKED_TABLES, MODEL_CONTEXT } from './model-context.js';

/** What the Ask tab gets back. The app runs `dax` itself, as the signed-in user, so RLS applies to the answer. */
export type AskAnswer = { title: string; explanation: string; dax: string };

// Only the question, the model's names/measures (MODEL_CONTEXT) and a previous DAX error are sent to Claude.
// Query results never leave Fabric: the browser runs the DAX against SM_FreshyFresh_Ops.
const SYSTEM = `You write one DAX query against the Power BI semantic model SM_FreshyFresh_Ops for FreshyFresh Foods,
a fictional refrigerated prepared-foods maker (all data is synthetic, Jul-Sep 2026, timestamps in UTC).
The app runs your query as the signed-in user, with row-level security: a plant QA manager only sees their plant, so
never filter by user or try to bypass security. The result is shown as a table, so return readable columns.

Rules:
- The query starts with EVALUATE (or DEFINE ... EVALUATE). Read-only DAX only.
- Use only the tables, columns and measures listed below. Prefer the existing measures for KPIs: they encode the
  business rules (OTIF = on time and in full; fill rate = cases shipped / ordered; waste rate = Aged Out + Damaged +
  QA Reject cases / cases produced; cold-chain excursion = 30+ minutes above 5.0 C; trip cost, dock wait).
- Show names next to ids (facility_name, customer_name, sku_name). Name calculated columns in plain English.
- Return at most 500 rows (TOPN when a list could be long) and sort the result meaningfully.
- Holds, corrective actions and their timeline (quality_hold, corrective_action, hold_update) are what QA did in the
  app. Rows with quality_hold[status] = "Archived" are demo clean-up: leave them out unless the question asks for
  them, and prefer the hold measures ([Open Holds], [Cases On Hold], [Open Actions], [Overdue Actions]), which do.
- If the question cannot be answered from these tables, return an empty dax and say so in the explanation.

Model:
${MODEL_CONTEXT}

Examples:
${FEW_SHOTS.map((f) => `Q: ${f.question}\n${f.dax}`).join('\n\n')}`;

const ANSWER_SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string', description: 'Short title for the answer table, max 8 words' },
    explanation: { type: 'string', description: '1-3 plain-English sentences: what the table shows and how it is calculated' },
    dax: { type: 'string', description: 'The DAX query, or an empty string if the question cannot be answered' },
  },
  required: ['title', 'explanation', 'dax'],
  additionalProperties: false,
} as const;

/** Server-side guard: the browser runs whatever comes back, so reject anything that is not a plain, RLS-scoped query. */
export function checkDax(dax: string): string | undefined {
  const body = dax.replace(/\/\/.*$|--.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '').trim();
  if (!/^(EVALUATE|DEFINE)\b/i.test(body)) return 'The query must start with EVALUATE or DEFINE.';
  if (/\bINFO\s*\./i.test(body)) return 'Model metadata functions are not allowed.';
  const hit = BLOCKED_TABLES.find((t) => new RegExp(`(^|[^A-Za-z0-9_])'?${t}'?\\s*\\[|\\b${t}\\b`, 'i').test(body));
  return hit ? `Table ${hit} is not row-level secured, so the Ask tab cannot query it.` : undefined;
}

/** Question -> {title, explanation, dax}. Kept free of the Fabric runtime so it can be tested locally. */
export async function answerQuestion(
  apiKey: string,
  question: string,
  previousDax: string,
  previousError: string,
): Promise<AskAnswer> {
  const q = question.trim();
  if (q.length < 3 || q.length > 500) throw new Error('Ask a question between 3 and 500 characters.');

  let prompt = q;
  if (previousDax && previousError) {
    prompt += `\n\nYour previous query failed. Fix it.\nQuery:\n${previousDax}\nError:\n${previousError.slice(0, 1500)}`;
  }

  const client = new Anthropic({ apiKey });
  const response = await client.beta.messages.create({
    model: 'claude-opus-5-5',
    max_tokens: 16000,
    betas: ['server-side-fallback-2026-07-01'],
    fallbacks: 'default',              // a declined request is retried server-side on Anthropic's recommended model
    output_config: { effort: 'medium', format: { type: 'json_schema', schema: ANSWER_SCHEMA } },
    system: [{ type: 'text', text: SYSTEM, cache_control: { type: 'ephemeral' } }],   // stable prefix: cached
    messages: [{ role: 'user', content: prompt }],
  });

  if (response.stop_reason === 'refusal') throw new Error('Claude declined this question. Try rephrasing it.');
  if (response.stop_reason === 'max_tokens') throw new Error('The answer was cut off. Try a narrower question.');
  const text = response.content.find((b) => b.type === 'text');
  if (!text || text.type !== 'text') throw new Error('No answer came back. Try again.');
  const answer = JSON.parse(text.text) as AskAnswer;

  console.log(`askFreshyFresh: ${q.length} chars, ${response.usage.input_tokens} in / ${response.usage.output_tokens} out, `
    + `cache read ${response.usage.cache_read_input_tokens ?? 0}`);
  if (answer.dax) {
    const problem = checkDax(answer.dax);
    if (problem) return { title: 'Not available', explanation: problem, dax: '' };
  }
  return answer;
}
