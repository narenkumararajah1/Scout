import type { ReactNode } from "react";

interface CardProps {
  title?: ReactNode;
  children: ReactNode;
}

export function Card({ title, children }: CardProps) {
  return (
    <div className="card">
      {title && <h3 className="card-title">{title}</h3>}
      <div className="card-body">{children}</div>
    </div>
  );
}
