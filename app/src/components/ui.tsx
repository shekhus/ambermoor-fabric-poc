import type { ReactNode } from "react";
import type { DataTable } from "@microsoft/fabric-visuals-core";
import { formatValue } from "@microsoft/fabric-visuals-core";

import { useSemanticModelQuery } from "@/hooks/use-semantic-model-query";
import { toDataTable, type ColumnMetadataMap } from "@/lib/to-data-table";
import { cn } from "@/lib/utils";

/** Runs a query factory's DAX and shapes the result. SDK errors arrive in `error`, never as throws. */
export function useTable(def: { connection: string; query: string; columnMetadata: ColumnMetadataMap }) {
    const { data, isLoading, error, refetch } = useSemanticModelQuery({ connection: def.connection, query: def.query });
    const table: DataTable | undefined =
        data?.status === "success" ? dateOnly(toDataTable(data.table, def.columnMetadata)) : undefined;
    return { table, isLoading, error, refetch };
}

/** DAX returns dates as ISO date-time strings; show date columns (format "yyyy-mm-dd") as plain YYYY-MM-DD. */
function dateOnly(table: DataTable): DataTable {
    const idx = table.columns.flatMap((c, i) => (c.format === "yyyy-mm-dd" ? [i] : []));
    if (idx.length === 0) return table;
    return {
        columns: table.columns.map((c) => (c.format === "yyyy-mm-dd" ? { ...c, format: undefined } : c)),
        rows: table.rows.map((r) => r.map((v, i) => (idx.includes(i) && typeof v === "string" ? v.slice(0, 10) : v))),
    };
}

/** First-row value of a column by its Vega-safe name. */
export function cell(table: DataTable | undefined, name: string, row = 0): unknown {
    if (!table) return undefined;
    const i = table.columns.findIndex((c) => c.name === name);
    return i < 0 ? undefined : table.rows[row]?.[i];
}

export function rowsAsObjects(table: DataTable | undefined): Record<string, unknown>[] {
    if (!table) return [];
    return table.rows.map((r) => Object.fromEntries(table.columns.map((c, i) => [c.name, r[i]])));
}

export function fmt(value: unknown, format?: string): string {
    if (value === null || value === undefined) return "—";
    return String(formatValue(value, format));
}

export function Skeleton({ className }: { className?: string }) {
    return <div className={cn("animate-pulse rounded-lg bg-muted", className)} aria-hidden />;
}

export function ErrorBanner({ error }: { error: Error | string }) {
    return (
        <div role="alert" className="rounded-lg border border-destructive bg-card p-3 text-300 text-destructive">
            {typeof error === "string" ? error : error.message}
        </div>
    );
}

export function Empty({ children }: { children: ReactNode }) {
    return (
        <div className="flex min-h-32 items-center justify-center rounded-xl border border-dashed border-border p-6 text-300 text-muted-foreground">
            {children}
        </div>
    );
}

export function Kpi({
    label, value, hint, tone = "default", loading,
}: { label: string; value: string; hint?: string; tone?: "default" | "alert" | "good"; loading?: boolean }) {
    return (
        <div
            className={cn(
                "relative overflow-hidden rounded-xl border border-border bg-card p-4 shadow-2",
                "before:absolute before:inset-y-0 before:left-0 before:w-1",
                tone === "alert" ? "before:bg-destructive" : tone === "good" ? "before:bg-success" : "before:bg-brand",
            )}
        >
            <div className="text-200 font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
            {loading ? (
                <Skeleton className="mt-2 h-8 w-24" />
            ) : (
                <div className="mt-1 font-[family-name:var(--font-numeric)] text-600 font-semibold text-card-foreground">
                    {value}
                </div>
            )}
            {hint && <div className="mt-1 text-200 text-muted-foreground">{hint}</div>}
        </div>
    );
}

export function Button({
    children, onClick, variant = "primary", disabled, type = "button",
}: {
    children: ReactNode;
    onClick?: () => void;
    variant?: "primary" | "secondary" | "danger";
    disabled?: boolean;
    type?: "button" | "submit";
}) {
    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled}
            className={cn(
                "rounded-lg px-3 py-1.5 text-300 font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                "disabled:cursor-not-allowed disabled:opacity-60",
                variant === "primary" && "bg-primary text-primary-foreground hover:opacity-90",
                variant === "secondary" && "border border-border bg-card text-card-foreground hover:bg-hover",
                variant === "danger" && "bg-destructive text-destructive-foreground hover:opacity-90",
            )}
        >
            {children}
        </button>
    );
}

export const inputClass =
    "w-full rounded-lg border border-input bg-background px-3 py-1.5 text-300 text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring";
