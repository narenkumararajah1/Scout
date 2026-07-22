import { useCallback, useRef, useState } from "react";
import type { ToastItem, ToastVariant } from "../components/ui/Toast";

const AUTO_DISMISS_MS = 4000;

export function useToasts() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const pushToast = useCallback(
    (message: string, variant: ToastVariant = "info") => {
      const id = String(nextId.current++);
      setToasts((current) => [...current, { id, message, variant }]);

      // Errors require manual dismissal (docs/design/COMPONENT_LIBRARY.md);
      // everything else clears itself.
      if (variant !== "error") {
        setTimeout(() => dismissToast(id), AUTO_DISMISS_MS);
      }
    },
    [dismissToast],
  );

  return { toasts, pushToast, dismissToast };
}
