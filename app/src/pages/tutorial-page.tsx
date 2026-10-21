import { Fragment, useState } from "react";
import { GraduationCap, RotateCcw } from "lucide-react";

import { resetMyHolds, type Hold } from "@/services/holds.service";
import { Button, ErrorBanner } from "@/components/ui";
import { cn } from "@/lib/utils";

type Tab = "pulse" | "trace" | "holds" | "fleet" | "ask";

/**
 * Guided cases. Every number was checked on 21 Oct 2026 against the live model, as admin (network) and impersonating
 * the P03 test user (plant), and against agent/golden_answers.json. Text in `backticks` renders as an ID to copy.
 */
interface Step {
    tab: Tab;
    title: string;
    doThis: string;
    network: string;
    plant?: string;            // omitted = same as network
    why: string;
    data: string;              // tables behind the step (for explaining the build)
}

interface Case {
    id: string;
    title: string;
    story: string;
    lesson: string;
    steps: Step[];
}

const CASES: Case[] = [
    {
        id: "recall",
        title: "Case 1 · Supplier recall: diced onions from Valley Fresh Produce",
        story: "On 15 Sep supplier notice SN-2026-001 flags ingredient lot `ILOT-P02-ING02-20260908` (diced yellow onions, "
            + "received at plant P02) for possible contamination. QA must find every finished lot made with it, every customer "
            + "who received it, and stop what is still in the building.",
        lesson: "Trace forward from one ingredient lot to lots, shipments and customers in one click, then act and leave an audit trail.",
        steps: [
            {
                tab: "trace", title: "Open the notice",
                doThis: "Open Lot trace and click the red chip `SN-2026-001 · ILOT-P02-ING02-20260908 · Open`.",
                network: "Finished lots 36 · Cases shipped 145 · Customers 10 (13 shipments) · Cases destroyed 551.",
                plant: "No red chip and no results: the notice and the lots belong to P02. Row-level security hides them from a P03 user. Go to Case 2.",
                why: "The recall scope takes one click instead of days of spreadsheets, and every number comes from the same model.",
                data: "fact_supplier_notice → bridge_lot_ingredient → trace_genealogy; fact_waste (reason Supplier Recall).",
            },
            {
                tab: "trace", title: "Read the scope",
                doThis: "Scroll the Finished lots grid and the Customers in scope chart.",
                network: "9 of the 36 lots were shipped; the other 27 never left P02. Top customers: Riverbend Fresh Market 31 cases, "
                    + "Prairie Bistro Group 23, Brookside Restaurant Partners 22.",
                why: "Shows who to call first and how much product is still under your control.",
                data: "trace_genealogy (cases_shipped, customer_id), fact_lot (cases_produced), dim_customer.",
            },
            {
                tab: "trace", title: "Hold the stock still in the plant",
                doThis: "In the grid select `LP02-260911-026` (Guacamole 10 lb tub, 42 made, 26 shipped). Keep the reason "
                    + "\"Supplier notice SN-2026-001\", set Severity Critical, Cases on hold 16, then Place hold.",
                network: "The hold is saved with your name. Open holds goes up by 1 on Plant pulse and on the Holds & actions tab.",
                why: "Action is taken where the problem is found, not in an email thread.",
                data: "App database (Rayfin): QualityHold, with source_ref = SN-2026-001.",
            },
            {
                tab: "holds", title: "Assign the corrective action",
                doThis: "Open Holds & actions, select the hold. Add a corrective action: \"Valley Fresh to confirm root cause and "
                    + "corrective plan\", owner = your email, due in 7 days, root cause Supplier. Then post the update "
                    + "\"Riverbend Fresh Market, Prairie Bistro Group and Brookside notified\".",
                network: "The action appears as Open; the timeline shows the hold, the action and your update, each with your name and time.",
                why: "Auditors ask who decided what and when. The timeline answers that without anyone writing it up.",
                data: "App database: CorrectiveAction, HoldUpdate.",
            },
            {
                tab: "holds", title: "Close it out",
                doThis: "Click Mark done on the action. In real life the lot would then be destroyed. For the demo, leave the hold Open: "
                    + "Reset demo archives it at the end.",
                network: "Action status Done. The hold stays Open until a person releases or destroys it.",
                why: "Closing the action and deciding the stock are separate steps, by design.",
                data: "App database: CorrectiveAction.status, QualityHold.status.",
            },
        ],
    },
    {
        id: "coldchain",
        title: "Case 2 · Cold chain: truck TRK-117 runs warm",
        story: "Between 10 and 14 Sep, reefer truck TRK-117 from plant P03 delivered four loads above 5 °C for 6 to 11 hours. "
            + "Customers rejected 158 cases. QA must separate a transport failure (one shipment) from a product failure (a whole lot).",
        lesson: "The excursion rule (≥ 30 min cumulative above 5 °C) finds the 4 real problems among 112 shipments with a short warm "
            + "reading, and the trace shows the rest of each lot was safe.",
        steps: [
            {
                tab: "pulse", title: "Spot it",
                doThis: "On Plant pulse read the Cold-chain excursions tile.",
                network: "4 excursions, all on TRK-117 from P03. (112 shipments had at least one reading above 5 °C, mostly door "
                    + "openings; the 30-minute rule filters those out.)",
                plant: "4 excursions: they are all P03's, so a P03 QA manager sees the full case.",
                why: "One rule, defined once in the model, used by the tile, the agent and the alert.",
                data: "fact_shipment.is_excursion and tor_minutes, built from ReeferTelemetry (15-min readings).",
            },
            {
                tab: "ask", title: "List the shipments",
                doThis: "In Ask, click \"Which shipments had a cold-chain excursion, and on which truck?\". "
                    + "(Network users can also open the live truck map from Fleet & freight.)",
                network: "SH000827 Sunset Restaurant Partners (600 min, 8.25 °C), SH000828 Sunset Restaurant Partners (615 min, 8.8 °C), "
                    + "SH001151 Bluebird Food Stores (660 min, 9.24 °C, 88 cases), SH000752 Silverline Corner Mart (375 min, 9.47 °C). "
                    + "All rejected on delivery: 158 cases.",
                why: "A question nobody built a page for, answered with your access.",
                data: "fact_shipment, dim_customer; the truck map reads ReeferTelemetry in the Eventhouse.",
            },
            {
                tab: "trace", title: "Trace a lot that rode the truck",
                doThis: "In Lot trace enter `ILOT-P03-ING19-20260908` (cooked chicken) and click Trace. Find `LP03-260912-030` "
                    + "(Chicken Alfredo 2 lb tub).",
                network: "7 finished lots, 325 cases shipped, 19 customers, 25 shipments. LP03-260912-030: 75 cases made, all shipped; "
                    + "17 of them were on SH001151.",
                why: "The other 58 cases of that lot went on other trucks within temperature, so this is not a lot recall.",
                data: "bridge_lot_ingredient → trace_genealogy; fact_shipment_line (cases per shipment and lot).",
            },
            {
                tab: "trace", title: "Hold the returned cases",
                doThis: "Select `LP03-260912-030`. Reason \"TRK-117 excursion: 17 cases rejected on SH001151\", Severity High, "
                    + "Cases on hold 17, then Place hold.",
                network: "Hold saved. A P03 user can place this hold too: it is their plant's lot.",
                why: "Rejected product comes back to the plant and must not be resold.",
                data: "App database: QualityHold.",
            },
            {
                tab: "holds", title: "Fix the truck, decide the product",
                doThis: "On the hold add the action \"Service TRK-117 reefer unit and recalibrate the probe\", root cause Equipment, "
                    + "owner = your email, due tomorrow. Post the update \"58 other cases of this lot were within temperature\". "
                    + "Optional: click Destroy (temperature-abused food is destroyed; the hold moves to the Destroyed tab until Reset demo).",
                network: "Corrective action Open with root cause Equipment; if you destroyed it, the hold shows in Destroyed (n).",
                why: "Root-cause categories show over time whether problems come from suppliers, equipment or process.",
                data: "App database: CorrectiveAction.root_cause_category, QualityHold.status = Destroyed.",
            },
        ],
    },
    {
        id: "dock",
        title: "Case 3 · Late Monday deliveries from P07",
        story: "Foodservice customers of P07 Southeast DC complain about late Monday deliveries. Is it the road (traffic, distance) "
            + "or the dock (trucks waiting to be loaded)?",
        lesson: "Not every problem is a lot hold. Here the food is fine: the fix is dock scheduling, and the data proves where the time goes.",
        steps: [
            {
                tab: "pulse", title: "Find the pattern",
                doThis: "On Plant pulse keep Channel = Foodservice and read the on-time heatmap.",
                network: "P07 × Monday is the weakest cell: 64.1% on time (39 shipments). The next weakest is P03 × Thursday at 87.2%.",
                plant: "Only P03's row. Its weakest cell is Foodservice Thursday at 87.2% (39 shipments), so P03 has no Monday problem.",
                why: "A weekly pattern shows up without anyone writing a query.",
                data: "fact_shipment.on_time by dim_facility × dim_date.weekday × dim_customer.channel.",
            },
            {
                tab: "fleet", title: "Dock or road?",
                doThis: "Open Fleet & freight. Read the Late trips caused by dock wait tile, then hover the red P07 bar.",
                network: "14 late trips caused by dock wait, all P07. The bar is 0.66 h: the average over all 502 P07 trips. The tooltip "
                    + "adds 6.26 h: the average for just those 14 late trips. Their drive time (13.1 h) was normal.",
                plant: "One bar for P03: 0.50 h over 539 trips, not red, and 0 late trips caused by dock wait.",
                why: "A few very bad trips hide inside an average. Showing both numbers tells the real story.",
                data: "fact_trip.dock_wait_h (departed − planned departure), drive_h, is_dock_delayed (> 2 h).",
            },
            {
                tab: "ask", title: "Who was affected?",
                doThis: "In Ask type \"Which customers received P07's late trips caused by dock wait?\".",
                network: "Redwood Catering Co 5 trips (6.07 h average wait), Aspen Restaurant Partners 5 (5.89 h), "
                    + "Riverbend Bistro Group 4 (6.96 h), over 9 Mondays from 6 Jul to 21 Sep.",
                plant: "No rows: P03 has no dock-caused late trips.",
                why: "Gives the account team the exact customers and dates for the conversation.",
                data: "fact_trip, dim_customer.",
            },
            {
                tab: "fleet", title: "What does it cost?",
                doThis: "Read Freight cost per case and the Top 10 lanes table.",
                network: "Total trip cost $3,957,157. P08 has the highest cost per case ($31.93), P06 the lowest ($19.05). "
                    + "Lane P07 → C0109 (Aspen Restaurant Partners) costs $78,998 over 39 trips with a 1.18 h average dock wait.",
                plant: "P03: 539 trips, $586,410, $20.99 per case.",
                why: "Waiting drivers are paid by the hour, so dock wait is a cost as well as a service problem.",
                data: "fact_trip.trip_cost_usd = route_km × cost_per_km + (dock_wait_h + drive_h) × driver rate (demo rates).",
            },
            {
                tab: "holds", title: "Decide the action",
                doThis: "Don't place a hold: the product was within temperature and in full. Write the action outside the app "
                    + "(for example, \"Add a Monday loading shift at P07\") and check the Fleet tab again next month.",
                network: "Open holds unchanged.",
                why: "Holds are for product. Using them for a logistics problem would pollute the food-safety audit trail.",
                data: "None: a deliberate no-op.",
            },
        ],
    },
];

