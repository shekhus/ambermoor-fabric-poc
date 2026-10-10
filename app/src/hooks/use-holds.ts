import { useCallback, useEffect, useState } from "react";

import { listHolds, type Hold } from "@/services/holds.service";

/** Holds from the app's SQL database. `facilityIds` (from the model, RLS-trimmed) scopes what this user sees. */
export function useHolds(facilityIds: string[] | undefined) {
    const [holds, setHolds] = useState<Hold[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | undefined>();

    const refetch = useCallback(async () => {
        setIsLoading(true);
        setError(undefined);
        try {
            setHolds(await listHolds());
        } catch (err) {
            setError(err instanceof Error ? err : new Error(String(err)));
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void refetch();
    }, [refetch]);

    const visible = facilityIds ? holds.filter((h) => facilityIds.includes(h.facility_id)) : [];
    return { holds: visible, isLoading: isLoading || !facilityIds, error, refetch };
}
