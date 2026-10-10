// Inject a user-entered value into a DAX string literal. Only plain IDs are accepted, so a search box can't inject DAX.
export function daxString(value: string): string {
    const v = value.trim();
    if (!/^[A-Za-z0-9_-]{1,60}$/.test(v)) {
        throw new Error(`Not a valid lot / notice id: "${value}"`);
    }
    return `"${v}"`;
}

export function fill(template: string, params: Record<string, string>): string {
    return template.replace(/@(\w+)/g, (m, key: string) => (key in params ? daxString(params[key]) : m));
}
