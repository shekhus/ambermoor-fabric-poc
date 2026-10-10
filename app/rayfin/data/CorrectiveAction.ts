import { entity, role, uuid, text, date, one } from '@microsoft/rayfin-core';
import { QualityHold } from './QualityHold.js';

@entity()
@role('authenticated', ['create', 'read', 'update'])
export class CorrectiveAction {
  @uuid() id!: string;
  @uuid() hold_id!: string;
  @one(() => QualityHold) hold!: QualityHold;
  @text({ max: 200 }) title!: string;
  @text({ max: 120 }) owner_upn!: string;
  @date() due_date!: Date;
  @text({ max: 12 }) status!: string; // Open | Done | Cancelled
  @text({ max: 12 }) root_cause_category!: string; // Supplier | Process | Equipment | People | Other
}
