interface Props {
  message: string;
  onDismiss: () => void;
}

export function ErrorBanner({ message, onDismiss }: Props) {
  return (
    <div
      role="alert"
      className="flex items-center justify-between border-b border-destructive/30 bg-destructive/10 px-4 py-1.5 text-xs text-destructive"
    >
      <span>{message}</span>
      <button onClick={onDismiss} aria-label="Dismiss error" className="ml-4 text-destructive/60 transition-colors hover:text-destructive">✕</button>
    </div>
  );
}
