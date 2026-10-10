import { entity, role, uuid, text, date, one } from '@microsoft/rayfin-core';
import { QualityHold } from './QualityHold.js';

// Append-only timeline: create + read, no update/delete.
@entity()
@role('authenticated', ['create', 'read'])
export class HoldUpdate {
  @uuid() id!: string;
  @uuid() hold_id!: string;
  @one(() => QualityHold) hold!: QualityHold;
  @text({ max: 1000 }) note!: string;
  @text({ max: 120 }) author!: string;
  @date() created_at!: Date;
}
