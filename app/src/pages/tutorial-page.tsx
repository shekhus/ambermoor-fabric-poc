import { useState } from "react";
import { GraduationCap, RotateCcw } from "lucide-react";

import { resetMyOpenHolds, type Hold } from "@/services/holds.service";
import { Button, ErrorBanner } from "@/components/ui";
import { cn } from "@/lib/utils";

type Tab = "pulse" | "trace" | "holds" | "fleet" | "ask";

/** One guided step. Expected numbers come from agent/golden_answers.json (network) and the P03 test (21 Oct 2026). */
interface Step {
    tab: Tab;
    title: string;
    doThis: string;
    network: string;
    plant: string;
    why: string;
}

const STEPS: Step[] = [
    {
        tab: "pulse", title: "1. Check plant health",
        doThis: "Open Plant pulse and read the six tiles at the top.",
        network: "Fill rate 99.54%, cold-chain excursions 4, open holds 0 after a reset.",
        plant: "P03: 35,338 cases produced, waste 1.46%, OTIF 91.1%, 4 excursions (all on truck TRK-117).",
        why: "A plant manager sees the day's health in 10 seconds. Every tile is a measure defined once in the semantic model.",
    },
    {
        tab: "pulse", title: "2. Spot where deliveries are late",
        doThis: "On Plant pulse, keep the Foodservice channel and read the on-time heatmap.",
        network: "P07 Southeast DC on Mondays is the weakest cell: about 64% on time.",
        plant: "Only your own plant's row is shown.",
        why: "The heatmap finds a weekly pattern without anyone writing a query.",
    },
    {
        tab: "fleet", title: "3. Find out why P07 is late",
        doThis: "Open Fleet & freight. Look for the red bar and the 'late trips caused by dock wait' tile.",
        network: "P07 is red: 14 late trips, all waited over 2 h at the dock (6.26 h on average). Trip cost $3,957,157; P08 has the highest cost per case ($31.93).",
        plant: "P03: 539 trips, about $586,410, no late trips caused by dock waits.",
        why: "It separates dock problems from road problems, and shows what each delivery costs.",
    },
    {
        tab: "trace", title: "4. Run a recall",
        doThis: "Open Lot trace and enter ingredient lot ILOT-P02-ING02-20260908 (the one in supplier notice SN-2026-001).",
        network: "36 finished lots, 145 cases shipped, 10 customers.",
        plant: "P03 sees nothing: those lots were made at P02. That is row-level security working.",
        why: "A recall answered in a minute instead of days of spreadsheets.",
    },
    {
        tab: "trace", title: "5. Put a lot on hold",
        doThis: "In the lot list, select a lot and click Place hold. Network users only: a plant user can only hold their own plant's lots.",
        network: "The Open holds tile and the badge on Holds & actions go up by one.",
        plant: "Skip this step, or use a lot from your own plant.",
        why: "Action is taken where the problem is found, and recorded with your name, not in an email.",
    },
    {
        tab: "holds", title: "6. Follow the hold through",
        doThis: "Open Holds & actions, select your hold, add a corrective action, then read the timeline.",
        network: "Your hold is there with your name; each change appears in the timeline.",
        plant: "Same, for holds at your plant.",
        why: "Auditors ask who held or released a lot and why. The app keeps that trail.",
    },
    {
        tab: "ask", title: "7. Ask in plain English",
        doThis: "Open Ask and click 'Which plant has the highest waste rate?'. Open 'Show the DAX query'.",
        network: "A table of 8 plants, P01 first (about 4.5%).",
        plant: "Only P03 (about 1.5%): the same question answers with your access.",
        why: "Questions nobody built a page for, without an analyst. Only the question and table names go to Claude.",
    },
    {
        tab: "pulse", title: "8. Clean up",
        doThis: "Click Reset demo below.",
        network: "Your open holds are released and their open actions cancelled. Open holds goes back to 0.",
        plant: "Same, for holds you opened.",
        why: "The next person starts clean. Nothing is deleted: the reset itself is logged on each hold.",
    },
];

