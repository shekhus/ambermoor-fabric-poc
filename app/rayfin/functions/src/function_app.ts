import { UserDataFunctions, type RayfinContext } from '@microsoft/fabric-user-data-functions';

import { answerQuestion, type AskAnswer } from './ask.js';

const udf = new UserDataFunctions();

/** The UDF host turns an uncaught error into a generic "InternalError", so name the real cause (never the key). */
function describe(err: unknown): string {
  if (!(err instanceof Error)) return String(err);
  const status = (err as { status?: number }).status;
  const cause = (err as { cause?: { code?: string; message?: string } }).cause;
  const detail = cause ? ` (cause: ${cause.code ?? ''} ${cause.message ?? ''})`.replace(/\s+\)/, ')') : '';
  return `${err.name}${status ? ` ${status}` : ''}: ${err.message}${detail}`.replace(/sk-ant-[\w-]+/g, '[redacted]');
}

/**
 * Ask FreshyFresh: natural-language question -> DAX (via Claude). The app runs the DAX itself as the signed-in user,
 * so row-level security shapes the answer. Logic lives in ask.ts; this file wires in the secret and reports errors.
 */
udf.func('askFreshyFresh', async (
  question: string,
  previousDax: string,
  previousError: string,
  ctx: RayfinContext,
): Promise<AskAnswer> => {
  try {
    return await answerQuestion(ctx.Secrets.ANTHROPIC_API_KEY, question, previousDax, previousError);
  } catch (err) {
    console.error('askFreshyFresh failed:', describe(err));
    return { title: 'Could not answer', explanation: describe(err), dax: '' };
  }
}, []);
