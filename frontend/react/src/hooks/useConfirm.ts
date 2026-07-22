import { useCallback, useState } from "react";
import type { ConfirmDialogProps } from "../components/ui/ConfirmDialog";

// Promise-based replacement for window.confirm() (V2->V3 parity pass,
// Priority 5 polish) - a native confirm() blocks the render thread and
// can't be styled, so destructive actions (Remove Company, Remove
// Recipient, Delete Schedule, Distribute Report) get a themed dialog
// instead. Mirrors useToasts()'s shape: a hook holding the state, paired
// with a container component the page renders inline.
export function useConfirm() {
  const [pending, setPending] = useState<{ message: string; resolve: (value: boolean) => void } | null>(null);

  const confirm = useCallback((message: string): Promise<boolean> => {
    return new Promise((resolve) => setPending({ message, resolve }));
  }, []);

  const confirmDialog: ConfirmDialogProps | null = pending
    ? {
        message: pending.message,
        onConfirm: () => {
          pending.resolve(true);
          setPending(null);
        },
        onCancel: () => {
          pending.resolve(false);
          setPending(null);
        },
      }
    : null;

  return { confirm, confirmDialog };
}
