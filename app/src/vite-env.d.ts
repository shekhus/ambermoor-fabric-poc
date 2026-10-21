/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Rayfin API base URL (e.g. http://localhost:5168). */
  readonly VITE_RAYFIN_API_URL?: string;
  /** Rayfin publishable key (pk-...). */
  readonly VITE_RAYFIN_PUBLISHABLE_KEY?: string;
  /** Fabric workspace ID — maps to FabricAuthOptions.workspaceId. */
  readonly VITE_FABRIC_WORKSPACE_ID?: string;
  /** Fabric/Rayfin item ID — maps to FabricAuthOptions.projectId. */
  readonly VITE_FABRIC_ITEM_ID?: string;
  /** Fabric portal base URL (e.g. https://app.fabric.microsoft.com/). */
  readonly VITE_FABRIC_PORTAL_URL?: string;
  /** Real-Time Dashboard RTD_FreshyFresh_Fleet link for the Fleet page (set in .env.production.local; holds IDs, gitignored). */
  readonly VITE_FLEET_MAP_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}