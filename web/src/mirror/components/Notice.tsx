import type { ReactNode } from "react";

export interface NoticeProps {
  tone?: "quiet" | "error" | "ok";
  title: string;
  children?: ReactNode;
  action?: { label: string; onClick: () => void };
}

export function Notice({ tone = "quiet", title, children, action }: NoticeProps) {
  return (
    <section className={`notice notice-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <p className="notice-title">{title}</p>
      {children && <div className="notice-body">{children}</div>}
      {action && (
        <button type="button" className="btn btn-secondary" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </section>
  );
}
