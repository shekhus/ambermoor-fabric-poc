import { useState, type FormEvent } from "react";
import { DataGrid } from "@microsoft/fabric-datagrid";
import type { ColumnDef, DataTable } from "@microsoft/fabric-visuals-core";
import { Sparkles } from "lucide-react";

import { useThemeContext } from "@/hooks/theme.context";
import { getFabricClient } from "@/lib/fabric-client";
import { askFreshyFresh, type AskAnswer } from "@/services/ask.service";
import { Button, Empty, ErrorBanner, inputClass, Skeleton } from "@/components/ui";
import { cn } from "@/lib/utils";

const EXAMPLES = [
    "Which plant has the highest waste rate?",
    "Show OTIF and on-time % by plant",
    "Which shipments had a cold-chain excursion, and on which truck?",
    "What are the 5 most expensive delivery lanes?",
    "Are late deliveries caused by dock waits?",
    "Which customers received product made with ingredient lot ILOT-P02-ING02-20260908?",
];

type Phase = "idle" | "writing" | "running" | "fixing";
const PHASE_TEXT: Record<Phase, string> = {
    idle: "",
    writing: "Writing the query… this takes 10–30 seconds.",
    running: "Running it on the model with your access…",
    fixing: "The first query failed in the model; asking for a fix…",
};

/** DAX column names ("dim_facility[facility_name]", "[Waste Rate %]") -> DataGrid-safe defs with readable labels. */
function shape(table: { columns: { name: string }[]; rows: unknown[][] }): DataTable {
    const columns: ColumnDef[] = table.columns.map((c, i) => {
        const label = (c.name.match(/\[([^\]]+)\]$/)?.[1] ?? c.name).replace(/_/g, " ");
        const values = table.rows.map((r) => r[i]).filter((v) => v !== null && v !== undefined);
        const numeric = values.length > 0 && values.every((v) => typeof v === "number");
        const format = !numeric ? undefined
            : label.includes("%") ? "0.0%"
            : values.every((v) => Number.isInteger(v)) ? "#,0" : "#,0.00";
        return { name: `c${i}`, displayName: label, format };
    });
    const rows = table.rows.map((r) => r.map((v) => (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T00:00:00/.test(v) ? v.slice(0, 10) : v)));
    return { columns, rows };
}

/** Runs DAX as the signed-in user (the embedded app's identity), so RLS applies. SDK errors come back, not thrown. */
async function runDax(dax: string): Promise<{ table?: DataTable; error?: string }> {
    const result = await getFabricClient().semanticModel("ambermoor").query(dax, { bypassCache: false });
    return result.status === "success" ? { table: shape(result.table) } : { error: result.error.message };
}

export function AskPage({ scopeLabel }: { scopeLabel: string }) {
    const { theme } = useThemeContext();
    const [question, setQuestion] = useState("");
    const [asked, setAsked] = useState("");
    const [phase, setPhase] = useState<Phase>("idle");
    const [answer, setAnswer] = useState<AskAnswer | undefined>();
    const [table, setTable] = useState<DataTable | undefined>();
    const [error, setError] = useState<string | undefined>();

    async function submit(e?: FormEvent, q = question) {
        e?.preventDefault();
        const text = q.trim();
        if (text.length < 3 || phase !== "idle") return;
        setQuestion(text);
        setAsked(text);
        setAnswer(undefined);
        setTable(undefined);
        setError(undefined);
        try {
            setPhase("writing");
            let a = await askFreshyFresh(text);
            let run = a.dax ? (setPhase("running"), await runDax(a.dax)) : {};
            if (run.error) {
                // A query that fails in the model goes back to Claude once, with the error, to be fixed.
                setPhase("fixing");
                a = await askFreshyFresh(text, a.dax, run.error);
                run = a.dax ? (setPhase("running"), await runDax(a.dax)) : {};
            }
            setAnswer(a);
            setTable(run.table);
            if (run.error) setError(`The query failed twice: ${run.error}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        } finally {
            setPhase("idle");
        }
    }

    const busy = phase !== "idle";
    return (
        <div className="flex flex-col gap-grid">
            <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-2">
                <label htmlFor="ask" className="flex items-center gap-2 text-400 font-semibold text-card-foreground">
                    <Sparkles className="icon-size-200 text-primary" aria-hidden /> Ask FreshyFresh
                </label>
                <div className="flex flex-col gap-2 sm:flex-row">
                    <input id="ask" className={inputClass} value={question} maxLength={500} autoComplete="off"
                        placeholder="e.g. Which plant had the most waste in August?"
                        onChange={(e) => setQuestion(e.target.value)} />
                    <Button type="submit" disabled={busy || question.trim().length < 3}>{busy ? "Thinking…" : "Ask"}</Button>
                </div>
                <div className="flex flex-wrap gap-2" role="group" aria-label="Example questions">
                    {EXAMPLES.map((ex) => (
                        <button key={ex} type="button" disabled={busy} onClick={() => void submit(undefined, ex)}
                            className={cn("rounded-full border border-border bg-card px-3 py-1 text-200 text-card-foreground",
                                "hover:bg-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60")}>
                            {ex}
                        </button>
                    ))}
                </div>
                <p className="text-200 text-muted-foreground">
                    Answers use your access ({scopeLabel}). Your question and the model's table and measure names go to
                    Claude (Anthropic) to write the query; the data itself stays in Fabric.
                </p>
            </form>

            {busy && (
                <div className="flex flex-col gap-2" aria-live="polite">
                    <span className="text-300 text-muted-foreground">{PHASE_TEXT[phase]}</span>
                    <Skeleton className="h-48" />
                </div>
            )}
            {!busy && error && <ErrorBanner error={error} />}

            {!busy && answer && (
                <section className="flex flex-col gap-3" aria-live="polite">
                    <div>
                        <h2 className="text-500 font-semibold">{answer.title}</h2>
                        <p className="text-300 text-muted-foreground">{answer.explanation}</p>
                    </div>
                    {table && (table.rows.length === 0
                        ? <Empty>No rows. With your access this question has no data.</Empty>
                        : <DataGrid data={table} theme={theme} header={{ title: answer.title, subtitle: asked }} />)}
                    {answer.dax && (
                        <details className="rounded-lg border border-border bg-card p-3 text-200">
                            <summary className="cursor-pointer font-medium text-card-foreground">Show the DAX query</summary>
                            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-muted-foreground">{answer.dax}</pre>
                        </details>
                    )}
                </section>
            )}
        </div>
    );
}
