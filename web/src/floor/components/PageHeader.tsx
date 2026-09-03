import type { ReactNode } from "react";

export interface PageHeaderProps {
  kicker: string;
  title: string;
  lede?: string;
  actions?: ReactNode;
}

export function PageHeader({ kicker, title, lede, actions }: PageHeaderProps) {
  return (
    <header className="page__header">
      <div>
        <span className="page__kicker">{kicker}</span>
        <h1>{title}</h1>
        {lede && <p className="page__lede">{lede}</p>}
      </div>
      {actions && <div className="page__actions">{actions}</div>}
    </header>
  );
}
