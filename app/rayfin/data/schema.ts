import { QualityHold } from './QualityHold.js';
import { CorrectiveAction } from './CorrectiveAction.js';
import { HoldUpdate } from './HoldUpdate.js';

export type FreshyFreshAppSchema = {
  QualityHold: QualityHold;
  CorrectiveAction: CorrectiveAction;
  HoldUpdate: HoldUpdate;
};

export const schema = [QualityHold, CorrectiveAction, HoldUpdate];