export function TutorialPage({ scopeLabel, isNetwork, holds, onGo, onReset }: {
    scopeLabel: string;
    isNetwork: boolean;
    holds: Hold[];
    onGo: (tab: Tab) => void;
    onReset: () => void;
}) {
    const [done, setDone] = useState<Set<number>>(new Set());
    const [confirming, setConfirming] = useState(false);
    const [resetting, setResetting] = useState(false);
    const [message, setMessage] = useState<string | undefined>();
    const [error, setError] = useState<string | undefined>();

    function toggle(i: number) {
        setDone((prev) => {
            const next = new Set(prev);
            if (next.has(i)) next.delete(i); else next.add(i);
            return next;
        });
    }

    async function reset() {
        setResetting(true);
        setError(undefined);
        try {
            const n = await resetMyOpenHolds(holds);
            setDone(new Set());
            setMessage(n === 0 ? "Nothing to reset: you have no open holds." : `Reset done: ${n} open hold${n === 1 ? "" : "s"} released.`);
            onReset();
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        } finally {
            setResetting(false);
            setConfirming(false);
        }
    }

    return (
        <div className="flex flex-col gap-grid">
            <section className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4 shadow-2">
                <h2 className="flex items-center gap-2 text-500 font-semibold text-card-foreground">
                    <GraduationCap className="icon-size-300 text-primary" aria-hidden /> Try it end to end
                </h2>
                <p className="text-300 text-muted-foreground">
                    Eight steps, about 10 minutes. You are viewing <strong className="text-card-foreground">{scopeLabel}</strong>, so
                    the <strong className="text-card-foreground">{isNetwork ? "network" : "plant"}</strong> numbers apply. All data is
                    synthetic; every expected number is checked against known answers.
                </p>
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-300 text-muted-foreground">{done.size} of {STEPS.length} done</span>
                    {!confirming ? (
                        <Button variant="secondary" onClick={() => setConfirming(true)} disabled={resetting}>
                            <span className="flex items-center gap-1.5"><RotateCcw className="icon-size-200" aria-hidden /> Reset demo</span>
                        </Button>
                    ) : (
                        <>
                            <span className="text-300 text-card-foreground">Release your open holds and cancel their open actions?</span>
                            <Button variant="danger" onClick={() => void reset()} disabled={resetting}>{resetting ? "Resetting…" : "Yes, reset"}</Button>
                            <Button variant="secondary" onClick={() => setConfirming(false)} disabled={resetting}>Cancel</Button>
                        </>
                    )}
                </div>
                {message && <p role="status" className="text-300 text-card-foreground">{message}</p>}
                {error && <ErrorBanner error={error} />}
            </section>

            <ol className="flex flex-col gap-3">
                {STEPS.map((s, i) => (
                    <li key={s.title} className={cn("rounded-xl border bg-card p-4", done.has(i) ? "border-primary" : "border-border")}>
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <label className="flex items-center gap-2 text-400 font-semibold text-card-foreground">
                                <input type="checkbox" checked={done.has(i)} onChange={() => toggle(i)} /> {s.title}
                            </label>
                            <Button variant="secondary" onClick={() => onGo(s.tab)}>Go to {TAB_LABEL[s.tab]}</Button>
                        </div>
                        <dl className="mt-2 grid gap-1 text-300 sm:grid-cols-[9rem_1fr]">
                            <dt className="text-muted-foreground">Do this</dt><dd className="text-card-foreground">{s.doThis}</dd>
                            <dt className="text-muted-foreground">You should see</dt>
                            <dd className="font-medium text-card-foreground">{isNetwork ? s.network : s.plant}</dd>
                            <dt className="text-muted-foreground">Why it matters</dt><dd className="text-muted-foreground">{s.why}</dd>
                        </dl>
                    </li>
                ))}
            </ol>
        </div>
    );
}

const TAB_LABEL: Record<Tab, string> = {
    pulse: "Plant pulse", trace: "Lot trace", holds: "Holds & actions", fleet: "Fleet & freight", ask: "Ask",
};
