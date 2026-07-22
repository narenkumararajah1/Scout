// Matches docs/design/COMPONENT_LIBRARY.md's documented toast types
// (Success/Warning/Information/Error/Progress) - critical ones
// (error) require manual dismissal, others auto-dismiss (see
// hooks/useToasts.ts).

export type ToastVariant = "success" | "warning" | "info" | "error" | "progress";

export interface ToastItem {
  id: string;
  message: string;
  variant: ToastVariant;
}

interface ToastProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

export function Toast({ toast, onDismiss }: ToastProps) {
  return (
    <div className={`toast toast-${toast.variant}`}>
      <span>{toast.message}</span>
      <button type="button" className="toast-dismiss" onClick={() => onDismiss(toast.id)} aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
