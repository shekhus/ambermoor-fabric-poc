import { entity, role, uuid, text, int, date } from '@microsoft/rayfin-core';

// Writeback: a finished-goods lot placed on hold by QA. Spec: docs/specs/app-command-center.md.
// Permissions: signed-in users can create/read/update; no deletes (holds are an audit trail).
// Facility scoping for QA managers is applied in the UI from the facilities the semantic model's RLS returns.
// DB-level facility enforcement (claims-based policy) is a follow-up; see app/CLAUDE.md.
@entity()
@role('authenticated', ['create', 'read', 'update'])
export class QualityHold {
  @uuid() id!: string;
  @text({ max: 40 }) lot_id!: string;
  @text({ max: 8 }) facility_id!: string;
  @text({ max: 200 }) reason!: string;
  @text({ max: 10 }) severity!: string; // Low | Medium | High | Critical
  @text({ max: 12 }) status!: string; // Open | Released | Destroyed
  @int() cases_on_hold!: number;
  @text({ max: 40, optional: true }) source_ref?: string; // e.g. SN-2026-001
  @text({ max: 120 }) opened_by!: string;
  @date() opened_at!: Date;
}