const TAB_LABEL: Record<Tab, string> = {
    pulse: "Plant pulse", trace: "Lot trace", holds: "Holds & actions", fleet: "Fleet & freight", ask: "Ask",
};

/** `ID` in text -> monospace, selectable. */
function Rich({ text }: { text: string }) {
    return (
        <>
            {text.split("`").map((part, i) => i % 2 === 1
                ? <code key={i} className="select-all rounded bg-secondary px-1 font-[family-name:var(--font-monospace)] text-secondary-foreground">{part}</code>
                : <Fragment key={i}>{part}</Fragment>)}
        </>
    );
}

export function TutorialPage({ scopeLabel, isNetwork, holds, onGo, onReset }: {
    scopeLabel: string;
    isNetwork: boolean;
    holds: Hold[];
    onGo: (tab: Tab) => void;
    onReset: () => void;
}) {
    const [caseId, setCaseId] = useState(CASES[0].id);
    const [done, setDone] = useState<Set<string>>(new Set());
    const [confirming, setConfirming] = useState(false);
    const [resetting, setResetting] = useState(false);
    const [message, setMessage] = useState<string | undefined>();
    const [error, setError] = useState<string | undefined>();
    const current = CASES.find((c) => c.id === caseId) ?? CASES[0];
    const total = CASES.reduce((n, c) => n + c.steps.length, 0);

    function toggle(key: string) {
        setDone((prev) => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key); else next.add(key);
            return next;
        });
    }

    async function reset() {
        setResetting(true);
        setError(undefined);
        try {
            const n = await resetMyHolds(holds);
            setDone(new Set());
            setMessage(n === 0 ? "Nothing to reset: you have no holds." : `Reset done: ${n} hold${n === 1 ? "" : "s"} archived. Every tab starts from 0.`);
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
                    <GraduationCap className="icon-size-300 text-primary" aria-hidden /> Try it end to end: three real cases
                </h2>
                <p className="text-300 text-muted-foreground">
                    Each case is a problem a QA or operations manager meets, followed from the first signal to the action, about
                    10 minutes each. You are viewing <strong className="text-card-foreground">{scopeLabel}</strong>, so the{" "}
                    <strong className="text-card-foreground">{isNetwork ? "network" : "plant"}</strong> numbers apply. All data is
                    synthetic; every expected number was checked against the live model.
                </p>
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-300 text-muted-foreground">{done.size} of {total} steps done</span>
                    {!confirming ? (
                        <Button variant="secondary" onClick={() => setConfirming(true)} disabled={resetting}>
                            <span className="flex items-center gap-1.5"><RotateCcw className="icon-size-200" aria-hidden /> Reset demo</span>
                        </Button>
                    ) : (
                        <>
                            <span className="text-300 text-card-foreground">
                                Archive every hold you opened (open, released and destroyed) and cancel their open actions? They disappear from the app but stay in the database.
                            </span>
                            <Button variant="danger" onClick={() => void reset()} disabled={resetting}>{resetting ? "Resetting…" : "Yes, reset"}</Button>
                            <Button variant="secondary" onClick={() => setConfirming(false)} disabled={resetting}>Cancel</Button>
                        </>
                    )}
                </div>
                {message && <p role="status" className="text-300 text-card-foreground">{message}</p>}
                {error && <ErrorBanner error={error} />}
            </section>

            <div role="tablist" aria-label="Cases" className="flex flex-wrap gap-1 rounded-lg border border-border bg-card p-1">
                {CASES.map((c) => {
                    const n = c.steps.filter((_, i) => done.has(`${c.id}-${i}`)).length;
                    return (
                        <button key={c.id} role="tab" type="button" aria-selected={caseId === c.id} onClick={() => setCaseId(c.id)}
                            className={cn(
                                "flex-1 rounded-md px-3 py-1.5 text-left text-300 font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                caseId === c.id ? "bg-primary text-primary-foreground" : "text-card-foreground hover:bg-hover",
                            )}>
                            {c.title.split(":")[0]} <span className="opacity-80">({n}/{c.steps.length})</span>
                        </button>
                    );
                })}
            </div>

            <section className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4" aria-label={current.title}>
                <h3 className="text-400 font-semibold text-card-foreground">{current.title}</h3>
                <p className="text-300 text-card-foreground"><Rich text={current.story} /></p>
                <p className="text-300 text-muted-foreground"><strong>What it shows:</strong> {current.lesson}</p>
            </section>

            <ol className="flex flex-col gap-3">
                {current.steps.map((s, i) => {
                    const key = `${current.id}-${i}`;
                    return (
                        <li key={key} className={cn("rounded-xl border bg-card p-4", done.has(key) ? "border-primary" : "border-border")}>
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <label className="flex items-center gap-2 text-400 font-semibold text-card-foreground">
                                    <input type="checkbox" checked={done.has(key)} onChange={() => toggle(key)} /> {i + 1}. {s.title}
                                </label>
                                <Button variant="secondary" onClick={() => onGo(s.tab)}>Go to {TAB_LABEL[s.tab]}</Button>
                            </div>
                            <dl className="mt-2 grid gap-1 text-300 sm:grid-cols-[9rem_1fr]">
                                <dt className="text-muted-foreground">Do this</dt>
                                <dd className="text-card-foreground"><Rich text={s.doThis} /></dd>
                                <dt className="text-muted-foreground">You should see</dt>
                                <dd className="font-medium text-card-foreground"><Rich text={isNetwork ? s.network : (s.plant ?? s.network)} /></dd>
                                <dt className="text-muted-foreground">Why it matters</dt>
                                <dd className="text-muted-foreground">{s.why}</dd>
                                <dt className="text-muted-foreground">Data behind it</dt>
                                <dd className="font-[family-name:var(--font-monospace)] text-200 text-muted-foreground">{s.data}</dd>
                            </dl>
                        </li>
                    );
                })}
            </ol>

            <p className="text-300 text-muted-foreground">
                Finished? Click <strong>Reset demo</strong> above so the next person starts clean. Nothing is deleted: your holds are
                archived (hidden from the app, kept in the database) and each gets an "Archived by Tutorial reset" entry in its timeline. Ask needs Anthropic API credit; until then those steps show
                an error.
            </p>
        </div>
    );
}
